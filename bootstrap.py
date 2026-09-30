"""Standalone bootstrap for: curl -fsSL <raw bootstrap.py URL> | py."""

from __future__ import annotations

import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

RAW_BASE = "https://raw.githubusercontent.com/orfaust/aliassh/main/"
FILES = ("install.py", "alias_connect.py")
MAX_FILE_BYTES = 1024 * 1024


def bootstrap() -> int:
    if sys.version_info < (3, 10):
        print("Python 3.10 or newer is required.", file=sys.stderr)
        return 1
    try:
        with tempfile.TemporaryDirectory(prefix="aliassh-") as directory:
            root = Path(directory)
            for name in FILES:
                request = urllib.request.Request(
                    f"{RAW_BASE}{name}?refresh={time.time_ns()}",
                    headers={"Cache-Control": "no-cache"},
                )
                with urllib.request.urlopen(request, timeout=20) as response:
                    content = response.read(MAX_FILE_BYTES + 1)
                if len(content) > MAX_FILE_BYTES:
                    raise ValueError(f"Download too large: {name}")
                (root / name).write_bytes(content)
            return subprocess.call([sys.executable, str(root / "install.py")])
    except (OSError, ValueError) as exc:
        print(f"Installation failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(bootstrap())
