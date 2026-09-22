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

# === Kalibrasi bidang dinding ===
# Diisi otomatis oleh calibrate.py. Bisa juga diisi manual (dalam meter).
WALL_DISTANCE_M = None
WALL_CALIBRATION_FILE = "wall_calibration.json"

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

# === OSC output ===
OSC_IP = "127.0.0.1"
OSC_PORT = 7000
OSC_ADDRESS_HIT = "/wall/hit"

# === Debug ===
SHOW_DEBUG_WINDOW = True
