import hashlib
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import time


def source_identity(repository):
    repository = Path(repository).resolve()
    deadline = time.monotonic() + 10

    def remaining_seconds():
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise ValueError("Source identity exceeded its time limit.")
        return remaining

    def git(*arguments):
        return subprocess.run(["git", "-C", str(repository), *arguments],
                              check=True, capture_output=True, timeout=remaining_seconds()).stdout

    try:
        if Path(os.fsdecode(git("rev-parse", "--show-toplevel")).strip()) != repository:
            raise ValueError("Expected the repository root.")
        head = git("rev-parse", "HEAD").decode().strip()
        names = sorted(set(git("ls-files", "--cached", "--others", "--exclude-standard", "-z").split(b"\0")) - {b""})
        digest = hashlib.sha256()
        for name in names:
            remaining_seconds()
            path = repository / os.fsdecode(name)
            digest.update(len(name).to_bytes(8, "big") + name)
            try:
                before = path.lstat()
            except FileNotFoundError:
                digest.update(b"deleted\0")
                continue
            if stat.S_ISLNK(before.st_mode):
                content = os.fsencode(os.readlink(path))
                digest.update(b"symlink\0" + len(content).to_bytes(8, "big") + content)
                continue
            if not stat.S_ISREG(before.st_mode) or not path.resolve().is_relative_to(repository):
                raise ValueError("Source includes a submodule, special file, or external directory link.")
            digest.update(b"executable\0" if before.st_mode & 0o111 else b"file\0")
            file_digest = hashlib.sha256()
            with path.open("rb") as stream:
                for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                    remaining_seconds()
                    file_digest.update(chunk)
            digest.update(file_digest.digest())
            after = path.lstat()
            if (before.st_ino, before.st_size, before.st_mtime_ns, before.st_ctime_ns) != (
                    after.st_ino, after.st_size, after.st_mtime_ns, after.st_ctime_ns):
                raise ValueError("Source changed while its identity was being recorded.")
        final_names = sorted(set(git("ls-files", "--cached", "--others", "--exclude-standard", "-z").split(b"\0")) - {b""})
        if names != final_names or head != git("rev-parse", "HEAD").decode().strip():
            raise ValueError("Source changed while its identity was being recorded.")
        return {"revision": head, "content_sha256": digest.hexdigest(),
                "coverage": "Tracked and nonignored untracked files; symlink targets are recorded without following them."}
    except (OSError, ValueError, subprocess.SubprocessError):
        return {"revision": None, "content_sha256": None,
                "error": "Source identity unavailable. Check repository access, concurrent edits, submodules, special files, and the 10-second time limit."}


if __name__ == "__main__":
    print(json.dumps(source_identity(Path(sys.argv[1]) / "repo"), indent=2))
