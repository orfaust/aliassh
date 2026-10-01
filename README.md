# Alias Connect

A terminal menu for managing SSH aliases in `~/.ssh/config` and connecting to them.

## Requirements

- Python 3.10 or newer
- OpenSSH (`ssh` available on your PATH)
- An interactive terminal

No Python packages need to be installed.

## Install

Install directly from GitHub. In **PowerShell**, use:

```powershell
(Invoke-WebRequest https://raw.githubusercontent.com/orfaust/aliassh/main/bootstrap.py).Content | py -
```

In **Command Prompt** or Git Bash on Windows, use:

```bash
curl -fsSL https://raw.githubusercontent.com/orfaust/aliassh/main/bootstrap.py | py -
```

On macOS or Linux, use:

```sh
curl -fsSL https://raw.githubusercontent.com/orfaust/aliassh/main/bootstrap.py | python3 -
```

In PowerShell, `curl` may be an alias for `Invoke-WebRequest` and does not accept `-fsSL`. These commands fetch the raw `bootstrap.py` from `main`; it downloads `install.py` and `alias_connect.py` over HTTPS and runs the installer. Review the scripts before piping them into Python. **Rerun the same command to update** after changes are published to `main`: it replaces the app and launcher without duplicating the PATH entry.

Alternatively, from a local checkout run:

```sh
python install.py # use python3 on macOS/Linux
```

The installer copies `alias_connect.py` to `~/.local/bin` on macOS/Linux or `%USERPROFILE%\AppData\Local\Programs\aliassh` on Windows and creates the `aliassh` launcher (`aliassh.cmd` on Windows). It appends a PATH entry to `~/.profile` on macOS/Linux or to the Windows user PATH. Open a new terminal, then run:

```sh
aliassh
```

If your shell does not load `~/.profile`, add `~/.local/bin` to that shell's startup file. No administrator rights or third-party Python packages are required. To run without installing, use `python alias_connect.py` from the repository directory (or `python3 alias_connect.py` on macOS/Linux).

To check for a newer commit and update only when needed, run:

```sh
aliassh update
```

This checks GitHub's `main` branch, downloads files pinned to the reported commit, and records the installed commit. It requires internet access. Older installations need to run the installation command above once to gain the `update` command. For local installs without a recorded commit, the first update installs the current upstream release.

## Usage

1. Run `aliassh` in an interactive terminal. The first entry is **new alias**; existing aliases follow in case-insensitive alphabetical order.
2. Use **↑/↓** to select an entry. Press **Enter** to connect (`ssh <alias>`), or **Esc** to quit.
3. On an existing alias, press **e** to edit its hostname, username, port or private key; **r** to rename it; or **d** to delete it. Deletion requires typing `yes` exactly.

When editing, press Enter at a prompt to retain the current value, or type `-` at the private-key prompt to remove the key. Editing a `Host` block shared by multiple aliases is disabled; renaming changes only the selected name, and deleting removes only that name (the shared block remains for the others). Changes are made in the file where the `Host` is declared, including local `Include` files. An alias defined in more than one `Host` directive cannot be edited, renamed or deleted.

Select **new alias** and press Enter to provide a name, hostname (IP address or domain), SSH username, port (press Enter for `22`) and optional private key path. The app appends a `Host` block to `~/.ssh/config` without starting a connection; it creates the file if needed. For example:

```sshconfig
Host my-server
    HostName example.com
    User alice
    Port 22
    IdentityFile "~/.ssh/id_ed25519"
```

The menu includes explicit `Host` names from `~/.ssh/config` and local files referenced by `Include`. Wildcard patterns containing `*`, `?` or `!` are not selectable.

## Tests

```sh
python -m unittest discover -v # use python3 on macOS/Linux
```
