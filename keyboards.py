"""
Semua inline keyboard (tombol) Telgit-Bot dikumpulkan di sini.
Filosofi UI: 100% tombol, nyaris tanpa perintah ketik manual (kecuali saat
memang wajib memasukkan teks, misal isi file atau nama repo baru).
"""
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

PAGE_SIZE = 8


def paginate(items, page, page_size=PAGE_SIZE):
    start = page * page_size
    end = start + page_size
    return items[start:end], (end < len(items)), (page > 0)


def main_menu_kb():
    rows = [
        [InlineKeyboardButton("📂 List Repository", callback_data="repo:list:0")],
        [InlineKeyboardButton("➕ Buat Repository Baru", callback_data="repo:new")],
        [InlineKeyboardButton("👀 Repo yang Dipantau (Watch)", callback_data="watch:list")],
        [InlineKeyboardButton("🔑 Akun GitHub", callback_data="account:menu")],
        [InlineKeyboardButton("ℹ️ Tentang Bot", callback_data="about")],
    ]
    return InlineKeyboardMarkup(rows)


def back_kb(callback_data="menu:main", label="🔙 Kembali"):
    return InlineKeyboardMarkup([[InlineKeyboardButton(label, callback_data=callback_data)]])


def account_menu_kb(logged_in: bool):
    rows = []
    if logged_in:
        rows.append([InlineKeyboardButton("🚪 Logout / Ganti Token", callback_data="account:logout")])
    else:
        rows.append([InlineKeyboardButton("🔐 Hubungkan Token GitHub", callback_data="account:login")])
    rows.append([InlineKeyboardButton("🔙 Menu Utama", callback_data="menu:main")])
    return InlineKeyboardMarkup(rows)


def repo_list_kb(repos, page):
    page_items, has_next, has_prev = paginate(repos, page)
    rows = []
    for idx, r in enumerate(page_items):
        icon = "🔒" if r.private else "📁"
        real_idx = page * PAGE_SIZE + idx
        rows.append([InlineKeyboardButton(f"{icon} {r.name}", callback_data=f"repo:open:{real_idx}")])
    nav = []
    if has_prev:
        nav.append(InlineKeyboardButton("⬅️ Sebelumnya", callback_data=f"repo:list:{page-1}"))
    if has_next:
        nav.append(InlineKeyboardButton("➡️ Berikutnya", callback_data=f"repo:list:{page+1}"))
    if nav:
        rows.append(nav)
    rows.append([InlineKeyboardButton("🔍 Cari Repo", callback_data="repo:search_repo")])
    rows.append([InlineKeyboardButton("🔙 Menu Utama", callback_data="menu:main")])
    return InlineKeyboardMarkup(rows)


def repo_menu_kb(is_starred=False):
    star_label = "⭐ Unstar" if is_starred else "☆ Star Repo"
    rows = [
        [InlineKeyboardButton("📄 Buka File / Folder", callback_data="dir:open:root")],
        [InlineKeyboardButton("➕ Tambah File Baru", callback_data="file:new_here")],
        [InlineKeyboardButton("📊 Info Repository", callback_data="repo:info")],
        [InlineKeyboardButton("🌿 Branch", callback_data="branch:list"),
         InlineKeyboardButton("📜 Riwayat Commit", callback_data="commit:list")],
        [InlineKeyboardButton("🔍 Cari Kode di Repo", callback_data="repo:codesearch"),
         InlineKeyboardButton("📦 Download ZIP", callback_data="repo:zip")],
        [InlineKeyboardButton(star_label, callback_data="repo:togglestar"),
         InlineKeyboardButton("🍴 Fork", callback_data="repo:fork")],
        [InlineKeyboardButton("↩️ Undo Commit Terakhir", callback_data="repo:revert")],
        [InlineKeyboardButton("👁️ Watch Repo Ini", callback_data="watch:add"),
         InlineKeyboardButton("🗑️ Hapus Repository", callback_data="repo:delete_confirm")],
        [InlineKeyboardButton("🔙 List Repository", callback_data="repo:list:0")],
    ]
    return InlineKeyboardMarkup(rows)


def confirm_kb(yes_cb, no_cb, yes_label="✅ Ya, lanjutkan", no_label="❌ Batal"):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(yes_label, callback_data=yes_cb),
         InlineKeyboardButton(no_label, callback_data=no_cb)],
    ])


def dir_listing_kb(entries, page, current_path):
    page_items, has_next, has_prev = paginate(entries, page)
    rows = []
    for idx, item in enumerate(page_items):
        real_idx = page * PAGE_SIZE + idx
        icon = "📁" if item.type == "dir" else "📄"
        if item.type == "dir":
            rows.append([InlineKeyboardButton(f"{icon} {item.name}/", callback_data=f"dir:open:{real_idx}")])
        else:
            rows.append([InlineKeyboardButton(f"{icon} {item.name}", callback_data=f"file:open:{real_idx}")])
    nav = []
    if has_prev:
        nav.append(InlineKeyboardButton("⬅️", callback_data=f"dir:page:{page-1}"))
    if has_next:
        nav.append(InlineKeyboardButton("➡️", callback_data=f"dir:page:{page+1}"))
    if nav:
        rows.append(nav)
    action_row = [InlineKeyboardButton("➕ File Baru di Sini", callback_data="file:new_here")]
    rows.append(action_row)
    if current_path:
        rows.append([InlineKeyboardButton("⬆️ Naik Satu Folder", callback_data="dir:up")])
    rows.append([InlineKeyboardButton("🔙 Menu Repository", callback_data="repo:reopen")])
    return InlineKeyboardMarkup(rows)


def file_menu_kb():
    rows = [
        [InlineKeyboardButton("👁️ Lihat Isi", callback_data="file:view")],
        [InlineKeyboardButton("✏️ Edit Isi File", callback_data="file:edit")],
        [InlineKeyboardButton("📜 Riwayat File", callback_data="file:history")],
        [InlineKeyboardButton("🗑️ Hapus File", callback_data="file:delete_confirm")],
        [InlineKeyboardButton("🔙 Kembali ke Folder", callback_data="dir:reopen")],
    ]
    return InlineKeyboardMarkup(rows)


def branch_list_kb(branches, current_default):
    rows = []
    for idx, b in enumerate(branches):
        tag = " (default)" if b.name == current_default else ""
        rows.append([InlineKeyboardButton(f"🌿 {b.name}{tag}", callback_data=f"branch:switch:{idx}")])
    rows.append([InlineKeyboardButton("➕ Buat Branch Baru", callback_data="branch:new")])
    rows.append([InlineKeyboardButton("🔙 Menu Repository", callback_data="repo:reopen")])
    return InlineKeyboardMarkup(rows)


def yesno_private_kb():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔒 Private", callback_data="newrepo:private:1"),
         InlineKeyboardButton("🌐 Public", callback_data="newrepo:private:0")],
    ])


def yesno_readme_kb():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Ya, buat README", callback_data="newrepo:readme:1"),
         InlineKeyboardButton("⏭️ Lewati", callback_data="newrepo:readme:0")],
    ])


def gitignore_template_kb():
    templates = ["None", "Python", "Node", "Java", "Go", "C++"]
    rows = []
    row = []
    for i, t in enumerate(templates):
        row.append(InlineKeyboardButton(t, callback_data=f"newrepo:gitignore:{t}"))
        if len(row) == 3:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    return InlineKeyboardMarkup(rows)


def watchlist_kb(watch_items):
    rows = []
    for name in watch_items:
        rows.append([InlineKeyboardButton(f"👁️ {name}", callback_data=f"watch:info:{name}")])
    rows.append([InlineKeyboardButton("🔙 Menu Utama", callback_data="menu:main")])
    return InlineKeyboardMarkup(rows)


def watch_info_kb(repo_name):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🛑 Berhenti Memantau", callback_data=f"watch:remove:{repo_name}")],
        [InlineKeyboardButton("🔙 Daftar Pantauan", callback_data="watch:list")],
    ])
