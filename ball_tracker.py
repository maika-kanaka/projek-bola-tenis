"""
Wall Interactive - Ball Tracker & Hit Detector
================================================
Mendeteksi bola (berdasarkan warna) menggunakan RealSense RGB-D, melacak
trajectory-nya, dan mengirim event "hit" via OSC saat bola mencapai
bidang dinding.

Urutan pemakaian:
    1. tools/hsv_picker.py   -> cari HSV_LOWER/HSV_UPPER yang pas untuk bola
    2. calibrate.py          -> ukur jarak dinding (dinding harus kosong)
    3. ball_tracker.py       -> jalankan deteksi + tracking

Event OSC dikirim ke OSC_IP:OSC_PORT pada address OSC_ADDRESS_HIT dengan
argumen (x_norm, y_norm, speed_m_s):
    x_norm, y_norm : posisi hit dinormalisasi 0.0-1.0 dalam frame kamera
                      (nanti dipetakan ke koordinat proyektor lewat
                      homography terpisah pada tahap kalibrasi proyektor)
    speed_m_s       : estimasi kecepatan bola saat hit (perkiraan kasar)
"""

import json
import os
import time
from collections import deque
from dataclasses import dataclass, field

import cv2
import numpy as np
import pyautogui
import pyrealsense2 as rs
from pythonosc.udp_client import SimpleUDPClient

import config


pyautogui.FAILSAFE = False


@dataclass
class Detection:
    timestamp: float
    x_px: int
    y_px: int
    depth_m: float


@dataclass
class BallTrack:
    """Menyimpan histori posisi bola untuk satu lintasan lempar."""

    detections: deque = field(default_factory=lambda: deque(maxlen=60))
    missed_frames: int = 0
    last_hit_time: float = 0.0

    def add(self, det: Detection):
        self.detections.append(det)
        self.missed_frames = 0

    def mark_missed(self):
        self.missed_frames += 1
        if self.missed_frames > config.MAX_TRACK_GAP_FRAMES:
            self.detections.clear()

    def is_valid(self) -> bool:
        return len(self.detections) >= config.MIN_TRACK_LENGTH

    def estimate_speed(self) -> float:
        """Estimasi kecepatan (m/s) dari 2 titik terakhir berdasarkan
        perubahan depth. Pendekatan kasar, bukan kecepatan 3D penuh —
        cukup untuk keperluan gameplay (mis. skor makin tinggi kalau
        lemparan makin keras)."""
        if len(self.detections) < 2:
            return 0.0
        p1, p2 = self.detections[-2], self.detections[-1]
        dt = p2.timestamp - p1.timestamp
        if dt <= 0:
            return 0.0
        dz = abs(p1.depth_m - p2.depth_m)
        return dz / dt


def load_wall_distance() -> float:
    if config.WALL_DISTANCE_M is not None:
        return config.WALL_DISTANCE_M
    if not os.path.exists(config.WALL_CALIBRATION_FILE):
        raise FileNotFoundError(
            f"File kalibrasi '{config.WALL_CALIBRATION_FILE}' tidak ditemukan. "
            "Jalankan calibrate.py dulu."
        )
    with open(config.WALL_CALIBRATION_FILE) as f:
        data = json.load(f)
    return float(data["wall_distance_m"])


def load_wall_roi_points():
    if config.WALL_ROI_POINTS is not None:
        return np.array(config.WALL_ROI_POINTS, dtype=np.float32)
    if not os.path.exists(config.WALL_CALIBRATION_FILE):
        return None

    with open(config.WALL_CALIBRATION_FILE) as f:
        data = json.load(f)

    points = data.get("wall_roi_points")
    if not points or len(points) != 4:
        return None
    return np.array(points, dtype=np.float32)


def map_hit_to_screen(x_px: int, y_px: int, roi_points: np.ndarray):
    """Pemetaan titik dalam ROI dinding ke posisi layar (monitor)."""
    if roi_points is None or len(roi_points) != 4:
        return None

    src = np.float32(roi_points)
    dst = np.float32(
        [
            [0, 0],
            [config.MOUSE_SCREEN_WIDTH, 0],
            [config.MOUSE_SCREEN_WIDTH, config.MOUSE_SCREEN_HEIGHT],
            [0, config.MOUSE_SCREEN_HEIGHT],
        ]
    )
    transform = cv2.getPerspectiveTransform(src, dst)
    point = np.float32([[[x_px, y_px]]])
    mapped = cv2.perspectiveTransform(point, transform)[0][0]

    x_screen = int(np.clip(mapped[0], 0, config.MOUSE_SCREEN_WIDTH - 1))
    y_screen = int(np.clip(mapped[1], 0, config.MOUSE_SCREEN_HEIGHT - 1))
    return x_screen, y_screen


def find_ball_in_frame(color_image: np.ndarray):
    """Deteksi bola berdasarkan warna (HSV). Return (x_px, y_px, radius_px) atau None."""
    hsv = cv2.cvtColor(color_image, cv2.COLOR_BGR2HSV)
    mask = cv2.inRange(hsv, config.HSV_LOWER, config.HSV_UPPER)
    mask = cv2.erode(mask, None, iterations=1)
    mask = cv2.dilate(mask, None, iterations=2)

    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return None

    largest = max(contours, key=cv2.contourArea)
    (x, y), radius = cv2.minEnclosingCircle(largest)

    if radius < config.MIN_BALL_RADIUS_PX or radius > config.MAX_BALL_RADIUS_PX:
        return None

    return int(x), int(y), int(radius)


def get_depth_at(depth_frame, x_px: int, y_px: int, depth_scale: float, patch: int = 3) -> float:
    """Ambil median depth di sekitar titik (x_px, y_px) supaya lebih stabil
    daripada 1 pixel tunggal (mengurangi noise sensor)."""
    depth_image = np.asanyarray(depth_frame.get_data())
    h, w = depth_image.shape
    x0, x1 = max(0, x_px - patch), min(w, x_px + patch + 1)
    y0, y1 = max(0, y_px - patch), min(h, y_px + patch + 1)
    patch_vals = depth_image[y0:y1, x0:x1].astype(np.float32) * depth_scale
    valid = patch_vals[patch_vals > 0.05]
    if valid.size == 0:
        return -1.0
    return float(np.median(valid))


def main():
    wall_distance_m = load_wall_distance()
    wall_roi_points = load_wall_roi_points()
    print(f"Jarak dinding (kalibrasi): {wall_distance_m:.3f} m")
    print(f"Threshold hit: +/-{config.HIT_THRESHOLD_M:.3f} m")
    if wall_roi_points is not None:
        print("ROI dinding dimuat untuk mapping mouse: 4 titik terdeteksi")
    else:
        print("ROI dinding belum dikalibrasi. Mouse tidak akan bergerak.")

    osc_client = SimpleUDPClient(config.OSC_IP, config.OSC_PORT)
    print(f"Mengirim OSC ke {config.OSC_IP}:{config.OSC_PORT} pada '{config.OSC_ADDRESS_HIT}'")

    pipeline = rs.pipeline()
    rs_config = rs.config()
    rs_config.enable_stream(
        rs.stream.depth, config.FRAME_WIDTH, config.FRAME_HEIGHT, rs.format.z16, config.FRAME_RATE
    )
    rs_config.enable_stream(
        rs.stream.color, config.FRAME_WIDTH, config.FRAME_HEIGHT, rs.format.bgr8, config.FRAME_RATE
    )
    profile = pipeline.start(rs_config)

    depth_scale = profile.get_device().first_depth_sensor().get_depth_scale()
    align = rs.align(rs.stream.color)  # align depth ke color agar koordinat pixel sinkron

    track = BallTrack()

    try:
        while True:
            frames = pipeline.wait_for_frames()
            aligned = align.process(frames)
            depth_frame = aligned.get_depth_frame()
            color_frame = aligned.get_color_frame()
            if not depth_frame or not color_frame:
                continue

            color_image = np.asanyarray(color_frame.get_data())
            now = time.time()

            found = find_ball_in_frame(color_image)
            hit_triggered = False

            if found is not None:
                x_px, y_px, radius_px = found
                depth_m = get_depth_at(depth_frame, x_px, y_px, depth_scale)
                in_play_area = config.PLAY_AREA_MIN_M <= depth_m <= config.PLAY_AREA_MAX_M

                if depth_m > 0 and in_play_area:
                    track.add(Detection(timestamp=now, x_px=x_px, y_px=y_px, depth_m=depth_m))

                    # --- cek kondisi HIT ---
                    near_wall = abs(depth_m - wall_distance_m) <= config.HIT_THRESHOLD_M
                    cooldown_ok = (now - track.last_hit_time) > config.HIT_COOLDOWN_S

                    if track.is_valid() and near_wall and cooldown_ok:
                        speed = track.estimate_speed()
                        x_norm = x_px / config.FRAME_WIDTH
                        y_norm = y_px / config.FRAME_HEIGHT

                        osc_client.send_message(config.OSC_ADDRESS_HIT, [x_norm, y_norm, speed])
                        track.last_hit_time = now
                        hit_triggered = True

                        if config.MOVE_MOUSE_ON_HIT and wall_roi_points is not None:
                            mouse_target = map_hit_to_screen(x_px, y_px, wall_roi_points)
                            if mouse_target is not None:
                                mouse_x, mouse_y = mouse_target
                                pyautogui.moveTo(mouse_x, mouse_y, duration=0.02)
                                print(f"Mouse -> ({mouse_x}, {mouse_y})")

                        print(f"HIT! x={x_norm:.2f} y={y_norm:.2f} speed~={speed:.2f} m/s")

                    if config.SHOW_DEBUG_WINDOW:
                        color = (0, 0, 255) if hit_triggered else (0, 255, 0)
                        cv2.circle(color_image, (x_px, y_px), radius_px, color, 2)
                        cv2.putText(
                            color_image, f"{depth_m:.2f} m", (x_px + 10, y_px),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2,
                        )
                else:
                    track.mark_missed()
            else:
                track.mark_missed()

            if config.SHOW_DEBUG_WINDOW:
                pts = list(track.detections)
                for i in range(1, len(pts)):
                    cv2.line(
                        color_image,
                        (pts[i - 1].x_px, pts[i - 1].y_px),
                        (pts[i].x_px, pts[i].y_px),
                        (255, 200, 0), 2,
                    )

                if wall_roi_points is not None:
                    cv2.polylines(
                        color_image,
                        [np.int32(wall_roi_points)],
                        isClosed=True,
                        color=(255, 255, 0),
                        thickness=2,
                    )

                cv2.putText(
                    color_image, f"Wall: {wall_distance_m:.2f} m", (10, 20),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1,
                )
                cv2.imshow("Wall Interactive - Ball Tracker (debug)", color_image)
                if cv2.waitKey(1) & 0xFF == ord("q"):
                    break

    finally:
        pipeline.stop()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
