import io
import json
import unittest
from pathlib import Path
from unittest.mock import patch

import bootstrap

COMMIT = "a" * 40


class BootstrapTests(unittest.TestCase):
    def test_resolves_commit_and_installs_files_from_same_revision(self):
        def fetch(request, timeout):
            self.assertEqual(timeout, 20)
            if request.full_url == bootstrap.API_URL:
                return io.BytesIO(json.dumps({"sha": COMMIT}).encode())
            self.assertTrue(request.full_url.startswith(bootstrap.RAW_BASE + COMMIT + "/"))
            name = request.full_url.split("?", 1)[0].rsplit("/", 1)[-1]
            return io.BytesIO(f"# {name}\n".encode())

        def invoke(command, env):
            self.assertEqual(env["ALIASSH_REF"], COMMIT)
            installer = Path(command[1])
            self.assertEqual(installer.read_text(), "# install.py\n")
            self.assertEqual((installer.parent / "alias_connect.py").read_text(), "# alias_connect.py\n")
            return 0

        with patch.dict(bootstrap.os.environ, {"ALIASSH_REF": ""}), \
             patch.object(bootstrap.urllib.request, "urlopen", side_effect=fetch) as get, \
             patch.object(bootstrap.subprocess, "call", side_effect=invoke) as run:
            self.assertEqual(bootstrap.bootstrap(), 0)
            self.assertEqual(get.call_count, 3)
            run.assert_called_once()

    def test_repeat_fetches_current_files(self):
        versions = iter([b"version 1", b"version 2"])
        seen = []

        def fetch(request, timeout):
            if "alias_connect.py" in request.full_url:
                return io.BytesIO(next(versions))
            return io.BytesIO(b"installer")

        def invoke(command, env):
            seen.append((Path(command[1]).parent / "alias_connect.py").read_bytes())
            return 0

        with patch.dict(bootstrap.os.environ, {"ALIASSH_REF": COMMIT}), \
             patch.object(bootstrap.urllib.request, "urlopen", side_effect=fetch), \
             patch.object(bootstrap.subprocess, "call", side_effect=invoke):
            self.assertEqual(bootstrap.bootstrap(), 0)
            self.assertEqual(bootstrap.bootstrap(), 0)
        self.assertEqual(seen, [b"version 1", b"version 2"])

    def test_download_failure_does_not_run_installer(self):
        with patch.dict(bootstrap.os.environ, {"ALIASSH_REF": COMMIT}), \
             patch.object(bootstrap.urllib.request, "urlopen", side_effect=OSError("offline")), \
             patch.object(bootstrap.subprocess, "call") as run:
            self.assertEqual(bootstrap.bootstrap(), 1)
            run.assert_not_called()

    def test_oversized_download_does_not_run_installer(self):
        with patch.dict(bootstrap.os.environ, {"ALIASSH_REF": COMMIT}), \
             patch.object(bootstrap.urllib.request, "urlopen", return_value=io.BytesIO(b"x" * (bootstrap.MAX_FILE_BYTES + 1))), \
             patch.object(bootstrap.subprocess, "call") as run:
            self.assertEqual(bootstrap.bootstrap(), 1)
            run.assert_not_called()


if __name__ == "__main__":
    unittest.main()
