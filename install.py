"""Install aliassh for the current user without third-party dependencies."""

from __future__ import annotations

import os
import re
import shutil
import stat
import sys
import tempfile
from pathlib import Path


SOURCE = Path(__file__).resolve().parent / "alias_connect.py"


def install(home: Path | None = None, platform: str | None = None) -> Path:
    home = home or Path.home()
    platform = platform or os.name
    if not SOURCE.is_file():
        raise FileNotFoundError(f"Missing {SOURCE}")
    if sys.version_info < (3, 10):
        raise RuntimeError("Python 3.10 or newer is required")
    commit = os.environ.get("ALIASSH_REF", "")
    if commit and not re.fullmatch(r"[0-9a-f]{40}", commit):
        raise ValueError("Invalid installation commit")

    if platform == "nt":
        directory = home / "AppData" / "Local" / "Programs" / "aliassh"
        launcher = directory / "aliassh.cmd"
        command = f'@echo off\r\n"{sys.executable}" "%~dp0alias_connect.py" %*\r\n'
    else:
        directory = home / ".local" / "bin"
        launcher = directory / "aliassh"
        command = f'#!{sys.executable}\nfrom alias_connect import main\nraise SystemExit(main())\n'

    directory.mkdir(parents=True, exist_ok=True)
    destination = directory / "alias_connect.py"
    if SOURCE != destination:
        # Replace complete files, never leave a truncated app after an interrupted update.
        with tempfile.NamedTemporaryFile(dir=directory, delete=False) as output:
            temporary = Path(output.name)
        try:
            shutil.copyfile(SOURCE, temporary)
            os.replace(temporary, destination)
        finally:
            temporary.unlink(missing_ok=True)
    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", newline="", dir=directory, delete=False) as output:
        temporary = Path(output.name)
        output.write(command)
    try:
        if platform != "nt":
            temporary.chmod(temporary.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
        os.replace(temporary, launcher)
    finally:
        temporary.unlink(missing_ok=True)
    version_file = directory / ".aliassh-version"
    if commit:
        version_file.write_text(commit + "\n", encoding="ascii")
    else:
        version_file.unlink(missing_ok=True)  # Local installs have no known upstream version.
    return launcher


def ensure_user_path(directory: Path, home: Path, platform: str) -> bool:
    """Make the launcher directory available to newly opened terminals."""
    if platform == "nt":
        import winreg

        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, r"Environment") as key:
            try:
                current, kind = winreg.QueryValueEx(key, "Path")
            except FileNotFoundError:
                current, kind = "", winreg.REG_EXPAND_SZ
            if str(directory).casefold() in {p.strip('"').casefold() for p in current.split(";")}:
                return False
            winreg.SetValueEx(key, "Path", 0, kind, current.rstrip(";") + (";" if current else "") + str(directory))
    else:
        profile = home / ".profile"
        line = f'export PATH="{directory}:$PATH" # aliassh\n'
        if profile.exists() and line in profile.read_text(encoding="utf-8"):
            return False
        with profile.open("a", encoding="utf-8") as output:
            if profile.stat().st_size:
                output.write("\n")
            output.write(line)
    return True


def main() -> int:
    try:
        launcher = install()
        path_changed = ensure_user_path(launcher.parent, Path.home(), os.name)
    except (OSError, RuntimeError, ValueError) as exc:
        print(f"Installation failed: {exc}", file=sys.stderr)
        return 1
    print(f"Installed: {launcher}")
    if path_changed or str(launcher.parent).casefold() not in {p.casefold() for p in os.environ.get("PATH", "").split(os.pathsep)}:
        print("Open a new terminal to use the updated PATH.")
    print("Run: aliassh")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
