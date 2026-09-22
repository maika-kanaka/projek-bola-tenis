"""
HSV Picker - alat bantu untuk menentukan HSV_LOWER/HSV_UPPER yang pas
untuk warna bola yang dipakai.

Jalankan, arahkan bola ke kamera, geser trackbar sampai HANYA bola yang
terlihat putih di jendela "mask". Tekan 's' untuk cetak nilai HSV yang
sedang aktif ke terminal, lalu salin ke config.py di folder utama.

Cara pakai:
    python tools/hsv_picker.py
"""

import cv2
import numpy as np
import pyrealsense2 as rs

WIDTH, HEIGHT, FPS = 640, 480, 30


def nothing(_):
    pass


def main():
    pipeline = rs.pipeline()
    rs_config = rs.config()
    rs_config.enable_stream(rs.stream.color, WIDTH, HEIGHT, rs.format.bgr8, FPS)
    
    try:
        profile = pipeline.start(rs_config)
        print("Camera initialized successfully")
        # Warm up the camera
        import time
        time.sleep(1)
    except RuntimeError as e:
        print(f"Error starting camera: {e}")
        print("\nTroubleshooting steps:")
        print("1. Check if RealSense camera is connected via USB")
        print("2. Check if another process is using the camera")
        print("3. Try: python3 -m pyrealsense2 (to verify installation)")
        print("4. On macOS, try without sudo")
        return

    cv2.namedWindow("controls")
    for name, default, maxval in [
        ("H min", 20, 179), ("H max", 35, 179),
        ("S min", 100, 255), ("S max", 255, 255),
        ("V min", 100, 255), ("V max", 255, 255),
    ]:
        cv2.createTrackbar(name, "controls", default, maxval, nothing)

    print("Tekan 's' untuk cetak nilai HSV saat ini, 'q' untuk keluar.")

    try:
        while True:
            try:
                frames = pipeline.wait_for_frames(timeout_ms=5000)
            except RuntimeError as e:
                print(f"Timeout waiting for frame: {e}")
                print("Camera may have disconnected. Reconnect and restart the script.")
                break
                
            color_frame = frames.get_color_frame()
            if not color_frame:
                continue

            image = np.asanyarray(color_frame.get_data())
            hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)

            lower = np.array([cv2.getTrackbarPos(n, "controls") for n in ("H min", "S min", "V min")])
            upper = np.array([cv2.getTrackbarPos(n, "controls") for n in ("H max", "S max", "V max")])

            mask = cv2.inRange(hsv, lower, upper)
            result = cv2.bitwise_and(image, image, mask=mask)

            cv2.imshow("color", image)
            cv2.imshow("mask", mask)
            cv2.imshow("result", result)

            key = cv2.waitKey(1) & 0xFF
            if key == ord("s"):
                print(f"HSV_LOWER = ({lower[0]}, {lower[1]}, {lower[2]})")
                print(f"HSV_UPPER = ({upper[0]}, {upper[1]}, {upper[2]})")
            elif key == ord("q"):
                break

    finally:
        pipeline.stop()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
