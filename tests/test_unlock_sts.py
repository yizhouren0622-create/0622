#!/usr/bin/env python3
from __future__ import annotations

import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import unlock_sts  # noqa: E402


class UnlockStsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp())
        self.prefs = self.tmp / "preferences"
        shutil.copytree(ROOT / "tests" / "fixtures" / "sample_prefs", self.prefs)
        self.templates = ROOT / "templates"

    def tearDown(self) -> None:
        shutil.rmtree(self.tmp)

    def test_unlock_progress_and_characters(self) -> None:
        actions = unlock_sts.unlock_all(self.prefs, self.templates, slot=0)
        self.assertTrue(any("STSUnlockProgress" in a for a in actions))

        progress = json.loads((self.prefs / "STSUnlockProgress").read_text())
        self.assertEqual(progress["IRONCLADUnlockLevel"], "6")
        self.assertEqual(progress["THE_SILENTUnlockLevel"], "6")
        self.assertEqual(progress["DEFECTUnlockLevel"], "5")
        self.assertEqual(progress["WATCHERUnlockLevel"], "6")

        unlocks = json.loads((self.prefs / "STSUnlocks").read_text())
        self.assertEqual(unlocks["The Silent"], "2")
        self.assertEqual(unlocks["Defect"], "2")
        self.assertEqual(unlocks["Watcher"], "2")

        player = json.loads((self.prefs / "STSPlayer").read_text())
        self.assertEqual(player["alias"], "tester")
        self.assertEqual(player["name"], "PlayerOne")
        self.assertEqual(player["IRONCLAD_WIN"], "true")
        self.assertEqual(player["DEFECT_WIN"], "true")

        ironclad = json.loads((self.prefs / "STSDataVagabond").read_text())
        self.assertEqual(ironclad["ASCENSION_LEVEL"], "20")
        self.assertEqual(ironclad["WIN_COUNT"], "1")
        self.assertEqual(ironclad["PLAYTIME"], "999")

        self.assertTrue((self.prefs / "STSSeenCards").exists())
        self.assertTrue((self.prefs / "STSSeenRelics").exists())
        self.assertTrue((self.prefs / "STSSeenBosses").exists())

    def test_discover_nested_ios_export(self) -> None:
        export = self.tmp / "ios_export" / "Documents" / "preferences"
        export.parent.mkdir(parents=True)
        shutil.copytree(self.prefs, export)
        discovered = unlock_sts.discover_prefs_dir(self.tmp / "ios_export")
        self.assertEqual(discovered, export)

    def test_cli_output_copy(self) -> None:
        out = self.tmp / "out_prefs"
        code = unlock_sts.main([str(self.prefs), "-o", str(out), "--no-backup"])
        self.assertEqual(code, 0)
        progress = json.loads((out / "STSUnlockProgress").read_text())
        self.assertEqual(progress["WATCHERUnlockLevel"], "6")
        # Original remains unchanged when using -o
        original = json.loads((self.prefs / "STSUnlockProgress").read_text())
        self.assertEqual(original["IRONCLADUnlockLevel"], "1")


if __name__ == "__main__":
    unittest.main()
