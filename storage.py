"""
Penyimpanan data user secara lokal (data/users.json).
Token GitHub dienkripsi memakai Fernet (jika library `cryptography` tersedia).
"""
import json
import threading
from config import USERS_DB_FILE, get_or_create_key

_lock = threading.RLock()

try:
    from cryptography.fernet import Fernet
    _key = get_or_create_key()
    _fernet = Fernet(_key) if _key else None
except ImportError:
    _fernet = None


def _encrypt(text: str) -> str:
    if not text:
        return ""
    if _fernet:
        return "enc:" + _fernet.encrypt(text.encode()).decode()
    return "plain:" + text


def _decrypt(text: str) -> str:
    if not text:
        return ""
    if text.startswith("plain:"):
        return text[len("plain:"):]
    if text.startswith("enc:") and _fernet:
        try:
            return _fernet.decrypt(text[len("enc:"):].encode()).decode()
        except Exception:
            return ""
    return ""


def _load() -> dict:
    if not USERS_DB_FILE.exists():
        return {}
    try:
        with open(USERS_DB_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _save(data: dict):
    tmp = USERS_DB_FILE.with_suffix(".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    tmp.replace(USERS_DB_FILE)


def set_token(user_id: int, token: str, username: str = None):
    with _lock:
        data = _load()
        uid = str(user_id)
        data.setdefault(uid, {})
        data[uid]["token"] = _encrypt(token)
        if username:
            data[uid]["github_username"] = username
        _save(data)


def get_token(user_id: int):
    with _lock:
        data = _load()
        enc = data.get(str(user_id), {}).get("token")
        return _decrypt(enc) if enc else None


def remove_token(user_id: int):
    with _lock:
        data = _load()
        uid = str(user_id)
        if uid in data:
            data[uid].pop("token", None)
            _save(data)


def has_token(user_id: int) -> bool:
    return bool(get_token(user_id))


# ---------- Fitur "Watch Repository" (notifikasi commit baru) ----------

def get_watchlist(user_id: int) -> dict:
    with _lock:
        data = _load()
        return dict(data.get(str(user_id), {}).get("watch", {}))


def set_watch(user_id: int, repo_full_name: str, sha: str):
    with _lock:
        data = _load()
        uid = str(user_id)
        data.setdefault(uid, {})
        data[uid].setdefault("watch", {})
        data[uid]["watch"][repo_full_name] = sha
        _save(data)


def unwatch(user_id: int, repo_full_name: str):
    with _lock:
        data = _load()
        uid = str(user_id)
        if uid in data and repo_full_name in data[uid].get("watch", {}):
            del data[uid]["watch"][repo_full_name]
            _save(data)


def all_watchers() -> dict:
    """Kembalikan {user_id_str: {repo_full_name: last_sha}} untuk keperluan polling job."""
    with _lock:
        data = _load()
        result = {}
        for uid, info in data.items():
            w = info.get("watch")
            if w:
                result[uid] = dict(w)
        return result


# ---------- Preferensi umum ----------

def set_pref(user_id: int, key: str, value):
    with _lock:
        data = _load()
        uid = str(user_id)
        data.setdefault(uid, {})
        data[uid].setdefault("prefs", {})
        data[uid]["prefs"][key] = value
        _save(data)


def get_pref(user_id: int, key: str, default=None):
    with _lock:
        data = _load()
        return data.get(str(user_id), {}).get("prefs", {}).get(key, default)
