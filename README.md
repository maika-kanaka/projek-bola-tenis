# Wall Interactive — Ball Tracker Prototype

Prototipe deteksi bola + hit detection untuk project wall interactive
menggunakan Intel RealSense (langkah "Prototipe deteksi bola" & "Trajectory
tracking & hit trigger" di roadmap).

## Struktur file
- `config.py` — semua parameter yang perlu ditune (HSV, threshold, OSC, dll)
- `calibrate.py` — ukur jarak dinding & ROI dinding (jalankan sekali di awal, dinding kosong)
- `ball_tracker.py` — deteksi bola real-time, tracking, kirim event OSC saat hit
- `tools/hsv_picker.py` — alat bantu cari warna HSV bola secara visual

## Instalasi

```bash
pip install -r requirements.txt
```

Catatan: `pyrealsense2` butuh Intel RealSense SDK (librealsense) terpasang
di sistem. Kalau `pip install pyrealsense2` gagal di platform kamu (misal
ARM/Raspberry Pi), install librealsense dari sumber sesuai dokumentasi
resmi Intel RealSense.

## Urutan pemakaian

1. **Cari warna bola**

   ```bash
   python tools/hsv_picker.py
   ```

   Arahkan bola ke kamera, geser trackbar sampai hanya bola yang putih di
   window "mask". Tekan `s` untuk cetak nilai HSV, salin ke `HSV_LOWER` /
   `HSV_UPPER` di `config.py`.

2. **Kalibrasi jarak dinding** (pastikan dinding kosong, tanpa orang/bola)

   ```bash
   python calibrate.py
   ```

   Hasil tersimpan di `wall_calibration.json`.

3. **Jalankan tracker**

   ```bash
   python ball_tracker.py
   ```

   Window debug menampilkan bola yang terdeteksi (lingkaran hijau), jejak
   trajectory (garis biru), dan lingkaran merah saat hit terdeteksi. Event
   hit dikirim via OSC ke `127.0.0.1:7000` address `/wall/hit` dengan
   payload `(x_norm, y_norm, speed_m_s)`.

## Catatan penting

- `x_norm, y_norm` masih dalam koordinat frame kamera (0.0–1.0), **belum**
  dipetakan ke koordinat proyektor. Mapping ke koordinat proyektor
  (homography) adalah langkah kalibrasi terpisah dari roadmap ("Bangun
  routine kalibrasi") yang bisa ditambahkan setelah proyektor terpasang
  di venue.
- Estimasi speed masih kasar (berbasis perubahan depth antar-frame),
  cukup untuk keperluan gameplay (misal skor lebih tinggi kalau lemparan
  lebih keras), bukan pengukuran ilmiah presisi.
- Kalau bola terlalu cepat & sering "lolos" dari deteksi hit, coba:
  - Naikkan `FRAME_RATE` (kalau RealSense mendukung di resolusi tsb)
  - Perbesar `HIT_THRESHOLD_M`
  - Turunkan `MIN_TRACK_LENGTH`
- Untuk menerima OSC di TouchDesigner: pakai **OSC In CHOP**, set port
  sesuai `OSC_PORT`. Di Unity: pakai library seperti extOSC atau UnityOSC.
