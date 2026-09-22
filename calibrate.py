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

import numpy as np
import pyrealsense2 as rs

import config


def calibrate_wall(num_frames: int = 60):
    pipeline = rs.pipeline()
    rs_config = rs.config()
    rs_config.enable_stream(
        rs.stream.depth, config.FRAME_WIDTH, config.FRAME_HEIGHT, rs.format.z16, config.FRAME_RATE
    )
    profile = pipeline.start(rs_config)

    depth_sensor = profile.get_device().first_depth_sensor()
    depth_scale = depth_sensor.get_depth_scale()  # meter per unit

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

    finally:
        pipeline.stop()

    if not samples:
        raise RuntimeError(
            "Tidak ada data depth valid yang terekam. Cek koneksi kamera / kondisi dinding."
        )

    wall_distance = float(np.median(samples))
    result = {
        "wall_distance_m": wall_distance,
        "depth_scale": depth_scale,
        "num_samples": len(samples),
    }

    with open(config.WALL_CALIBRATION_FILE, "w") as f:
        json.dump(result, f, indent=2)

    print(f"\nKalibrasi selesai. Jarak dinding: {wall_distance:.3f} m")
    print(f"Disimpan ke: {config.WALL_CALIBRATION_FILE}")


if __name__ == "__main__":
    calibrate_wall()
