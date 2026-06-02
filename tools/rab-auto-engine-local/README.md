# RAB Otomatis

Local-first MVP untuk otomasi RAB dari PDF denah. Modul ini tidak memakai API berbayar dan tidak mengunggah data ke cloud.

## Cara Menjalankan

```powershell
cd "C:\Users\user\Documents\New project 5\tools\rab-auto-engine-local"
python -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements.txt
.\.venv\Scripts\python -m uvicorn backend.app:app --host 127.0.0.1 --port 8787 --reload
```

Di komputer ini interpreter `python` default terdeteksi tidak lengkap karena modul standard library `tempfile` tidak tersedia. Jika perintah venv gagal, jalankan script helper yang otomatis memakai runtime Python Codex jika tersedia:

```powershell
.\start-rab-otomatis.ps1
```

Buka:

```text
http://127.0.0.1:8787
```

## Fitur MVP

- Project Manager lokal dengan SQLite.
- Upload PDF dan rasterize ke PNG thumbnail/halaman memakai PyMuPDF.
- Viewer denah dengan overlay dinding, ruang, OCR, MEP, jalur, dan bukaan.
- Klasifikasi halaman dan kalibrasi skala manual/dua titik.
- Deteksi dinding OpenCV.
- Deteksi ruang OpenCV.
- OCR Tesseract jika executable Tesseract tersedia di PATH.
- Manual tagging MEP dan adapter YOLO lokal opsional di `models/mep_symbols.pt`.
- Export dataset MEP ke JSON, YOLO label TXT, dan `data.yaml`.
- Pengukuran jalur manual.
- Input struktur manual.
- Formula library starter dan safe formula engine tanpa `eval`.
- Generate draft RAB, edit volume/harga/catatan, confirm, lock/manual override.
- Database harga lokal, input manual, import/export CSV.
- Audit missing data, low confidence, harga kosong, kalibrasi kosong, data belum confirm.
- Export RAB CSV, RAB JSON, printable HTML, audit JSON.
- Diagnostik dependency lokal.

## Dependency Opsional

- Tesseract OCR: diperlukan hanya untuk OCR. Jika tidak ada, fitur OCR menampilkan status missing dan fitur lain tetap berjalan.
- Ultralytics + model `models/mep_symbols.pt`: diperlukan hanya untuk YOLO MEP. Jika tidak ada, gunakan manual tagging.
- Ollama: dideteksi di diagnostik, belum menjadi sumber wajib.

## Catatan Akurasi

Semua output otomatis adalah draft. Item hasil OpenCV/OCR/YOLO diberi source, confidence, status, dan harus dikonfirmasi pengguna. Missing data tidak diubah diam-diam menjadi final quantity.
