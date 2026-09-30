# Alias Connect

A terminal menu for connecting to SSH hosts defined in `~/.ssh/config`.

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

In a Unix shell, replace `py -` with `python3 -`. PowerShell's `curl` may be an alias for `Invoke-WebRequest`, which does not accept `-fsSL`. The URL must point to the **raw file**, not the repository homepage. The bootstrap downloads `install.py` and `alias_connect.py` over HTTPS and runs the installer. Review the script before piping it into Python if you do not trust the source.

Alternatively, from a local checkout run:

```bash
python install.py
```

The installer copies the app to your user directory, creates the `aliassh` command (`aliassh.cmd` on Windows), and adds its directory to your user PATH. Open a new terminal, then run:

```bash
aliassh
```

On Unix the installer updates `~/.profile`; on Windows it updates the user PATH. If your shell does not load `~/.profile`, add `~/.local/bin` to that shell's startup file. No administrator rights or Python packages are required. To run directly without installing, use `python alias_connect.py`.

Use **↑/↓** to select an entry, **Enter** to connect, **e** to edit connection settings, **r** to rename, **d** to delete, or **Esc** to quit. Deletion requires typing `yes` to confirm. Edit prompts for hostname, username, port and private key: press Enter to keep a value or type `-` to remove the private key. Editing a `Host` block shared by multiple aliases is disabled to avoid changing other aliases. Edit, rename and delete update the `Host` definition in the config file where it is declared (including locally included files); if an alias appears in multiple `Host` directives, neither action changes it. Existing aliases are listed alphabetically, ignoring case. Selecting an alias with Enter runs `ssh <alias>` in the current terminal.

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
