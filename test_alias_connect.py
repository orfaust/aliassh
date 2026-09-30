import io
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch

import alias_connect


class AliasTests(unittest.TestCase):
    def test_hosts_includes_and_wildcards(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            included = root / "extra.conf"
            included.write_text("Host remote another\nHost *.internal\nHost remote\n")
            config = root / "config"
            config.write_text("Host main backup # comment\nHost *\nInclude extra.conf\nHost main\n")
            self.assertEqual(alias_connect.read_aliases(config), ["main", "backup", "remote", "another"])

    def test_cyclic_include(self):
        with tempfile.TemporaryDirectory() as directory:
            config = Path(directory) / "config"
            config.write_text("Host local\nInclude config\n")
            self.assertEqual(alias_connect.read_aliases(config), ["local"])

    def test_navigation_updates_only_two_markers(self):
        output = io.StringIO()
        keys = iter(["\xe0", "P", "\r"])
        with patch.object(alias_connect.os, "name", "nt"), \
             patch.dict("sys.modules", {"msvcrt": types.SimpleNamespace(getwch=lambda: next(keys))}), \
             patch.object(alias_connect.sys, "stdout", output):
            self.assertEqual(alias_connect.choose_alias(["first", "second"]), "second")
        rendered = output.getvalue()
        self.assertEqual(rendered.count("first"), 1)
        self.assertEqual(rendered.count("second"), 1)
        self.assertIn("\x1b[2A\r ", rendered)
        self.assertIn("\x1b[1A\r❯", rendered)

    def test_action_keys_and_new_alias_guard(self):
        for key, action in (("r", "rename"), ("d", "delete"), ("e", "edit")):
            keys = iter(["\xe0", "P", key])
            with patch.object(alias_connect.os, "name", "nt"), \
                 patch.dict("sys.modules", {"msvcrt": types.SimpleNamespace(getwch=lambda: next(keys))}), \
                 patch.object(alias_connect.sys, "stdout", io.StringIO()):
                self.assertEqual(alias_connect.choose_alias(["new alias", "server"]), (action, "server"))

    def test_edit_host_values_and_preserve_other_directives(self):
        with tempfile.TemporaryDirectory() as directory:
            config = Path(directory) / "config"
            config.write_text("Host work\n    HostName old.example # note\n    User alice\n    Port 2222\n    IdentityFile \"~/.ssh/old\"\n    ForwardAgent yes\nHost other\n    User bob\n")
            with patch("builtins.input", side_effect=["new.example", "", "22", "-"]):
                self.assertTrue(alias_connect.change_alias(config, "work", "edit", ["work", "other"]))
            self.assertEqual(config.read_text(), "Host work\n    HostName new.example # note\n    User alice\n    Port 22\n    ForwardAgent yes\nHost other\n    User bob\n")

    def test_edit_rejects_invalid_port_and_shared_block(self):
        with tempfile.TemporaryDirectory() as directory:
            config = Path(directory) / "config"
            original = "Host work\n    HostName example.com\nHost shared another\n    User alice\n"
            config.write_text(original)
            with patch("builtins.input", side_effect=["", "", "70000", ""]):
                self.assertFalse(alias_connect.change_alias(config, "work", "edit", ["work", "shared", "another"]))
            with patch("builtins.input") as prompt:
                self.assertFalse(alias_connect.change_alias(config, "shared", "edit", ["work", "shared", "another"]))
                prompt.assert_not_called()
            self.assertEqual(config.read_text(), original)

    def test_rename_in_included_file_preserves_other_hosts(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            config = root / "config"
            config.write_text("Include extra.conf\nHost local\n")
            extra = root / "extra.conf"
            extra.write_text("Host old other # note\n    HostName example.com\nHost untouched\n")
            with patch("builtins.input", return_value="renamed"):
                self.assertTrue(alias_connect.change_alias(config, "old", "rename", ["old", "other", "untouched"]))
            self.assertEqual(extra.read_text(), "Host renamed other # note\n    HostName example.com\nHost untouched\n")
            self.assertEqual(config.read_text(), "Include extra.conf\nHost local\n")

    def test_delete_requires_confirmation_and_preserves_shared_block(self):
        with tempfile.TemporaryDirectory() as directory:
            config = Path(directory) / "config"
            original = "Host one two\n    HostName example.com\nHost next\n    User alice\n"
            config.write_text(original)
            with patch("builtins.input", return_value="no"):
                self.assertFalse(alias_connect.change_alias(config, "one", "delete", ["one", "two"]))
            self.assertEqual(config.read_text(), original)
            with patch("builtins.input", return_value="yes"):
                self.assertTrue(alias_connect.change_alias(config, "one", "delete", ["one", "two"]))
            self.assertEqual(config.read_text(), original.replace("Host one two", "Host two"))
            with patch("builtins.input", return_value="yes"):
                self.assertTrue(alias_connect.change_alias(config, "two", "delete", ["two"]))
            self.assertEqual(config.read_text(), "Host next\n    User alice\n")

    def test_ambiguous_alias_is_not_changed(self):
        with tempfile.TemporaryDirectory() as directory:
            config = Path(directory) / "config"
            original = "Host duplicate\nHost duplicate\n"
            config.write_text(original)
            with patch("builtins.input") as prompt:
                self.assertFalse(alias_connect.change_alias(config, "duplicate", "delete", ["duplicate"]))
                prompt.assert_not_called()
            self.assertEqual(config.read_text(), original)

    def test_create_alias_with_default_port(self):
        with tempfile.TemporaryDirectory() as directory:
            config = Path(directory) / ".ssh" / "config"
            with patch("builtins.input", side_effect=["work", "example.org", "alice", "", ""]):
                self.assertTrue(alias_connect.create_alias(config, []))
            self.assertIn("Host work\n    HostName example.org\n    User alice\n    Port 22\n", config.read_text())

    def test_reject_duplicate_and_invalid_port_without_writing(self):
        with tempfile.TemporaryDirectory() as directory:
            config = Path(directory) / "config"
            config.write_text("Host old\n")
            with patch("builtins.input", side_effect=["OLD"]):
                self.assertFalse(alias_connect.create_alias(config, ["old"]))
            with patch("builtins.input", side_effect=["new", "example.org", "alice", "65536"]):
                self.assertFalse(alias_connect.create_alias(config, ["old"]))
            self.assertEqual(config.read_text(), "Host old\n")

    def test_new_alias_does_not_connect(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            with patch.object(alias_connect.Path, "home", return_value=home), \
                 patch.object(alias_connect.sys.stdin, "isatty", return_value=True), \
                 patch.object(alias_connect.sys.stdout, "isatty", return_value=True), \
                 patch.object(alias_connect, "choose_alias", return_value="new alias") as choose, \
                 patch("builtins.input", side_effect=["work", "example.org", "alice", "", ""]), \
                 patch.object(alias_connect.subprocess, "call") as call:
                self.assertEqual(alias_connect.main(), 0)
                choose.assert_called_once_with(["new alias"])
                call.assert_not_called()
                self.assertEqual(alias_connect.read_aliases(home / ".ssh" / "config"), ["work"])

    def test_main_dispatches_edit_without_ssh(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            (home / ".ssh").mkdir()
            config = home / ".ssh" / "config"
            config.write_text("Host old\n    HostName example.com\n")
            with patch.object(alias_connect.Path, "home", return_value=home), \
                 patch.object(alias_connect.sys.stdin, "isatty", return_value=True), \
                 patch.object(alias_connect.sys.stdout, "isatty", return_value=True), \
                 patch.object(alias_connect, "choose_alias", return_value=("rename", "old")), \
                 patch("builtins.input", return_value="new"), \
                 patch.object(alias_connect.subprocess, "call") as call:
                self.assertEqual(alias_connect.main(), 0)
                call.assert_not_called()
            self.assertEqual(alias_connect.read_aliases(config), ["new"])

    def test_connection_uses_argument_list(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            (home / ".ssh").mkdir()
            (home / ".ssh" / "config").write_text("Host zebra\nHost server\nHost Alpha\n")
            with patch.object(alias_connect.Path, "home", return_value=home), \
                 patch.object(alias_connect.sys.stdin, "isatty", return_value=True), \
                 patch.object(alias_connect.sys.stdout, "isatty", return_value=True), \
                 patch.object(alias_connect, "choose_alias", return_value="server") as choose, \
                 patch.object(alias_connect.subprocess, "call", return_value=0) as call:
                self.assertEqual(alias_connect.main(), 0)
                choose.assert_called_once_with(["new alias", "Alpha", "server", "zebra"])
                call.assert_called_once_with(["ssh", "server"])


if __name__ == "__main__":
    unittest.main()
