"""
Wrapper di atas PyGithub — semua operasi ke GitHub lewat sini.
Satu instance GH per user (dibuat dari token pribadi mereka).
"""
from github import Github, GithubException


class GH:
    def __init__(self, token: str):
        self.gh = Github(token, per_page=50, timeout=20)
        self._user = None

    @property
    def user(self):
        if self._user is None:
            self._user = self.gh.get_user()
        return self._user

    def verify(self):
        """Lempar exception kalau token tidak valid; return login username jika valid."""
        return self.user.login

    # ---------- Repository ----------

    def list_repos(self, sort="updated"):
        return list(self.user.get_repos(sort=sort))

    def get_repo(self, full_name: str):
        return self.gh.get_repo(full_name)

    def create_repo(self, name, private=False, description="", auto_init=True,
                     gitignore_template=None, license_template=None):
        kwargs = dict(name=name, private=private, description=description,
                       auto_init=auto_init)
        if gitignore_template:
            kwargs["gitignore_template"] = gitignore_template
        if license_template:
            kwargs["license_template"] = license_template
        return self.user.create_repo(**kwargs)

    def delete_repo(self, full_name: str):
        self.get_repo(full_name).delete()

    def repo_info(self, full_name: str):
        r = self.get_repo(full_name)
        return {
            "full_name": r.full_name,
            "description": r.description or "-",
            "private": r.private,
            "stars": r.stargazers_count,
            "forks": r.forks_count,
            "language": r.language or "-",
            "size_kb": r.size,
            "default_branch": r.default_branch,
            "updated_at": r.updated_at,
            "url": r.html_url,
            "open_issues": r.open_issues_count,
        }

    # ---------- Files & folders ----------

    def list_contents(self, full_name: str, path: str = "", ref: str = None):
        repo = self.get_repo(full_name)
        kwargs = {"ref": ref} if ref else {}
        contents = repo.get_contents(path or "", **kwargs)
        if not isinstance(contents, list):
            contents = [contents]
        contents.sort(key=lambda c: (c.type != "dir", c.name.lower()))
        return contents

    def get_file(self, full_name: str, path: str, ref: str = None):
        repo = self.get_repo(full_name)
        kwargs = {"ref": ref} if ref else {}
        return repo.get_contents(path, **kwargs)

    def save_file(self, full_name: str, path: str, content: str, message: str,
                  branch: str = None):
        """Buat file baru atau update file yang sudah ada. Return (aksi, hasil)."""
        repo = self.get_repo(full_name)
        get_kwargs = {"ref": branch} if branch else {}
        commit_kwargs = {"branch": branch} if branch else {}
        try:
            existing = repo.get_contents(path, **get_kwargs)
            result = repo.update_file(path, message, content, existing.sha, **commit_kwargs)
            return "updated", result
        except GithubException as e:
            if e.status == 404:
                result = repo.create_file(path, message, content, **commit_kwargs)
                return "created", result
            raise

    def delete_file(self, full_name: str, path: str, message: str, branch: str = None):
        repo = self.get_repo(full_name)
        get_kwargs = {"ref": branch} if branch else {}
        commit_kwargs = {"branch": branch} if branch else {}
        existing = repo.get_contents(path, **get_kwargs)
        return repo.delete_file(path, message, existing.sha, **commit_kwargs)

    # ---------- Branches ----------

    def list_branches(self, full_name: str):
        return list(self.get_repo(full_name).get_branches())

    def create_branch(self, full_name: str, new_branch: str, source_branch: str = None):
        repo = self.get_repo(full_name)
        source_branch = source_branch or repo.default_branch
        source = repo.get_branch(source_branch)
        repo.create_git_ref(ref=f"refs/heads/{new_branch}", sha=source.commit.sha)

    def delete_branch(self, full_name: str, branch: str):
        repo = self.get_repo(full_name)
        ref = repo.get_git_ref(f"heads/{branch}")
        ref.delete()

    # ---------- Commits & riwayat (fitur eksklusif) ----------

    def get_commits(self, full_name: str, path: str = None, branch: str = None, limit: int = 10):
        repo = self.get_repo(full_name)
        kwargs = {}
        if path:
            kwargs["path"] = path
        if branch:
            kwargs["sha"] = branch
        commits = repo.get_commits(**kwargs)
        out = []
        for i, c in enumerate(commits):
            if i >= limit:
                break
            out.append(c)
        return out

    def revert_last_commit(self, full_name: str, branch: str = None):
        """Undo destruktif: paksa HEAD branch mundur ke commit sebelumnya (force-reset)."""
        repo = self.get_repo(full_name)
        branch = branch or repo.default_branch
        ref = repo.get_git_ref(f"heads/{branch}")
        latest = repo.get_commit(ref.object.sha)
        parents = latest.commit.parents
        if not parents:
            raise ValueError("Tidak ada commit sebelumnya untuk di-revert.")
        parent_sha = parents[0].sha
        ref.edit(sha=parent_sha, force=True)
        return parent_sha

    def get_latest_commit_sha(self, full_name: str, branch: str = None):
        repo = self.get_repo(full_name)
        branch = branch or repo.default_branch
        return repo.get_branch(branch).commit.sha

    # ---------- Star & Fork ----------

    def star(self, full_name: str):
        self.user.add_to_starred(self.get_repo(full_name))

    def unstar(self, full_name: str):
        self.user.remove_from_starred(self.get_repo(full_name))

    def is_starred(self, full_name: str) -> bool:
        return self.user.has_in_starred(self.get_repo(full_name))

    def fork(self, full_name: str):
        return self.user.create_fork(self.get_repo(full_name))

    # ---------- Pencarian kode dalam repo (fitur eksklusif) ----------

    def search_code_in_repo(self, full_name: str, query: str, limit: int = 15):
        q = f"{query} repo:{full_name}"
        results = self.gh.search_code(q)
        out = []
        for i, item in enumerate(results):
            if i >= limit:
                break
            out.append(item)
        return out

    # ---------- Lain-lain ----------

    def get_zip_url(self, full_name: str, ref: str = None):
        repo = self.get_repo(full_name)
        ref = ref or repo.default_branch
        return f"https://github.com/{full_name}/archive/refs/heads/{ref}.zip"

    def rate_limit(self):
        return self.gh.get_rate_limit()
