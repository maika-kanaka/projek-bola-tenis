"""
Kalibrasi bidang dinding.

Jalankan skrip ini dengan kondisi dinding KOSONG (tanpa orang/bola di depan
kamera) untuk menangkap jarak rata-rata dinding ke kamera. Hasilnya disimpan
ke file JSON dan dipakai oleh ball_tracker.py sebagai referensi "hit".

Cara pakai:
    python calibrate.py
"""

import json
import time

import cv2
import numpy as np
import pyrealsense2 as rs

import config


def collect_wall_roi_points(pipeline):
    """Minta user mengeklik 4 titik ROI dinding di frame RGB."""
    window_name = "Calibrate Wall ROI"
    points = []

    def on_mouse(event, x, y, flags, param):
        if event == cv2.EVENT_LBUTTONDOWN and len(points) < 4:
            points.append((x, y))
            print(f"ROI point {len(points)}/4: ({x}, {y})")

    cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
    cv2.setMouseCallback(window_name, on_mouse)

    print("Klik 4 titik dinding ROI dalam urutan:")
    print("  1) kiri-atas, 2) kanan-atas, 3) kanan-bawah, 4) kiri-bawah")
    print("Tekan tombol 'r' untuk reset jika perlu, 'q' untuk batal.")

    try:
        while True:
            frames = pipeline.wait_for_frames()
            color_frame = frames.get_color_frame()
            if not color_frame:
                continue

            color_image = np.asanyarray(color_frame.get_data())
            for idx, (px, py) in enumerate(points, start=1):
                cv2.circle(color_image, (px, py), 6, (0, 255, 255), -1)
                cv2.putText(
                    color_image, str(idx), (px + 8, py - 8),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2,
                )

            cv2.putText(
                color_image,
                "Klik 4 titik ROI dinding...",
                (10, 25),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (255, 255, 255),
                2,
            )
            cv2.imshow(window_name, color_image)

            key = cv2.waitKey(1) & 0xFF
            if key == ord("r"):
                points.clear()
                print("ROI direset.")
            elif key == ord("q"):
                raise KeyboardInterrupt("Kalibrasi ROI dibatalkan oleh user.")
            elif len(points) == 4:
                break

    finally:
        cv2.destroyAllWindows()

    if len(points) != 4:
        raise RuntimeError("Butuh tepat 4 titik ROI dinding.")

    return [[int(x), int(y)] for x, y in points]


def calibrate_wall(num_frames: int = 60):
    pipeline = rs.pipeline()
    rs_config = rs.config()
    rs_config.enable_stream(
        rs.stream.depth, config.FRAME_WIDTH, config.FRAME_HEIGHT, rs.format.z16, config.FRAME_RATE
    )
    rs_config.enable_stream(
        rs.stream.color, config.FRAME_WIDTH, config.FRAME_HEIGHT, rs.format.bgr8, config.FRAME_RATE
    )
    profile = pipeline.start(rs_config)

    depth_sensor = profile.get_device().first_depth_sensor()
    depth_scale = depth_sensor.get_depth_scale()

    print(f"Depth scale: {depth_scale:.6f} m/unit")
    print("Pastikan dinding kosong (tanpa orang/bola) di depan kamera...")
    time.sleep(2)

    samples = []
    try:
        for i in range(num_frames):
            frames = pipeline.wait_for_frames()
            depth_frame = frames.get_depth_frame()
            if not depth_frame:
                continue

            depth_image = np.asanyarray(depth_frame.get_data()).astype(np.float32) * depth_scale

            # Ambil hanya nilai valid (bukan 0 / out of range)
            valid = depth_image[(depth_image > 0.1) & (depth_image < 10.0)]
            if valid.size == 0:
                continue

            median_depth = float(np.median(valid))
            samples.append(median_depth)
            print(f"  Frame {i + 1}/{num_frames}: jarak median = {median_depth:.3f} m")

        if not samples:
            raise RuntimeError(
                "Tidak ada data depth valid yang terekam. Cek koneksi kamera / kondisi dinding."
            )

        wall_distance = float(np.median(samples))
        roi_points = collect_wall_roi_points(pipeline)

        result = {
            "wall_distance_m": wall_distance,
            "depth_scale": depth_scale,
            "num_samples": len(samples),
            "wall_roi_points": roi_points,
        }

        with open(config.WALL_CALIBRATION_FILE, "w") as f:
            json.dump(result, f, indent=2)

        print(f"\nKalibrasi selesai. Jarak dinding: {wall_distance:.3f} m")
        print(f"ROI dinding disimpan: {roi_points}")
        print(f"Disimpan ke: {config.WALL_CALIBRATION_FILE}")

    finally:
        pipeline.stop()
        cv2.destroyAll_windows()


if __name__ == "__main__":
    calibrate_wall()
