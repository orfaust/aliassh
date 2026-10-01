# Agent instructions — aliassh

## Project

- Repository root is this directory (`aliassh/`), not its parent. Python 3.10+; standard library only. User-facing text and documentation are in English.
- `alias_connect.py`: reads `~/.ssh/config` and local `Include` files, renders the interactive menu, creates/edits/renames/deletes `Host` entries, and starts `ssh` with an argument list (never a shell command).
- `install.py`: copies the application into a user-owned directory, creates the `aliassh` launcher, updates the user PATH, and records the installed upstream SHA in `.aliassh-version`. `bootstrap.py`: resolves `main` via GitHub API, downloads `install.py` and `alias_connect.py` pinned to that commit, and runs the installer. `aliassh update` compares the recorded SHA with `main` and runs the pinned bootstrap only when they differ.
- `README.md` documents installation, keys and usage. Keep it synchronized with changes to commands or UI behavior.

## Safety and behavior

- Never use the real `~/.ssh/config`, SSH keys, or user PATH for tests. Use temporary directories and mocks; never initiate a real SSH connection in tests.
- Preserve unrelated SSH directives and the originating file when editing included hosts. Reject ambiguous duplicate definitions and shared `Host` blocks when edits could affect other aliases. Require explicit confirmation before deleting an alias.
- Keep alias input validation and atomic file replacement for edits; do not interpolate alias names into a shell command.
- The menu supports Enter (connect), e (edit connection fields), r (rename), d (delete), Esc (quit), and arrow keys. `new alias` is always first; remaining entries are alphabetical.
- Installation changes the user's PATH/profile. Do not run `python install.py` during validation against a real home directory. Already installed users must reinstall once to receive new CLI features; after that `aliassh update` handles published commits. Mock GitHub API and raw downloads in tests.

## Verification

From the repository root:

```bash
python -m unittest discover -v
python -m py_compile alias_connect.py install.py bootstrap.py
git diff --check
```

Tests live in `test_alias_connect.py`, `test_install.py` and `test_bootstrap.py`. Test new behavior using temporary config files and mocked input, terminal keys, SSH invocation and network downloads. Avoid publishing or executing the remote `curl | py` installer merely to verify documentation.
