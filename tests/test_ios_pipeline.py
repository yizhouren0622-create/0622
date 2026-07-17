#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import sts_ios_pipeline  # noqa: E402
import unlock_sts  # noqa: E402


class IosPipelineDemoTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp())
        self.fake = self.tmp / "fake_ios_device"
        src = ROOT / "tests" / "fixtures" / "fake_ios_device"
        # copytree requires destination to not exist
        import shutil

        shutil.copytree(src, self.fake)
        self.work = self.tmp / "work"

    def tearDown(self) -> None:
        import shutil

        shutil.rmtree(self.tmp)

    def test_demo_run_end_to_end(self) -> None:
        rc = sts_ios_pipeline.main(
            [
                "--work",
                str(self.work),
                "run",
                "--mode",
                "demo",
                "--fake-device",
                str(self.fake),
                "--remote-prefs",
                "Documents/preferences",
                "--templates",
                str(ROOT / "templates"),
            ]
        )
        self.assertEqual(rc, 0)

        restored = self.fake / "Documents" / "preferences" / "STSUnlockProgress"
        data = json.loads(restored.read_text(encoding="utf-8"))
        self.assertEqual(data["IRONCLADUnlockLevel"], "6")
        self.assertEqual(data["WATCHERUnlockLevel"], "6")

        player = json.loads(
            (self.fake / "Documents" / "preferences" / "STSPlayer").read_text(encoding="utf-8")
        )
        self.assertEqual(player["alias"], "tester")
        self.assertEqual(player["IRONCLAD_WIN"], "true")

        meta = json.loads((self.work / "pipeline_meta.json").read_text(encoding="utf-8"))
        self.assertEqual(meta["mode"], "demo")

    def test_capture_then_unlock_keeps_identity(self) -> None:
        rc = sts_ios_pipeline.main(
            [
                "--work",
                str(self.work),
                "capture",
                "--mode",
                "demo",
                "--fake-device",
                str(self.fake),
            ]
        )
        self.assertEqual(rc, 0)
        rc = sts_ios_pipeline.main(
            [
                "--work",
                str(self.work),
                "unlock",
                "--templates",
                str(ROOT / "templates"),
            ]
        )
        self.assertEqual(rc, 0)
        prefs = unlock_sts.discover_prefs_dir(self.work / "unlocked_preferences")
        player = json.loads((prefs / "STSPlayer").read_text(encoding="utf-8"))
        self.assertEqual(player["name"], "PlayerOne")


if __name__ == "__main__":
    unittest.main()
