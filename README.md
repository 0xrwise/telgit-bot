# 🤖 Telgit-Bot

**Bot Telegram untuk mengelola repository GitHub — sepenuhnya lewat tombol, tanpa perintah ribet.**

Powered by **0xrwise**

---

## ✨ Apa yang Bisa Dilakukan Bot Ini?

### Fitur Utama
- 📂 **Lihat daftar repository** kamu, langsung dari chat Telegram
- 👆 **Pilih repo lewat tombol** — tidak perlu ketik nama repo satu-satu
- 📁 **Jelajahi folder & file** di dalam repo, selayaknya file manager
- ✏️ **Tambah, edit, dan hapus file** langsung dari HP kamu
- ➕ **Buat repository baru** (private/public, dengan/tanpa README, dengan `.gitignore` otomatis)

### Fitur Eksklusif (Belum Umum Ditemukan di Bot Sejenis)
| Fitur | Kegunaan |
|---|---|
| 🌿 **Manajemen Branch** | Lihat, pindah, dan buat branch baru langsung dari chat |
| 📜 **Riwayat Commit** | Lihat histori commit repo atau file tertentu |
| ↩️ **Undo Commit Terakhir** | "Rollback" cepat kalau commit terakhir salah |
| ⭐ **Star & 🍴 Fork** | Bintangi atau fork repo orang lain tanpa buka browser |
| 🔍 **Cari Kode dalam Repo** | Cari kata kunci di dalam file-file sebuah repo |
| 📦 **Download ZIP** | Dapat link download source code repo secara instan |
| 👀 **Watch Repository** | Bot otomatis kirim notifikasi kalau ada commit baru masuk (polling berkala) |
| 📤 **Quick Upload** | Kirim/forward dokumen ke bot dengan caption path file → langsung ter-commit ke repo aktif |

Semua navigasi memakai **tombol inline Telegram** — kamu tinggal tap, tidak perlu mengetik perintah `/perintah` untuk berpindah menu. Mengetik hanya diperlukan saat memang wajib, misalnya menulis isi file atau nama repo baru.

---

## 🖥️ Bisa Jalan di Mana Saja

Bot ini murni Python, jadi bisa dijalankan di:
- 📱 **Termux** (Android)
- 🐧 **Debian / Ubuntu / Linux lainnya**
- 🪟 **Windows** (via WSL atau langsung)
- ☁️ **VPS** apa pun (agar bot tetap online 24 jam)

---

## 🚀 Cara Instalasi

### 1. Siapkan Bot Telegram
1. Chat [@BotFather](https://t.me/BotFather) di Telegram
2. Ketik `/newbot`, ikuti instruksinya
3. Simpan **token** yang diberikan (bentuknya seperti `123456:ABC-DEF...`)

### 2. Download Project Ini
```bash
git clone https://github.com/username-kamu/telgit-bot.git
cd telgit-bot
```
*(Ganti `username-kamu` setelah kamu upload project ini ke GitHub-mu sendiri)*

### 3. Jalankan Installer Otomatis
Installer ini otomatis mendeteksi apakah kamu pakai Termux, Debian, atau lainnya:
```bash
chmod +x install.sh
./install.sh
```

### 4. Isi Token Bot
Buka file `.env` yang sudah dibuat otomatis, lalu isi:
```env
BOT_TOKEN=isi_token_dari_botfather_di_sini
```

### 5. Jalankan Bot
```bash
python bot.py
```
Kalau muncul log `Telgit-Bot berjalan...`, bot sudah aktif! 🎉

---

## 🔐 Menghubungkan Akun GitHub

Bot **tidak** memakai token GitHub milikmu (0xrwise) — setiap orang yang memakai bot ini menghubungkan **token GitHub-nya sendiri**, sehingga aman dan terpisah antar pengguna.

Caranya:
1. Chat bot kamu, ketik `/start`
2. Tekan tombol **🔑 Akun GitHub → 🔐 Hubungkan Token GitHub**
3. Buat Personal Access Token di https://github.com/settings/tokens
   - Pilih scope **`repo`** (akses penuh ke repository)
4. Salin & kirim token itu ke bot

Token disimpan **terenkripsi** di file lokal (`data/users.json`) menggunakan `cryptography` (Fernet), bukan di server pihak ketiga mana pun. Pesan berisi token juga otomatis dihapus dari chat setelah dikirim.

> ⚠️ **Penting:** Jangan pernah meng-upload folder `data/` atau file `.env` ke GitHub — keduanya sudah otomatis diabaikan lewat `.gitignore`.

---

## 📖 Cara Pakai Sehari-hari

```
/start
   └─ 📂 List Repository
         └─ (pilih repo) → 📄 Buka File/Folder
               └─ (pilih file) → ✏️ Edit Isi File
                     └─ ketik isi baru → ketik pesan commit → ✅ selesai!
```

Semua alur seperti di atas — cukup tap tombol, isi teks hanya saat diminta.

### Contoh: Membuat Repo Baru
1. Tekan **➕ Buat Repository Baru**
2. Ketik nama repo → ketik deskripsi (atau `-` untuk kosong)
3. Tekan **Private/Public** → **Ya/Lewati README** → pilih template `.gitignore`
4. Selesai, repo langsung jadi!

### Contoh: Memantau Repo (Watch)
1. Buka repo yang ingin dipantau
2. Tekan **👁️ Watch Repo Ini**
3. Setiap ada commit baru masuk ke repo itu, bot otomatis kirim notifikasi ke chat kamu — tanpa perlu cek manual.

### Contoh: Quick Upload
Kirim dokumen apa pun ke bot dengan **caption** berisi lokasi file di repo, misalnya:
```
docs/catatan.md
```
Selama repo sedang "aktif" (baru saja dibuka), bot langsung commit file itu ke path tersebut.

---

## 🛠️ Struktur Project

```
telgit-bot/
├── bot.py              # Entry point utama + semua handler
├── config.py           # Konfigurasi (.env, kunci enkripsi)
├── storage.py          # Penyimpanan token & watchlist user (lokal, terenkripsi)
├── github_service.py   # Semua fungsi ke GitHub API (lewat PyGithub)
├── keyboards.py        # Semua tombol inline Telegram
├── requirements.txt    # Daftar dependency Python
├── install.sh          # Installer otomatis (Termux/Debian/dll)
├── .env.example        # Contoh konfigurasi environment
└── data/                # (dibuat otomatis) token & watchlist tersimpan di sini
```

---

## ❓ Troubleshooting

**Bot tidak merespons sama sekali**
Pastikan `BOT_TOKEN` di `.env` sudah benar dan bot sedang `python bot.py` (tidak error di terminal).

**Notifikasi Watch Repo tidak muncul**
Pastikan `python-telegram-bot[job-queue]` sudah terinstall (bukan cuma `python-telegram-bot` polos). Jalankan ulang `pip install -r requirements.txt`.

**Token GitHub ditolak**
Pastikan token punya scope `repo` dan belum expired. Buat ulang di https://github.com/settings/tokens.

**Mau jalan 24 jam di Termux**
Pakai `termux-wake-lock` sebelum menjalankan bot, dan pertimbangkan `tmux`/`screen` supaya proses tidak mati saat aplikasi Termux ditutup:
```bash
pkg install tmux
tmux new -s telgitbot
python bot.py
# tekan Ctrl+B lalu D untuk keluar tanpa mematikan bot
```

**Mau jalan 24 jam di VPS**
Gunakan `systemd` atau `pm2`/`tmux` agar bot otomatis restart jika crash atau server reboot.

---

## 📜 Lisensi & Kredit

Dibuat dan dikembangkan oleh **0xrwise**.
Silakan gunakan, modifikasi, dan sebarkan — jangan lupa cantumkan kredit ya! 🙏

---

**Selamat mencoba Telgit-Bot! Kalau ada ide fitur tambahan, tinggal kembangkan sendiri dari struktur kode yang sudah rapi ini.** 🚀
