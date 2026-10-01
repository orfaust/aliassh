"""Standalone bootstrap for: curl -fsSL <raw bootstrap.py URL> | py."""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

RAW_BASE = "https://raw.githubusercontent.com/orfaust/aliassh/"
API_URL = "https://api.github.com/repos/orfaust/aliassh/commits/main"
FILES = ("install.py", "alias_connect.py")
MAX_FILE_BYTES = 1024 * 1024


def bootstrap() -> int:
    if sys.version_info < (3, 10):
        print("Python 3.10 or newer is required.", file=sys.stderr)
        return 1
    try:
        commit = os.environ.get("ALIASSH_REF")
        if not commit:
            request = urllib.request.Request(API_URL, headers={"Accept": "application/vnd.github+json", "Cache-Control": "no-cache"})
            with urllib.request.urlopen(request, timeout=20) as response:
                commit = json.load(response)["sha"]
        if not re.fullmatch(r"[0-9a-f]{40}", commit):
            raise ValueError("Invalid commit from GitHub")
        with tempfile.TemporaryDirectory(prefix="aliassh-") as directory:
            root = Path(directory)
            for name in FILES:
                request = urllib.request.Request(
                    f"{RAW_BASE}{commit}/{name}?refresh={time.time_ns()}",
                    headers={"Cache-Control": "no-cache"},
                )
                with urllib.request.urlopen(request, timeout=20) as response:
                    content = response.read(MAX_FILE_BYTES + 1)
                if len(content) > MAX_FILE_BYTES:
                    raise ValueError(f"Download too large: {name}")
                (root / name).write_bytes(content)
            environment = os.environ.copy()
            environment["ALIASSH_REF"] = commit
            return subprocess.call([sys.executable, str(root / "install.py")], env=environment)
    except (OSError, ValueError, KeyError) as exc:
        print(f"Installation failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(bootstrap())
