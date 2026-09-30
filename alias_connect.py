"""Select an SSH Host alias and connect to it."""

from __future__ import annotations

import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

HOST_DIRECTIVE = re.compile(r"^\s*Host\s+(.*?)\s*$", re.IGNORECASE)
NEW_ALIAS = "new alias"


def read_aliases(config: Path, visited: set[Path] | None = None) -> list[str]:
    """Read literal Host aliases, including those in locally included config files."""
    if visited is None:
        visited = set()
    config = config.expanduser().resolve()
    if config in visited:
        return []
    visited.add(config)

    aliases: list[str] = []
    if not config.exists() and config == (Path.home() / ".ssh" / "config").resolve():
        return []
    try:
        lines = config.read_text(encoding="utf-8-sig").splitlines()
    except (OSError, UnicodeError) as exc:
        if config == (Path.home() / ".ssh" / "config").resolve():
            raise OSError(f"Cannot read {config}: {exc}") from exc
        return []

    for line in lines:
        line = line.split("#", 1)[0].strip()
        match = HOST_DIRECTIVE.match(line)
        if match:
            for alias in match.group(1).split():
                if not any(char in alias for char in "*?!") and alias not in aliases:
                    aliases.append(alias)
            continue
        parts = line.split(None, 1)
        if len(parts) == 2 and parts[0].lower() == "include":
            for pattern in parts[1].split():
                base = Path(pattern).expanduser()
                if not base.is_absolute():
                    base = config.parent / base
                for included in sorted(base.parent.glob(base.name)):
                    if included.is_file():
                        for alias in read_aliases(included, visited):
                            if alias not in aliases:
                                aliases.append(alias)
    return aliases


def choose_alias(aliases: list[str]) -> str | tuple[str, str] | None:
    """Display an interactive menu. Returns None when the user cancels."""
    if os.name == "nt":
        import msvcrt

        def key() -> str:
            char = msvcrt.getwch()
            if char in ("\x00", "\xe0"):
                return {"H": "up", "P": "down"}.get(msvcrt.getwch(), "other")
            return {"\r": "enter", "\x1b": "escape", "\x03": "interrupt", "r": "rename", "d": "delete", "e": "edit"}.get(char, "other")
    else:
        import termios
        import tty

        def key() -> str:
            fd = sys.stdin.fileno()
            previous = termios.tcgetattr(fd)
            try:
                tty.setraw(fd)
                char = sys.stdin.read(1)
                if char == "\x1b":
                    import select

                    if select.select([sys.stdin], [], [], 0.05)[0]:
                        sequence = sys.stdin.read(1)
                        if sequence == "[" and select.select([sys.stdin], [], [], 0.05)[0]:
                            return {"A": "up", "B": "down"}.get(sys.stdin.read(1), "other")
                    return "escape"
                return {"\r": "enter", "\n": "enter", "\x03": "interrupt", "r": "rename", "d": "delete", "e": "edit"}.get(char, "other")
            finally:
                termios.tcsetattr(fd, termios.TCSADRAIN, previous)

    selected = 0
    try:
        sys.stdout.write("SSH aliases (↑/↓ select, Enter connect, e edit, r rename, d delete, Esc quit):\n")
        for index, alias in enumerate(aliases):
            sys.stdout.write(f"{'❯' if index == selected else ' '} {alias}\n")
        sys.stdout.flush()
        while True:
            pressed = key()
            if pressed == "enter":
                return aliases[selected]
            if pressed in ("rename", "delete", "edit") and aliases[selected] != NEW_ALIAS:
                return pressed, aliases[selected]
            if pressed in ("escape", "interrupt"):
                return None
            if pressed not in ("up", "down"):
                continue
            previous = selected
            selected = (selected + (1 if pressed == "down" else -1)) % len(aliases)
            if selected == previous:
                continue
            # The cursor rests below the list: update only the old and new markers.
            for index, marker in ((previous, " "), (selected, "❯")):
                sys.stdout.write(f"\x1b[{len(aliases) - index}A\r{marker}\x1b[{len(aliases) - index}B\r")
            sys.stdout.flush()
    finally:
        sys.stdout.write("\x1b[0m\n")
        sys.stdout.flush()


def create_alias(config: Path, existing: list[str]) -> bool:
    """Prompt for a Host block and append it only after all fields are valid."""
    try:
        alias = input("Alias name: ").strip()
        if (not alias or any(char.isspace() or char in "*?!#" or ord(char) < 32 for char in alias)
                or alias.casefold() == NEW_ALIAS or alias.casefold() in {name.casefold() for name in existing}):
            print("Invalid alias or alias already exists.", file=sys.stderr)
            return False
        hostname = input("Hostname (IP address or domain): ").strip()
        if not hostname or any(char.isspace() or char == "#" or ord(char) < 32 for char in hostname):
            print("Invalid hostname.", file=sys.stderr)
            return False
        user = input("SSH username: ").strip()
        if not user or any(char.isspace() or char == "#" or ord(char) < 32 for char in user):
            print("Invalid username.", file=sys.stderr)
            return False
        port = input("Port [22]: ").strip() or "22"
        if not port.isascii() or not port.isdecimal() or not 1 <= int(port) <= 65535:
            print("Invalid port (1-65535).", file=sys.stderr)
            return False
        identity = input("Private key file (optional): ").strip()
        if identity and ("\n" in identity or "\r" in identity or '"' in identity or "#" in identity):
            print("Invalid private key path.", file=sys.stderr)
            return False
    except (EOFError, KeyboardInterrupt):
        print("\nCreation cancelled.")
        return False

    block = f"Host {alias}\n    HostName {hostname}\n    User {user}\n    Port {port}\n"
    if identity:
        block += f'    IdentityFile "{identity}"\n'
    try:
        config.parent.mkdir(parents=True, exist_ok=True)
        with config.open("a", encoding="utf-8") as output:
            if config.stat().st_size:
                output.write("\n")
            output.write(block)
    except OSError as exc:
        print(f"Cannot save {config}: {exc}", file=sys.stderr)
        return False
    print(f"Alias {alias} saved to {config}.")
    return True


def find_host(config: Path, alias: str, visited: set[Path] | None = None) -> list[tuple[Path, int, list[str]]]:
    """Locate literal Host directives across local Include files."""
    visited = visited if visited is not None else set()
    config = config.expanduser().resolve()
    if config in visited:
        return []
    visited.add(config)
    lines = config.read_text(encoding="utf-8-sig").splitlines(keepends=True)
    matches = []
    for index, line in enumerate(lines):
        clean = line.split("#", 1)[0].strip()
        host = HOST_DIRECTIVE.match(clean)
        if host and alias in host.group(1).split():
            matches.append((config, index, lines))
        parts = clean.split(None, 1)
        if len(parts) == 2 and parts[0].lower() == "include":
            for pattern in parts[1].split():
                base = Path(pattern).expanduser()
                if not base.is_absolute():
                    base = config.parent / base
                for included in sorted(base.parent.glob(base.name)):
                    if included.is_file():
                        matches.extend(find_host(included, alias, visited))
    return matches


def edit_host(lines: list[str], index: int, alias: str) -> list[str] | None:
    """Prompt for connection settings; preserve unrelated SSH directives."""
    names = HOST_DIRECTIVE.match(lines[index].split("#", 1)[0]).group(1).split()
    if len(names) != 1:
        print("This Host block is shared by multiple aliases; config unchanged.", file=sys.stderr)
        return None
    end = index + 1
    while end < len(lines) and not re.match(r"^\s*(Host|Match)\s+", lines[end], re.IGNORECASE):
        end += 1
    fields = ("HostName", "User", "Port", "IdentityFile")
    found: dict[str, int] = {}
    for position in range(index + 1, end):
        part = lines[position].strip().split(None, 1)
        if part and part[0].casefold() in {field.casefold() for field in fields}:
            name = next(field for field in fields if field.casefold() == part[0].casefold())
            if name in found:
                print(f"Multiple {name} entries; config unchanged.", file=sys.stderr)
                return None
            found[name] = position
    defaults = {}
    for field in fields:
        parts = lines[found[field]].strip().split(None, 1) if field in found else []
        value = parts[1].split(" #", 1)[0] if len(parts) > 1 else ""
        defaults[field] = value.strip().strip('"')
    defaults["Port"] = defaults["Port"] or "22"
    print(f"Editing {alias}: press Enter to keep a value; type - to clear the private key.")
    values = {}
    for field, label in (("HostName", "Hostname"), ("User", "SSH username"),
                         ("Port", "Port"), ("IdentityFile", "Private key file")):
        answer = input(f"{label} [{defaults[field]}]: ").strip()
        values[field] = defaults[field] if not answer else answer
    if values["IdentityFile"] == "-":
        values["IdentityFile"] = ""
    for field in ("HostName", "User"):
        value = values[field]
        if value and (any(char.isspace() or ord(char) < 32 for char in value) or "#" in value):
            print(f"Invalid {field}.", file=sys.stderr)
            return None
    port = values["Port"]
    if not port.isascii() or not port.isdecimal() or not 1 <= int(port) <= 65535:
        print("Invalid port (1-65535).", file=sys.stderr)
        return None
    identity = values["IdentityFile"]
    if any(char in identity for char in '\r\n"#'):
        print("Invalid private key path.", file=sys.stderr)
        return None
    values["IdentityFile"] = f'"{identity}"' if identity else ""
    updated = lines.copy()
    newline = "\r\n" if lines[index].endswith("\r\n") else "\n"
    for field in reversed(fields):
        value = values[field]
        if field in found:
            position = found[field]
            if value:
                original = lines[position]
                comment = original[original.index("#"):] if "#" in original else ""
                comment = comment.rstrip("\r\n")
                updated[position] = f"    {field} {value}{' ' + comment if comment else ''}{newline}"
            else:
                del updated[position]
        elif value and (field != "Port" or value != "22"):
            updated.insert(index + 1, f"    {field} {value}{newline}")
    return updated


def change_alias(config: Path, alias: str, action: str, existing: list[str]) -> bool:
    """Edit one unambiguous Host entry; never alter unrelated blocks."""
    try:
        matches = find_host(config, alias)
        if len(matches) != 1:
            print("Alias has no unique Host definition; config unchanged.", file=sys.stderr)
            return False
        path, index, lines = matches[0]
        line = lines[index]
        host = HOST_DIRECTIVE.match(line.split("#", 1)[0])
        names = host.group(1).split()
        if action == "edit":
            edited = edit_host(lines, index, alias)
            if edited is None:
                return False
            lines = edited
        elif action == "rename":
            replacement = input(f"New name for {alias}: ").strip()
            if (not replacement or any(char.isspace() or char in "*?!#" or ord(char) < 32 for char in replacement)
                    or replacement.casefold() == NEW_ALIAS
                    or replacement.casefold() in {name.casefold() for name in existing}):
                print("Invalid alias or alias already exists.", file=sys.stderr)
                return False
            names[names.index(alias)] = replacement
            lines[index] = re.sub(r"^(\s*Host\s+)[^#\r\n]*", lambda m: m.group(1) + " ".join(names) + re.search(r"\s*$", m.group(0)).group(), line, count=1, flags=re.IGNORECASE)
        elif action == "delete":
            if input(f"Delete {alias} from {path}? Type yes to confirm: ").strip() != "yes":
                print("Deletion cancelled.")
                return False
            if len(names) > 1:
                names.remove(alias)
                lines[index] = re.sub(r"^(\s*Host\s+)[^#\r\n]*", lambda m: m.group(1) + " ".join(names) + re.search(r"\s*$", m.group(0)).group(), line, count=1, flags=re.IGNORECASE)
            else:
                end = index + 1
                while end < len(lines) and not re.match(r"^\s*(Host|Match)\s+", lines[end], re.IGNORECASE):
                    end += 1
                del lines[index:end]
        else:
            raise ValueError(f"Unknown action: {action}")
        # Replace atomically, preserving file permissions and leaving other entries intact.
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", newline="", dir=path.parent, delete=False) as output:
            temporary = Path(output.name)
            output.writelines(lines)
        try:
            temporary.chmod(path.stat().st_mode)
            os.replace(temporary, path)
        finally:
            temporary.unlink(missing_ok=True)
    except (OSError, UnicodeError, EOFError, KeyboardInterrupt) as exc:
        print(f"Change cancelled or failed: {exc}", file=sys.stderr)
        return False
    print(f"Alias {alias} {'edited' if action == 'edit' else 'renamed' if action == 'rename' else 'deleted'} in {path}.")
    return True


def main() -> int:
    config = Path.home() / ".ssh" / "config"
    try:
        aliases = read_aliases(config)
    except OSError as exc:
        print(exc, file=sys.stderr)
        return 1
    if not (sys.stdin.isatty() and sys.stdout.isatty()):
        print("Run the program in an interactive terminal.", file=sys.stderr)
        return 1

    alias = choose_alias([NEW_ALIAS, *sorted(aliases, key=str.casefold)])
    if alias is None:
        return 0
    if alias == NEW_ALIAS:
        return 0 if create_alias(config, aliases) else 1
    if isinstance(alias, tuple):
        action, name = alias
        return 0 if change_alias(config, name, action, aliases) else 1
    print(f"Connecting to {alias}...", flush=True)
    try:
        return subprocess.call(["ssh", alias])
    except FileNotFoundError:
        print("ssh command not found: install OpenSSH and try again.", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        return 130


if __name__ == "__main__":
    sys.exit(main())
