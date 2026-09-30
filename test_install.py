import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import install


class InstallTests(unittest.TestCase):
    def test_unix_install_and_path_is_idempotent(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            launcher = install.install(home, "posix")
            self.assertTrue(launcher.is_file())
            self.assertTrue(os.access(launcher, os.X_OK))
            self.assertTrue((launcher.parent / "alias_connect.py").is_file())
            self.assertTrue(install.ensure_user_path(launcher.parent, home, "posix"))
            self.assertFalse(install.ensure_user_path(launcher.parent, home, "posix"))
            self.assertEqual((home / ".profile").read_text().count("# aliassh"), 1)

    def test_windows_launcher(self):
        with tempfile.TemporaryDirectory() as tmp:
            launcher = install.install(Path(tmp), "nt")
            self.assertEqual(launcher.name, "aliassh.cmd")
            self.assertIn("alias_connect.py", launcher.read_text())
            self.assertTrue((launcher.parent / "alias_connect.py").is_file())

    def test_main_uses_mock_home_without_modifying_real_profile(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(install.Path, "home", return_value=Path(tmp)), \
                 patch.object(install.os, "name", "posix"):
                self.assertEqual(install.main(), 0)
            self.assertTrue((Path(tmp) / ".profile").exists())


if __name__ == "__main__":
    unittest.main()
