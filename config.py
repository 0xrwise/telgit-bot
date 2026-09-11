"""
Konfigurasi utama Telgit-Bot.
Membaca variabel dari file .env dan menyiapkan folder data + kunci enkripsi.
"""
import os
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()

# Jika diisi, hanya user ID ini (pisahkan koma) yang boleh pakai bot.
# Kosongkan untuk mengizinkan siapa saja mendaftarkan token GitHub-nya sendiri.
_raw_allowed = os.getenv("ALLOWED_USERS", "").strip()
ALLOWED_USERS = {u.strip() for u in _raw_allowed.split(",") if u.strip()}

ENCRYPTION_KEY_FILE = DATA_DIR / "secret.key"
USERS_DB_FILE = DATA_DIR / "users.json"

# Interval polling untuk fitur "Watch Repository" (deteksi commit baru), dalam detik.
WATCH_INTERVAL_SECONDS = int(os.getenv("WATCH_INTERVAL_SECONDS", "300"))

BOT_NAME = "Telgit-Bot"
BOT_AUTHOR = "0xrwise"

# Batas ukuran file yang boleh ditampilkan/diedit langsung di chat (byte).
# GitHub Contents API sendiri punya batas ~1MB untuk base64 content.
MAX_FILE_VIEW_SIZE = 60_000
MAX_FILE_EDIT_SIZE = 900_000


def get_or_create_key():
    """Ambil (atau buat) kunci enkripsi lokal untuk menyimpan token GitHub user."""
    try:
        from cryptography.fernet import Fernet
    except ImportError:
        return None
    if ENCRYPTION_KEY_FILE.exists():
        return ENCRYPTION_KEY_FILE.read_bytes()
    key = Fernet.generate_key()
    ENCRYPTION_KEY_FILE.write_bytes(key)
    try:
        os.chmod(ENCRYPTION_KEY_FILE, 0o600)
    except Exception:
        pass
    return key


def is_allowed(user_id: int) -> bool:
    if not ALLOWED_USERS:
        return True
    return str(user_id) in ALLOWED_USERS
