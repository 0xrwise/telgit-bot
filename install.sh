#!/usr/bin/env bash
# ============================================================
#  Telgit-Bot Installer — Universal (Termux, Debian, Ubuntu, dll)
#  Powered by 0xrwise
# ============================================================
set -e

echo "================================================"
echo "   🚀 Telgit-Bot Installer — by 0xrwise"
echo "================================================"

# Deteksi lingkungan
if [ -n "$PREFIX" ] && [[ "$PREFIX" == *"com.termux"* ]]; then
    ENV_TYPE="termux"
    echo "📱 Lingkungan terdeteksi: Termux"
elif [ -f /etc/debian_version ]; then
    ENV_TYPE="debian"
    echo "🐧 Lingkungan terdeteksi: Debian/Ubuntu"
else
    ENV_TYPE="generic"
    echo "💻 Lingkungan terdeteksi: Generic Linux/Unix"
fi

# Install Python & pip sesuai lingkungan
case "$ENV_TYPE" in
    termux)
        pkg update -y && pkg upgrade -y
        pkg install -y python git
        ;;
    debian)
        sudo apt update -y
        sudo apt install -y python3 python3-pip python3-venv git
        ;;
    generic)
        echo "⚠️ Pastikan python3, pip, dan git sudah terpasang manual."
        ;;
esac

PYTHON_BIN=$(command -v python3 || command -v python)

echo "🐍 Menggunakan: $($PYTHON_BIN --version)"

# Buat virtual environment (kecuali di Termux yang kadang bermasalah dengan venv, tapi tetap dicoba)
if [ ! -d ".venv" ]; then
    echo "📦 Membuat virtual environment..."
    $PYTHON_BIN -m venv .venv || echo "⚠️ Gagal buat venv, lanjut pakai python3 global."
fi

if [ -d ".venv" ]; then
    source .venv/bin/activate
    echo "✅ Virtual environment aktif."
fi

echo "📥 Menginstall dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# Siapkan file .env jika belum ada
if [ ! -f ".env" ]; then
    cp .env.example .env
    echo ""
    echo "📝 File .env telah dibuat dari .env.example."
    echo "   Silakan edit file .env dan isi BOT_TOKEN dari @BotFather."
fi

mkdir -p data

echo ""
echo "================================================"
echo "✅ Instalasi selesai!"
echo ""
echo "Langkah selanjutnya:"
echo "  1. Edit file .env → isi BOT_TOKEN"
echo "  2. Jalankan bot dengan:"
if [ -d ".venv" ]; then
    echo "       source .venv/bin/activate && python bot.py"
else
    echo "       python3 bot.py"
fi
echo "================================================"
