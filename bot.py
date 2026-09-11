"""
Telgit-Bot — Bot Telegram untuk mengelola repository GitHub sepenuhnya lewat tombol.
Powered by 0xrwise.

Fitur inti  : list, buat, hapus repo | browse folder | tambah/edit/hapus file
Fitur ekstra: branch manager, riwayat commit, undo commit, star/fork,
              pencarian kode dalam repo, download ZIP, watch-repo (notifikasi
              commit baru otomatis), quick-upload lewat forward dokumen.
"""
import logging
import base64
from datetime import datetime

from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler, MessageHandler,
    ConversationHandler, ContextTypes, filters,
)
from github import GithubException

import config
import storage
import keyboards as kb
from github_service import GH

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger("telgit-bot")

# ---- Conversation states ----
(
    ASK_TOKEN, ASK_REPO_NAME, ASK_REPO_DESC, ASK_FILE_NAME, ASK_FILE_CONTENT,
    ASK_COMMIT_MSG, ASK_CODE_SEARCH, ASK_BRANCH_NAME, ASK_REPO_SEARCH,
) = range(9)


# ================= Helper umum =================

def get_gh(context: ContextTypes.DEFAULT_TYPE, user_id: int):
    """Ambil instance GH dari cache di user_data, atau buat baru dari token tersimpan."""
    gh = context.user_data.get("gh")
    if gh:
        return gh
    token = storage.get_token(user_id)
    if not token:
        return None
    gh = GH(token)
    context.user_data["gh"] = gh
    return gh


async def require_login(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    gh = get_gh(context, user_id)
    if gh is None:
        text = (
            "🔐 Kamu belum menghubungkan akun GitHub.\n\n"
            "Tekan tombol di bawah untuk memasukkan Personal Access Token (PAT)."
        )
        target = update.callback_query.message if update.callback_query else update.message
        await target.reply_text(text, reply_markup=kb.account_menu_kb(False))
        return None
    return gh


async def edit_or_send(update: Update, text, reply_markup=None, parse_mode=None):
    q = update.callback_query
    if q:
        try:
            await q.edit_message_text(text, reply_markup=reply_markup, parse_mode=parse_mode,
                                       disable_web_page_preview=True)
        except Exception:
            await q.message.reply_text(text, reply_markup=reply_markup, parse_mode=parse_mode,
                                        disable_web_page_preview=True)
    else:
        await update.message.reply_text(text, reply_markup=reply_markup, parse_mode=parse_mode,
                                         disable_web_page_preview=True)


def fmt_size(n):
    if n < 1024:
        return f"{n} B"
    if n < 1024 * 1024:
        return f"{n/1024:.1f} KB"
    return f"{n/1024/1024:.1f} MB"


# ================= /start & Menu Utama =================

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not config.is_allowed(user_id):
        await update.message.reply_text("🚫 Maaf, kamu tidak diizinkan memakai bot ini.")
        return
    name = update.effective_user.first_name or "Sobat"
    text = (
        f"👋 Halo, {name}!\n\n"
        f"Selamat datang di *{config.BOT_NAME}* — kelola repository GitHub-mu "
        f"langsung dari Telegram, cukup lewat tombol, tanpa perintah ribet.\n\n"
        f"_Powered by {config.BOT_AUTHOR}_"
    )
    await update.message.reply_text(text, reply_markup=kb.main_menu_kb(), parse_mode=ParseMode.MARKDOWN)


async def cb_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.pop("nav", None)
    await edit_or_send(update, f"🏠 *Menu Utama {config.BOT_NAME}*\n\nPilih salah satu fitur di bawah:",
                        kb.main_menu_kb(), ParseMode.MARKDOWN)


async def cb_about(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        f"🤖 *{config.BOT_NAME}*\n"
        f"Powered by *{config.BOT_AUTHOR}*\n\n"
        "Bot manajemen GitHub berbasis tombol penuh:\n"
        "• List, buat, hapus repository\n"
        "• Jelajah folder & file, tambah/edit/hapus\n"
        "• Manajemen branch & riwayat commit\n"
        "• Undo commit terakhir\n"
        "• Star / Fork repository\n"
        "• Pencarian kode dalam repo\n"
        "• Download ZIP repo\n"
        "• Watch repo — notifikasi otomatis saat ada commit baru\n"
        "• Quick upload — forward dokumen untuk langsung commit\n"
    )
    await edit_or_send(update, text, kb.back_kb(), ParseMode.MARKDOWN)


# ================= Akun / Token GitHub =================

async def cb_account_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    logged_in = storage.has_token(user_id)
    extra = ""
    if logged_in:
        gh = get_gh(context, user_id)
        try:
            login = gh.verify()
            extra = f"\n\n✅ Terhubung sebagai: *{login}*"
        except Exception:
            extra = "\n\n⚠️ Token tersimpan tapi sepertinya tidak valid lagi."
    text = "🔑 *Akun GitHub*" + extra
    await edit_or_send(update, text, kb.account_menu_kb(logged_in), ParseMode.MARKDOWN)


async def cb_account_login(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "🔐 Kirimkan *Personal Access Token* (PAT) GitHub-mu.\n\n"
        "Cara membuat token:\n"
        "1. Buka https://github.com/settings/tokens\n"
        "2. Generate new token (classic atau fine-grained)\n"
        "3. Centang scope `repo` (akses penuh ke repository)\n"
        "4. Salin token, lalu kirim ke sini\n\n"
        "🔒 Token disimpan terenkripsi di server/perangkatmu sendiri, tidak dibagikan ke siapa pun.\n\n"
        "Ketik /cancel untuk batal."
    )
    await edit_or_send(update, text, parse_mode=ParseMode.MARKDOWN)
    return ASK_TOKEN


async def receive_token(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    token = update.message.text.strip()
    try:
        await update.message.delete()
    except Exception:
        pass
    msg = await update.message.reply_text("⏳ Memverifikasi token...")
    gh = GH(token)
    try:
        login = gh.verify()
    except Exception as e:
        await msg.edit_text(f"❌ Token tidak valid atau gagal terhubung.\n`{e}`", parse_mode=ParseMode.MARKDOWN)
        return ConversationHandler.END
    storage.set_token(user_id, token, username=login)
    context.user_data["gh"] = gh
    await msg.edit_text(f"✅ Berhasil terhubung sebagai *{login}*!", parse_mode=ParseMode.MARKDOWN,
                         reply_markup=kb.main_menu_kb())
    return ConversationHandler.END


async def cb_account_logout(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    storage.remove_token(user_id)
    context.user_data.pop("gh", None)
    await edit_or_send(update, "🚪 Token dihapus. Hubungkan token baru kapan saja.",
                        kb.account_menu_kb(False))


# ================= List / Buka Repository =================

async def cb_repo_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    gh = await require_login(update, context)
    if not gh:
        return
    page = int(update.callback_query.data.split(":")[-1])
    try:
        repos = context.user_data.get("repo_cache")
        if repos is None:
            await update.callback_query.answer("Memuat daftar repo...")
            repos = gh.list_repos()
            context.user_data["repo_cache"] = repos
    except GithubException as e:
        await edit_or_send(update, f"❌ Gagal mengambil daftar repo: {e.data.get('message', e)}", kb.back_kb())
        return
    if not repos:
        await edit_or_send(update, "📭 Kamu belum punya repository apa pun.", kb.main_menu_kb())
        return
    text = f"📂 *Repository kamu* ({len(repos)} total)\nHalaman {page+1}"
    await edit_or_send(update, text, kb.repo_list_kb(repos, page), ParseMode.MARKDOWN)


async def cb_repo_open(update: Update, context: ContextTypes.DEFAULT_TYPE):
    idx = int(update.callback_query.data.split(":")[-1])
    repos = context.user_data.get("repo_cache") or []
    if idx >= len(repos):
        await update.callback_query.answer("Data kedaluwarsa, muat ulang list ya.", show_alert=True)
        return
    repo = repos[idx]
    context.user_data["current_repo"] = repo.full_name
    context.user_data["current_branch"] = None
    context.user_data["current_path"] = ""
    await open_repo_menu(update, context)


async def open_repo_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    gh = get_gh(context, update.effective_user.id)
    full_name = context.user_data.get("current_repo")
    starred = False
    try:
        starred = gh.is_starred(full_name)
    except Exception:
        pass
    text = f"📁 *{full_name}*\n\nPilih aksi:"
    await edit_or_send(update, text, kb.repo_menu_kb(starred), ParseMode.MARKDOWN)


async def cb_repo_reopen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await open_repo_menu(update, context)


async def cb_repo_search_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await edit_or_send(update, "🔍 Ketik nama repo (atau sebagian nama) yang ingin dicari:")
    return ASK_REPO_SEARCH


async def receive_repo_search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.message.text.strip().lower()
    repos = context.user_data.get("repo_cache") or []
    filtered = [r for r in repos if query in r.name.lower()]
    if not filtered:
        await update.message.reply_text("😕 Tidak ada repo yang cocok.", reply_markup=kb.back_kb("repo:list:0"))
        return ConversationHandler.END
    context.user_data["repo_cache"] = filtered
    await update.message.reply_text(f"🔍 Ditemukan {len(filtered)} repo cocok dengan '{query}':",
                                     reply_markup=kb.repo_list_kb(filtered, 0))
    return ConversationHandler.END


# ================= Info Repository =================

async def cb_repo_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    gh = get_gh(context, update.effective_user.id)
    full_name = context.user_data["current_repo"]
    await update.callback_query.answer("Mengambil info...")
    try:
        info = gh.repo_info(full_name)
    except GithubException as e:
        await edit_or_send(update, f"❌ Gagal: {e.data.get('message', e)}", kb.back_kb("repo:reopen"))
        return
    vis = "🔒 Private" if info["private"] else "🌐 Public"
    text = (
        f"📊 *Info: {info['full_name']}*\n\n"
        f"{vis}\n"
        f"📝 {info['description']}\n"
        f"⭐ Stars: {info['stars']}  |  🍴 Forks: {info['forks']}\n"
        f"💻 Bahasa: {info['language']}\n"
        f"📦 Ukuran: {fmt_size(info['size_kb']*1024)}\n"
        f"🌿 Default branch: {info['default_branch']}\n"
        f"🐛 Open issues: {info['open_issues']}\n"
        f"🕒 Update terakhir: {info['updated_at'].strftime('%d %b %Y %H:%M')}\n"
        f"🔗 {info['url']}"
    )
    await edit_or_send(update, text, kb.back_kb("repo:reopen"), ParseMode.MARKDOWN)


# ================= Star / Fork / Zip / Revert =================

async def cb_repo_togglestar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    gh = get_gh(context, update.effective_user.id)
    full_name = context.user_data["current_repo"]
    try:
        if gh.is_starred(full_name):
            gh.unstar(full_name)
            await update.callback_query.answer("⭐ Unstarred")
        else:
            gh.star(full_name)
            await update.callback_query.answer("⭐ Starred!")
    except GithubException as e:
        await update.callback_query.answer(f"Gagal: {e.data.get('message', e)}", show_alert=True)
    await open_repo_menu(update, context)


async def cb_repo_fork(update: Update, context: ContextTypes.DEFAULT_TYPE):
    gh = get_gh(context, update.effective_user.id)
    full_name = context.user_data["current_repo"]
    await update.callback_query.answer("Memfork repo...")
    try:
        forked = gh.fork(full_name)
        await edit_or_send(update, f"🍴 Berhasil fork ke *{forked.full_name}*\n{forked.html_url}",
                            kb.back_kb("repo:reopen"), ParseMode.MARKDOWN)
    except GithubException as e:
        await edit_or_send(update, f"❌ Gagal fork: {e.data.get('message', e)}", kb.back_kb("repo:reopen"))


async def cb_repo_zip(update: Update, context: ContextTypes.DEFAULT_TYPE):
    gh = get_gh(context, update.effective_user.id)
    full_name = context.user_data["current_repo"]
    branch = context.user_data.get("current_branch")
    url = gh.get_zip_url(full_name, branch)
    text = f"📦 Link download ZIP untuk *{full_name}*:\n{url}\n\n_Tinggal buka link ini di browser/aria2/wget._"
    await edit_or_send(update, text, kb.back_kb("repo:reopen"), ParseMode.MARKDOWN)


async def cb_repo_revert_ask(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "⚠️ *Undo Commit Terakhir*\n\n"
        "Ini akan memaksa branch mundur ke commit sebelumnya (force-reset). "
        "Commit terakhir tidak dihapus dari GitHub tapi branch tidak lagi menunjuk ke sana.\n\n"
        "Yakin ingin lanjut?"
    )
    await edit_or_send(update, text, kb.confirm_kb("repo:revert_do", "repo:reopen"), ParseMode.MARKDOWN)


async def cb_repo_revert_do(update: Update, context: ContextTypes.DEFAULT_TYPE):
    gh = get_gh(context, update.effective_user.id)
    full_name = context.user_data["current_repo"]
    branch = context.user_data.get("current_branch")
    await update.callback_query.answer("Memproses...")
    try:
        new_sha = gh.revert_last_commit(full_name, branch)
        await edit_or_send(update, f"↩️ Berhasil! Branch sekarang menunjuk ke commit `{new_sha[:7]}`.",
                            kb.back_kb("repo:reopen"), ParseMode.MARKDOWN)
    except Exception as e:
        await edit_or_send(update, f"❌ Gagal revert: {e}", kb.back_kb("repo:reopen"))


# ================= Hapus Repository =================

async def cb_repo_delete_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    full_name = context.user_data["current_repo"]
    text = f"🗑️ Yakin ingin *menghapus permanen* repository *{full_name}*?\n\nTindakan ini tidak bisa dibatalkan!"
    await edit_or_send(update, text, kb.confirm_kb("repo:delete_do", "repo:reopen"), ParseMode.MARKDOWN)


async def cb_repo_delete_do(update: Update, context: ContextTypes.DEFAULT_TYPE):
    gh = get_gh(context, update.effective_user.id)
    full_name = context.user_data["current_repo"]
    try:
        gh.delete_repo(full_name)
        context.user_data.pop("repo_cache", None)
        await edit_or_send(update, f"🗑️ Repository *{full_name}* berhasil dihapus.",
                            kb.main_menu_kb(), ParseMode.MARKDOWN)
    except GithubException as e:
        await edit_or_send(update, f"❌ Gagal hapus: {e.data.get('message', e)}", kb.back_kb("repo:reopen"))


# ================= Buat Repository Baru =================

async def cb_repo_new_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    gh = await require_login(update, context)
    if not gh:
        return ConversationHandler.END
    context.user_data["newrepo"] = {}
    await edit_or_send(update, "✏️ Ketik nama repository baru:")
    return ASK_REPO_NAME


async def receive_repo_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    name = update.message.text.strip().replace(" ", "-")
    context.user_data["newrepo"]["name"] = name
    await update.message.reply_text("📝 Ketik deskripsi singkat (atau kirim `-` untuk kosongkan):")
    return ASK_REPO_DESC


async def receive_repo_desc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    desc = update.message.text.strip()
    context.user_data["newrepo"]["description"] = "" if desc == "-" else desc
    await update.message.reply_text("🔒 Repo ini mau private atau public?", reply_markup=kb.yesno_private_kb())
    return ConversationHandler.END


async def cb_newrepo_private(update: Update, context: ContextTypes.DEFAULT_TYPE):
    private = update.callback_query.data.split(":")[-1] == "1"
    context.user_data["newrepo"]["private"] = private
    await edit_or_send(update, "📄 Sertakan file README otomatis?", kb.yesno_readme_kb())


async def cb_newrepo_readme(update: Update, context: ContextTypes.DEFAULT_TYPE):
    readme = update.callback_query.data.split(":")[-1] == "1"
    context.user_data["newrepo"]["auto_init"] = readme
    await edit_or_send(update, "🧩 Pilih template `.gitignore` (opsional):", kb.gitignore_template_kb())


async def cb_newrepo_gitignore(update: Update, context: ContextTypes.DEFAULT_TYPE):
    template = update.callback_query.data.split(":")[-1]
    gh = get_gh(context, update.effective_user.id)
    data = context.user_data["newrepo"]
    await update.callback_query.answer("Membuat repository...")
    try:
        repo = gh.create_repo(
            name=data["name"],
            private=data.get("private", False),
            description=data.get("description", ""),
            auto_init=data.get("auto_init", True),
            gitignore_template=None if template == "None" else template,
        )
        context.user_data.pop("repo_cache", None)
        text = f"✅ Repository *{repo.full_name}* berhasil dibuat!\n🔗 {repo.html_url}"
        await edit_or_send(update, text, kb.back_kb("repo:list:0"), ParseMode.MARKDOWN)
    except GithubException as e:
        await edit_or_send(update, f"❌ Gagal membuat repo: {e.data.get('message', e)}", kb.back_kb())


# ================= Browse Folder & File =================

def _current_path_display(path):
    return path if path else "/ (root)"


async def load_dir_and_show(update: Update, context: ContextTypes.DEFAULT_TYPE, page=0):
    gh = get_gh(context, update.effective_user.id)
    full_name = context.user_data["current_repo"]
    path = context.user_data.get("current_path", "")
    branch = context.user_data.get("current_branch")
    try:
        entries = gh.list_contents(full_name, path, branch)
    except GithubException as e:
        await edit_or_send(update, f"❌ Gagal buka folder: {e.data.get('message', e)}", kb.back_kb("repo:reopen"))
        return
    context.user_data["dir_entries"] = entries
    context.user_data["dir_page"] = page
    text = f"📁 *{full_name}*\n📍 Lokasi: `{_current_path_display(path)}`\n\n{len(entries)} item ditemukan."
    await edit_or_send(update, text, kb.dir_listing_kb(entries, page, path), ParseMode.MARKDOWN)


async def cb_dir_open_root(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["current_path"] = ""
    await load_dir_and_show(update, context, 0)


async def cb_dir_reopen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await load_dir_and_show(update, context, context.user_data.get("dir_page", 0))


async def cb_dir_page(update: Update, context: ContextTypes.DEFAULT_TYPE):
    page = int(update.callback_query.data.split(":")[-1])
    await load_dir_and_show(update, context, page)


async def cb_dir_open_idx(update: Update, context: ContextTypes.DEFAULT_TYPE):
    idx = int(update.callback_query.data.split(":")[-1])
    entries = context.user_data.get("dir_entries") or []
    if idx >= len(entries):
        await update.callback_query.answer("Data kedaluwarsa, buka ulang folder.", show_alert=True)
        return
    item = entries[idx]
    context.user_data["current_path"] = item.path
    await load_dir_and_show(update, context, 0)


async def cb_dir_up(update: Update, context: ContextTypes.DEFAULT_TYPE):
    path = context.user_data.get("current_path", "")
    parent = "/".join(path.split("/")[:-1])
    context.user_data["current_path"] = parent
    await load_dir_and_show(update, context, 0)


async def cb_file_open(update: Update, context: ContextTypes.DEFAULT_TYPE):
    idx = int(update.callback_query.data.split(":")[-1])
    entries = context.user_data.get("dir_entries") or []
    if idx >= len(entries):
        await update.callback_query.answer("Data kedaluwarsa, buka ulang folder.", show_alert=True)
        return
    item = entries[idx]
    context.user_data["current_file"] = item.path
    text = f"📄 *{item.name}*\n📍 `{item.path}`\n📦 Ukuran: {fmt_size(item.size)}\n\nPilih aksi:"
    await edit_or_send(update, text, kb.file_menu_kb(), ParseMode.MARKDOWN)


async def cb_file_view(update: Update, context: ContextTypes.DEFAULT_TYPE):
    gh = get_gh(context, update.effective_user.id)
    full_name = context.user_data["current_repo"]
    path = context.user_data["current_file"]
    branch = context.user_data.get("current_branch")
    await update.callback_query.answer("Mengambil isi file...")
    try:
        f = gh.get_file(full_name, path, branch)
        if f.size > config.MAX_FILE_VIEW_SIZE:
            await edit_or_send(update, f"⚠️ File terlalu besar untuk ditampilkan ({fmt_size(f.size)}).",
                                kb.back_kb("file:reopen" if False else "dir:reopen"))
            return
        raw = base64.b64decode(f.content).decode("utf-8", errors="replace")
    except GithubException as e:
        await edit_or_send(update, f"❌ Gagal: {e.data.get('message', e)}", kb.back_kb("dir:reopen"))
        return
    except Exception as e:
        await edit_or_send(update, f"❌ Gagal membaca file (mungkin biner): {e}", kb.back_kb("dir:reopen"))
        return
    snippet = raw if len(raw) <= 3500 else raw[:3500] + "\n\n... (dipotong, file terlalu panjang)"
    text = f"📄 *{path}*\n\n```\n{snippet}\n```"
    await edit_or_send(update, text, kb.back_kb("dir:reopen"), ParseMode.MARKDOWN)


async def cb_file_edit_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    path = context.user_data.get("current_file", "")
    await edit_or_send(update, f"✏️ Kirim *isi baru* untuk file `{path}` (kirim sebagai teks biasa).\n\n"
                                f"Ketik /cancel untuk batal.", parse_mode=ParseMode.MARKDOWN)
    context.user_data["pending_path"] = path
    return ASK_FILE_CONTENT


async def cb_file_new_here_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    path = context.user_data.get("current_path", "")
    await edit_or_send(update, f"📝 Ketik *nama file baru* di dalam `{_current_path_display(path)}`\n"
                                f"(contoh: `notes.txt` atau `src/app.py`):", parse_mode=ParseMode.MARKDOWN)
    return ASK_FILE_NAME


async def receive_file_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    name = update.message.text.strip()
    base_path = context.user_data.get("current_path", "")
    full_path = f"{base_path}/{name}" if base_path else name
    context.user_data["pending_path"] = full_path
    await update.message.reply_text(f"✏️ Sekarang kirim *isi* untuk file `{full_path}`:",
                                     parse_mode=ParseMode.MARKDOWN)
    return ASK_FILE_CONTENT


async def receive_file_content(update: Update, context: ContextTypes.DEFAULT_TYPE):
    content = update.message.text
    context.user_data["pending_content"] = content
    await update.message.reply_text("💬 Ketik pesan commit (atau kirim `-` untuk pesan default):")
    return ASK_COMMIT_MSG


async def receive_commit_msg(update: Update, context: ContextTypes.DEFAULT_TYPE):
    gh = get_gh(context, update.effective_user.id)
    full_name = context.user_data["current_repo"]
    path = context.user_data.pop("pending_path")
    content = context.user_data.pop("pending_content")
    branch = context.user_data.get("current_branch")
    msg = update.message.text.strip()
    if msg == "-":
        msg = f"Update {path} via {config.BOT_NAME}"
    status_msg = await update.message.reply_text("⏳ Menyimpan ke GitHub...")
    try:
        action, result = gh.save_file(full_name, path, content, msg, branch)
        label = "dibuat" if action == "created" else "diperbarui"
        text = f"✅ File `{path}` berhasil *{label}*!\n📝 Commit: {msg}"
        await status_msg.edit_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=kb.back_kb("dir:reopen"))
    except GithubException as e:
        await status_msg.edit_text(f"❌ Gagal menyimpan: {e.data.get('message', e)}",
                                    reply_markup=kb.back_kb("dir:reopen"))
    return ConversationHandler.END


async def cb_file_delete_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    path = context.user_data.get("current_file", "")
    text = f"🗑️ Yakin hapus file `{path}`?"
    await edit_or_send(update, text, kb.confirm_kb("file:delete_do", "dir:reopen"), ParseMode.MARKDOWN)


async def cb_file_delete_do(update: Update, context: ContextTypes.DEFAULT_TYPE):
    gh = get_gh(context, update.effective_user.id)
    full_name = context.user_data["current_repo"]
    path = context.user_data["current_file"]
    branch = context.user_data.get("current_branch")
    try:
        gh.delete_file(full_name, path, f"Delete {path} via {config.BOT_NAME}", branch)
        await edit_or_send(update, f"🗑️ File `{path}` berhasil dihapus.", kb.back_kb("dir:reopen"),
                            ParseMode.MARKDOWN)
    except GithubException as e:
        await edit_or_send(update, f"❌ Gagal hapus: {e.data.get('message', e)}", kb.back_kb("dir:reopen"))


async def cb_file_history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    gh = get_gh(context, update.effective_user.id)
    full_name = context.user_data["current_repo"]
    path = context.user_data["current_file"]
    branch = context.user_data.get("current_branch")
    await update.callback_query.answer("Mengambil riwayat...")
    try:
        commits = gh.get_commits(full_name, path=path, branch=branch, limit=10)
    except GithubException as e:
        await edit_or_send(update, f"❌ Gagal: {e.data.get('message', e)}", kb.back_kb("dir:reopen"))
        return
    if not commits:
        await edit_or_send(update, "📭 Belum ada riwayat commit untuk file ini.", kb.back_kb("dir:reopen"))
        return
    lines = [f"📜 *Riwayat: {path}*\n"]
    for c in commits:
        d = c.commit.author.date.strftime("%d %b %Y %H:%M")
        msg = c.commit.message.split("\n")[0][:60]
        lines.append(f"• `{c.sha[:7]}` — {msg}\n   👤 {c.commit.author.name} • {d}")
    await edit_or_send(update, "\n".join(lines), kb.back_kb("dir:reopen"), ParseMode.MARKDOWN)


# ================= Branch Manager =================

async def cb_branch_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    gh = get_gh(context, update.effective_user.id)
    full_name = context.user_data["current_repo"]
    await update.callback_query.answer("Memuat branch...")
    try:
        branches = gh.list_branches(full_name)
        default_branch = gh.get_repo(full_name).default_branch
    except GithubException as e:
        await edit_or_send(update, f"❌ Gagal: {e.data.get('message', e)}", kb.back_kb("repo:reopen"))
        return
    context.user_data["branch_cache"] = branches
    text = f"🌿 *Branch di {full_name}*\nBranch aktif saat ini: `{context.user_data.get('current_branch') or default_branch}`"
    await edit_or_send(update, text, kb.branch_list_kb(branches, default_branch), ParseMode.MARKDOWN)


async def cb_branch_switch(update: Update, context: ContextTypes.DEFAULT_TYPE):
    idx = int(update.callback_query.data.split(":")[-1])
    branches = context.user_data.get("branch_cache") or []
    if idx >= len(branches):
        await update.callback_query.answer("Data kedaluwarsa.", show_alert=True)
        return
    branch = branches[idx]
    context.user_data["current_branch"] = branch.name
    context.user_data["current_path"] = ""
    await update.callback_query.answer(f"Beralih ke branch {branch.name}")
    await open_repo_menu(update, context)


async def cb_branch_new_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await edit_or_send(update, "🌱 Ketik nama branch baru (akan dibuat dari branch saat ini):")
    return ASK_BRANCH_NAME


async def receive_branch_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    gh = get_gh(context, update.effective_user.id)
    full_name = context.user_data["current_repo"]
    source = context.user_data.get("current_branch")
    name = update.message.text.strip().replace(" ", "-")
    try:
        gh.create_branch(full_name, name, source)
        await update.message.reply_text(f"✅ Branch `{name}` berhasil dibuat!", parse_mode=ParseMode.MARKDOWN,
                                         reply_markup=kb.back_kb("branch:list"))
    except GithubException as e:
        await update.message.reply_text(f"❌ Gagal buat branch: {e.data.get('message', e)}",
                                         reply_markup=kb.back_kb("branch:list"))
    return ConversationHandler.END


# ================= Riwayat Commit Repo =================

async def cb_commit_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    gh = get_gh(context, update.effective_user.id)
    full_name = context.user_data["current_repo"]
    branch = context.user_data.get("current_branch")
    await update.callback_query.answer("Mengambil riwayat commit...")
    try:
        commits = gh.get_commits(full_name, branch=branch, limit=10)
    except GithubException as e:
        await edit_or_send(update, f"❌ Gagal: {e.data.get('message', e)}", kb.back_kb("repo:reopen"))
        return
    lines = [f"📜 *10 Commit Terakhir — {full_name}*\n"]
    for c in commits:
        d = c.commit.author.date.strftime("%d %b %Y %H:%M")
        msg = c.commit.message.split("\n")[0][:60]
        lines.append(f"• `{c.sha[:7]}` — {msg}\n   👤 {c.commit.author.name} • {d}")
    await edit_or_send(update, "\n".join(lines), kb.back_kb("repo:reopen"), ParseMode.MARKDOWN)


# ================= Pencarian Kode dalam Repo =================

async def cb_codesearch_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await edit_or_send(update, "🔍 Ketik kata kunci yang ingin dicari di dalam repo ini:")
    return ASK_CODE_SEARCH


async def receive_codesearch(update: Update, context: ContextTypes.DEFAULT_TYPE):
    gh = get_gh(context, update.effective_user.id)
    full_name = context.user_data["current_repo"]
    query = update.message.text.strip()
    status = await update.message.reply_text("🔍 Mencari...")
    try:
        results = gh.search_code_in_repo(full_name, query)
    except GithubException as e:
        await status.edit_text(f"❌ Gagal mencari: {e.data.get('message', e)}",
                                reply_markup=kb.back_kb("repo:reopen"))
        return ConversationHandler.END
    if not results:
        await status.edit_text("😕 Tidak ada hasil ditemukan.", reply_markup=kb.back_kb("repo:reopen"))
        return ConversationHandler.END
    lines = [f"🔍 *Hasil pencarian '{query}'* ({len(results)} ditemukan)\n"]
    for r in results:
        lines.append(f"📄 `{r.path}`")
    await status.edit_text("\n".join(lines), parse_mode=ParseMode.MARKDOWN, reply_markup=kb.back_kb("repo:reopen"))
    return ConversationHandler.END


# ================= Watch Repo (notifikasi commit baru) =================

async def cb_watch_add(update: Update, context: ContextTypes.DEFAULT_TYPE):
    gh = get_gh(context, update.effective_user.id)
    full_name = context.user_data["current_repo"]
    branch = context.user_data.get("current_branch")
    user_id = update.effective_user.id
    try:
        sha = gh.get_latest_commit_sha(full_name, branch)
        storage.set_watch(user_id, full_name, sha)
        await update.callback_query.answer("👁️ Repo ini sekarang dipantau!", show_alert=True)
    except GithubException as e:
        await update.callback_query.answer(f"Gagal: {e.data.get('message', e)}", show_alert=True)
    await open_repo_menu(update, context)


async def cb_watch_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    watch = storage.get_watchlist(user_id)
    if not watch:
        await edit_or_send(update, "📭 Belum ada repo yang dipantau.\n\n"
                                    "Buka repo lalu tekan '👁️ Watch Repo Ini' untuk mulai memantau.",
                            kb.back_kb())
        return
    text = f"👀 *Repo yang Dipantau* ({len(watch)})\n\nBot akan mengirim notifikasi otomatis saat ada commit baru."
    await edit_or_send(update, text, kb.watchlist_kb(watch.keys()), ParseMode.MARKDOWN)


async def cb_watch_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    repo_name = update.callback_query.data.split(":", 2)[-1]
    text = f"👁️ *{repo_name}*\n\nSedang dipantau. Notifikasi otomatis dikirim tiap ada commit baru."
    await edit_or_send(update, text, kb.watch_info_kb(repo_name), ParseMode.MARKDOWN)


async def cb_watch_remove(update: Update, context: ContextTypes.DEFAULT_TYPE):
    repo_name = update.callback_query.data.split(":", 2)[-1]
    storage.unwatch(update.effective_user.id, repo_name)
    await update.callback_query.answer("🛑 Berhenti memantau.")
    await cb_watch_list(update, context)


async def job_check_watchlist(context: ContextTypes.DEFAULT_TYPE):
    """Job berkala: cek commit terbaru tiap repo yang dipantau, kirim notif kalau berubah."""
    watchers = storage.all_watchers()
    for uid_str, repos in watchers.items():
        uid = int(uid_str)
        token = storage.get_token(uid)
        if not token:
            continue
        gh = GH(token)
        for full_name, last_sha in list(repos.items()):
            try:
                new_sha = gh.get_latest_commit_sha(full_name)
            except Exception:
                continue
            if new_sha and new_sha != last_sha:
                storage.set_watch(uid, full_name, new_sha)
                try:
                    commits = gh.get_commits(full_name, limit=1)
                    msg = commits[0].commit.message.split("\n")[0] if commits else "(tidak diketahui)"
                    author = commits[0].commit.author.name if commits else "?"
                except Exception:
                    msg, author = "(tidak diketahui)", "?"
                text = (
                    f"🔔 *Commit baru di {full_name}!*\n\n"
                    f"👤 {author}\n"
                    f"📝 {msg}\n"
                    f"🔗 `{new_sha[:7]}`"
                )
                try:
                    await context.bot.send_message(chat_id=uid, text=text, parse_mode=ParseMode.MARKDOWN)
                except Exception as e:
                    logger.warning(f"Gagal kirim notif ke {uid}: {e}")


# ================= Quick Upload lewat Forward Dokumen =================

async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Fitur eksklusif: kirim/forward dokumen teks dengan caption berisi path,
    bot langsung commit ke repo yang sedang aktif. Contoh caption: notes/todo.md
    """
    user_id = update.effective_user.id
    gh = get_gh(context, user_id)
    if not gh:
        await update.message.reply_text("🔐 Hubungkan akun GitHub dulu lewat menu 🔑 Akun GitHub.")
        return
    full_name = context.user_data.get("current_repo")
    if not full_name:
        await update.message.reply_text("📁 Buka salah satu repository dulu (menu List Repository), "
                                         "baru kirim/forward dokumen untuk quick-upload.")
        return
    doc = update.message.document
    caption = (update.message.caption or "").strip()
    path = caption if caption else doc.file_name
    branch = context.user_data.get("current_branch")
    status = await update.message.reply_text(f"⏳ Mengunggah `{path}` ke {full_name}...",
                                              parse_mode=ParseMode.MARKDOWN)
    try:
        tg_file = await doc.get_file()
        raw_bytes = bytes(await tg_file.download_as_bytearray())
        if len(raw_bytes) > config.MAX_FILE_EDIT_SIZE:
            await status.edit_text("⚠️ File terlalu besar (>900KB) untuk API Contents GitHub.")
            return
        try:
            text_content = raw_bytes.decode("utf-8")
            action, _ = gh.save_file(full_name, path, text_content,
                                      f"Quick upload {path} via {config.BOT_NAME}", branch)
        except UnicodeDecodeError:
            # File biner: pakai base64 lewat git data API sederhana (create/update via content b64)
            import base64 as b64mod
            content_b64 = b64mod.b64encode(raw_bytes).decode()
            repo = gh.get_repo(full_name)
            kwargs = {"branch": branch} if branch else {}
            try:
                existing = repo.get_contents(path, ref=branch) if branch else repo.get_contents(path)
                repo.update_file(path, f"Quick upload {path}", content_b64, existing.sha, **kwargs)
                action = "updated"
            except GithubException as e:
                if e.status == 404:
                    repo.create_file(path, f"Quick upload {path}", content_b64, **kwargs)
                    action = "created"
                else:
                    raise
        label = "diperbarui" if action == "updated" else "dibuat"
        await status.edit_text(f"✅ File `{path}` berhasil {label} di *{full_name}*!",
                                parse_mode=ParseMode.MARKDOWN)
    except GithubException as e:
        await status.edit_text(f"❌ Gagal upload: {e.data.get('message', e)}")
    except Exception as e:
        await status.edit_text(f"❌ Terjadi kesalahan: {e}")


# ================= Cancel & Fallback =================

async def cmd_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ Dibatalkan.", reply_markup=kb.main_menu_kb())
    return ConversationHandler.END


async def cb_noop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    logger.error("Exception saat handle update:", exc_info=context.error)
    try:
        if isinstance(update, Update) and update.effective_chat:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=f"⚠️ Terjadi kesalahan tak terduga: {context.error}",
            )
    except Exception:
        pass


# ================= Main =================

def build_app():
    if not config.BOT_TOKEN:
        raise SystemExit("❌ BOT_TOKEN belum diset. Isi file .env terlebih dahulu (lihat .env.example).")

    app = Application.builder().token(config.BOT_TOKEN).build()

    conv = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(cb_account_login, pattern="^account:login$"),
            CallbackQueryHandler(cb_repo_new_start, pattern="^repo:new$"),
            CallbackQueryHandler(cb_file_edit_start, pattern="^file:edit$"),
            CallbackQueryHandler(cb_file_new_here_start, pattern="^file:new_here$"),
            CallbackQueryHandler(cb_branch_new_start, pattern="^branch:new$"),
            CallbackQueryHandler(cb_codesearch_start, pattern="^repo:codesearch$"),
            CallbackQueryHandler(cb_repo_search_start, pattern="^repo:search_repo$"),
        ],
        states={
            ASK_TOKEN: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_token)],
            ASK_REPO_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_repo_name)],
            ASK_REPO_DESC: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_repo_desc)],
            ASK_FILE_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_file_name)],
            ASK_FILE_CONTENT: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_file_content)],
            ASK_COMMIT_MSG: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_commit_msg)],
            ASK_CODE_SEARCH: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_codesearch)],
            ASK_BRANCH_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_branch_name)],
            ASK_REPO_SEARCH: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_repo_search)],
        },
        fallbacks=[CommandHandler("cancel", cmd_cancel)],
        allow_reentry=True,
    )
    app.add_handler(conv)

    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("menu", cmd_start))
    app.add_handler(CommandHandler("cancel", cmd_cancel))

    app.add_handler(CallbackQueryHandler(cb_main_menu, pattern="^menu:main$"))
    app.add_handler(CallbackQueryHandler(cb_about, pattern="^about$"))

    app.add_handler(CallbackQueryHandler(cb_account_menu, pattern="^account:menu$"))
    app.add_handler(CallbackQueryHandler(cb_account_logout, pattern="^account:logout$"))

    app.add_handler(CallbackQueryHandler(cb_repo_list, pattern=r"^repo:list:\d+$"))
    app.add_handler(CallbackQueryHandler(cb_repo_open, pattern=r"^repo:open:\d+$"))
    app.add_handler(CallbackQueryHandler(cb_repo_reopen, pattern="^repo:reopen$"))
    app.add_handler(CallbackQueryHandler(cb_repo_info, pattern="^repo:info$"))
    app.add_handler(CallbackQueryHandler(cb_repo_togglestar, pattern="^repo:togglestar$"))
    app.add_handler(CallbackQueryHandler(cb_repo_fork, pattern="^repo:fork$"))
    app.add_handler(CallbackQueryHandler(cb_repo_zip, pattern="^repo:zip$"))
    app.add_handler(CallbackQueryHandler(cb_repo_revert_ask, pattern="^repo:revert$"))
    app.add_handler(CallbackQueryHandler(cb_repo_revert_do, pattern="^repo:revert_do$"))
    app.add_handler(CallbackQueryHandler(cb_repo_delete_confirm, pattern="^repo:delete_confirm$"))
    app.add_handler(CallbackQueryHandler(cb_repo_delete_do, pattern="^repo:delete_do$"))

    app.add_handler(CallbackQueryHandler(cb_newrepo_private, pattern=r"^newrepo:private:[01]$"))
    app.add_handler(CallbackQueryHandler(cb_newrepo_readme, pattern=r"^newrepo:readme:[01]$"))
    app.add_handler(CallbackQueryHandler(cb_newrepo_gitignore, pattern=r"^newrepo:gitignore:.+$"))

    app.add_handler(CallbackQueryHandler(cb_dir_open_root, pattern="^dir:open:root$"))
    app.add_handler(CallbackQueryHandler(cb_dir_reopen, pattern="^dir:reopen$"))
    app.add_handler(CallbackQueryHandler(cb_dir_page, pattern=r"^dir:page:\d+$"))
    app.add_handler(CallbackQueryHandler(cb_dir_open_idx, pattern=r"^dir:open:\d+$"))
    app.add_handler(CallbackQueryHandler(cb_dir_up, pattern="^dir:up$"))

    app.add_handler(CallbackQueryHandler(cb_file_open, pattern=r"^file:open:\d+$"))
    app.add_handler(CallbackQueryHandler(cb_file_view, pattern="^file:view$"))
    app.add_handler(CallbackQueryHandler(cb_file_delete_confirm, pattern="^file:delete_confirm$"))
    app.add_handler(CallbackQueryHandler(cb_file_delete_do, pattern="^file:delete_do$"))
    app.add_handler(CallbackQueryHandler(cb_file_history, pattern="^file:history$"))

    app.add_handler(CallbackQueryHandler(cb_branch_list, pattern="^branch:list$"))
    app.add_handler(CallbackQueryHandler(cb_branch_switch, pattern=r"^branch:switch:\d+$"))

    app.add_handler(CallbackQueryHandler(cb_commit_list, pattern="^commit:list$"))

    app.add_handler(CallbackQueryHandler(cb_watch_add, pattern="^watch:add$"))
    app.add_handler(CallbackQueryHandler(cb_watch_list, pattern="^watch:list$"))
    app.add_handler(CallbackQueryHandler(cb_watch_info, pattern=r"^watch:info:.+$"))
    app.add_handler(CallbackQueryHandler(cb_watch_remove, pattern=r"^watch:remove:.+$"))

    app.add_handler(MessageHandler(filters.Document.ALL, handle_document))

    app.add_error_handler(error_handler)

    if app.job_queue:
        app.job_queue.run_repeating(job_check_watchlist, interval=config.WATCH_INTERVAL_SECONDS, first=30)
    else:
        logger.warning("JobQueue tidak tersedia — fitur Watch Repo (notifikasi otomatis) nonaktif. "
                        "Install dengan: pip install \"python-telegram-bot[job-queue]\"")

    return app


def main():
    app = build_app()
    logger.info(f"{config.BOT_NAME} berjalan... (powered by {config.BOT_AUTHOR})")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
