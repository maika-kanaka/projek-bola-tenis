"""
Konfigurasi untuk Wall Interactive Ball Tracker.
Sesuaikan nilai-nilai ini sesuai kondisi venue & bola yang dipakai.
"""

# === RealSense stream settings ===
FRAME_WIDTH = 640
FRAME_HEIGHT = 480
FRAME_RATE = 60  # fps — makin tinggi makin bagus untuk bola cepat (cek limit device di resolusi ini)

# === Deteksi bola berbasis warna (HSV) ===
# Default: kuning terang. Sesuaikan dengan warna bola yang dipakai,
# gunakan tools/hsv_picker.py untuk mencari range yang pas.
HSV_LOWER = (20, 100, 100)
HSV_UPPER = (35, 255, 255)

MIN_BALL_RADIUS_PX = 4      # radius minimum blob (pixel) supaya noise kefilter
MAX_BALL_RADIUS_PX = 60     # radius maksimum blob (pixel)

# Kontrol tambahan untuk filter bentuk: circularity = 4*pi*area / perimeter^2
# Nilai 1.0 berarti lingkaran sempurna. Turunkan kalau bola sering terpotong
# oleh tepi frame atau tertutup parsial.
MIN_CIRCULARITY = 0.65

# === Optional AI detector ===
# Jika True, tracker akan mencoba menggunakan detector AI (`ai_ball_detector.py`).
# Jika torch/timbang model tidak tersedia, sistem akan fallback ke deteksi warna.
USE_AI_DETECTOR = False
AI_CONF_THRESHOLD = 0.35

# === Kalibrasi bidang dinding ===
# Diisi otomatis oleh calibrate.py. Bisa juga diisi manual (dalam meter).
WALL_DISTANCE_M = None
WALL_CALIBRATION_FILE = "wall_calibration.json"

# ROI dinding (4 titik klik): [top-left, top-right, bottom-right, bottom-left]
# dipakai untuk memetakan koordinat bola dari frame kamera ke koordinat monitor.
WALL_ROI_POINTS = None

# Jika True, mouse akan dipindahkan ke posisi hit yang dipetakan ke layar saat bola mengenai dinding.
MOVE_MOUSE_ON_HIT = True
MOUSE_SCREEN_WIDTH = 1920
MOUSE_SCREEN_HEIGHT = 1080

# Toleransi "hit": bola dianggap kena dinding kalau depth-nya berada
# dalam WALL_DISTANCE_M +/- HIT_THRESHOLD_M
HIT_THRESHOLD_M = 0.15

# Jarak minimum & maksimum area main (meter) dari kamera,
# dipakai untuk memfilter noise di luar area bermain
PLAY_AREA_MIN_M = 0.3
PLAY_AREA_MAX_M = 6.0

# === Tracking ===
MAX_TRACK_GAP_FRAMES = 5     # berapa frame boleh "hilang" sebelum track dianggap putus
MIN_TRACK_LENGTH = 3         # minimum jumlah titik sebelum track dianggap valid (kurangi false positive)

HIT_COOLDOWN_S = 0.5         # jeda antar hit (detik) biar 1 lemparan tidak terhitung berkali-kali

# === Debug ===
SHOW_DEBUG_WINDOW = True
