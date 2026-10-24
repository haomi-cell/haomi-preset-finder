# HAOMI Preset Finder

Pencari video TikTok bertema preset Alight Motion. Frontend menerima kata kunci, username, atau URL video; hasil video dapat dibuka untuk melihat metadata, statistik publik yang tersedia, deskripsi, tautan preset, dan komentar yang diberikan sumber data. XML dapat diambil dan dipreview secara terbatas di browser.

## Struktur

- `pages/index.html` — frontend Cloudflare Pages (file utama yang dipublikasikan).
- `public/preset-finder.html` — salinan frontend lama yang diselaraskan.
- `api/preset-finder/*.js` — Vercel Functions untuk resolve, search, user, dan proxy XML.
- `backend-server/search_server.py` — backend Python untuk pencarian/akun TikTok menggunakan Scrapling.

## Penting: dua layanan diperlukan

Cloudflare Pages static **tidak menjalankan** Python atau Vercel Functions di folder `api/`. Agar semua fungsi bekerja, deploy frontend dan backend/API secara terpisah:

1. **Backend Python**: deploy `backend-server/search_server.py` ke host Python yang mendukung browser Chromium untuk Scrapling. Set `PORT` sesuai platform. Install dependensi Scrapling dan browser yang diperlukan oleh versi Scrapling tersebut. Endpoint health: `/health`.
2. **Vercel API** (disarankan untuk endpoint `api/preset-finder/*.js`): deploy repo ini ke Vercel. Tambahkan environment variable `HAOMI_BACKEND_URL` berisi URL HTTPS publik backend Python, tanpa slash di akhir. Jangan gunakan URL tunnel sementara `trycloudflare.com` sebagai URL produksi.
3. **Cloudflare Pages frontend**: di `pages/index.html`, ubah meta `haomi-api-base` menjadi URL API Vercel, misalnya `https://NAMA-PROYEK.vercel.app/api/preset-finder`. Deploy folder `pages` sebagai output/static directory sesuai konfigurasi proyek Pages.
4. Pastikan API dan backend dapat diakses publik melalui HTTPS. Backend mengaktifkan CORS; untuk produksi, batasi `Access-Control-Allow-Origin` ke domain frontend.

Jika ingin menjalankan backend lokal:

```bash
python -m pip install scrapling
scrapling install
python backend-server/search_server.py
```

Lalu backend mendengarkan port `8901` secara default. Endpoint `/health` dapat dipakai untuk tes. Ketersediaan scraping tetap bergantung pada perubahan situs TikTok, jaringan, dan sumber data publik.

## Fitur dan batasan

- Pencarian kata kunci, username, dan URL video.
- Detail publik: akun, deskripsi, waktu unggah WIB, resolusi, durasi, like, komentar, share, views, dan statistik lain bila disediakan sumber.
- Ekstraksi URL dari deskripsi dan komentar yang tersedia melalui sumber data.
- Batas file XML 5 MB di proxy. File ZIP tetap dapat dibuka sebagai tautan, tetapi preview canvas hanya membaca XML dan hanya menggambar sebagian elemen/shape; preview bukan renderer penuh Alight Motion.
- TikTok tidak selalu menyediakan lokasi, komentar, statistik simpan/download, atau semua metadata. Field yang tidak tersedia ditampilkan sebagai `—`/`unknown`, bukan ditebak.

## Pemeriksaan cepat

- Buka `https://URL-BACKEND/health` — harus mengembalikan JSON `status: true`.
- Buka URL API Vercel `/api/preset-finder/resolve` dengan metode POST dan body JSON `{"video":"URL_VIDEO_TIKTOK"}`.
- Pastikan meta `haomi-api-base` pada frontend menunjuk ke base API yang benar.
