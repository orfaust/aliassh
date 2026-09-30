# Alias Connect

A terminal menu for connecting to SSH hosts defined in `~/.ssh/config`.

## Requirements

- Python 3.10 or newer
- OpenSSH (`ssh` available on your PATH)
- An interactive terminal

No Python packages need to be installed.

## Install

From Command Prompt on Windows (or a shell where `py` is available), install directly from GitHub:

```bash
curl -fsSL https://raw.githubusercontent.com/orfaust/aliassh/main/bootstrap.py | py -
```

The URL must point to the **raw file**, not the repository homepage. **This command will work only after `bootstrap.py`, `install.py`, and `alias_connect.py` have been committed and published on the repository's `main` branch.** The bootstrap downloads `install.py` and `alias_connect.py` from that branch over HTTPS and runs the installer. Review the downloaded script before piping it into Python if you do not trust the source. On Unix, replace `py -` with `python3 -`.

Alternatively, from a local checkout run:

```bash
python install.py
```

The installer copies the app to your user directory, creates the `aliassh` command (`aliassh.cmd` on Windows), and adds its directory to your user PATH. Open a new terminal, then run:

```bash
aliassh
```

On Unix the installer updates `~/.profile`; on Windows it updates the user PATH. If your shell does not load `~/.profile`, add `~/.local/bin` to that shell's startup file. No administrator rights or Python packages are required. To run directly without installing, use `python alias_connect.py`.

Use **↑/↓** to select an entry, **Enter** to connect, **r** to rename, **d** to delete, or **Esc** to quit. Deletion requires typing `yes` to confirm. Rename and delete edit the `Host` definition in the config file where it is declared (including locally included files); if an alias appears in multiple `Host` directives, neither action changes it. Existing aliases are listed alphabetically, ignoring case. Selecting an alias with Enter runs `ssh <alias>` in the current terminal.

The first entry, **new alias**, prompts for an alias name, hostname (IP address or domain), SSH username, port (defaults to `22`), and an optional private key file path. It appends a `Host` block to `~/.ssh/config` without starting a connection. The config file is created if it does not exist. For example:

```sshconfig
Host my-server
    HostName example.com
    User alice
    Port 22
    IdentityFile "~/.ssh/id_ed25519"
```

The menu includes explicit `Host` names from `~/.ssh/config` and locally included config files. SSH wildcard patterns containing `*`, `?`, or `!` are not selectable.

## Tests

```bash
python -m unittest discover -v
```
