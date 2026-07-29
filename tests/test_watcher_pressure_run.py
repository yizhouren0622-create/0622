#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import start_watcher_pressure_run as swpr  # noqa: E402


class WatcherPressureRunTests(unittest.TestCase):
    def test_patch_strikes(self) -> None:
        save = {
            "cards": [
                {"id": "Strike_P", "misc": 0, "upgrades": 0},
                {"id": "Strike_P", "misc": 0, "upgrades": 1},
                {"id": "Defend_P", "misc": 0, "upgrades": 0},
                {"id": "Eruption", "misc": 0, "upgrades": 0},
                {"id": "Vigilance", "misc": 0, "upgrades": 0},
            ]
        }
        patched, replaced = swpr.patch_strikes_to_pressure(save)
        self.assertEqual(replaced, 2)
        ids = [c["id"] for c in patched["cards"]]
        self.assertEqual(ids.count("PathToVictory"), 2)
        self.assertEqual(ids.count("Defend_P"), 1)
        self.assertEqual(ids.count("Eruption"), 1)
        upgraded = [c for c in patched["cards"] if c["id"] == "PathToVictory"]
        self.assertTrue(all(c["upgrades"] == 1 for c in upgraded))

    def test_encode_decode_roundtrip(self) -> None:
        original = {
            "cards": [{"id": "Strike_P", "misc": 0, "upgrades": 0}],
            "current_health": 72,
        }
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "WATCHER.autosave"
            path.write_bytes(swpr.encode_save(original))
            loaded = swpr.decode_save(path)
            self.assertEqual(loaded["cards"][0]["id"], "Strike_P")
            self.assertEqual(loaded["current_health"], 72)

    def test_cli_dry_run(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            save_path = Path(tmp) / "WATCHER.autosave"
            payload = {
                "cards": [
                    {"id": "Strike_P", "misc": 0, "upgrades": 0},
                    {"id": "Strike_P", "misc": 0, "upgrades": 0},
                ]
            }
            save_path.write_bytes(swpr.encode_save(payload))
            rc = swpr.main(["--save", str(save_path), "--dry-run"])
            self.assertEqual(rc, 0)
            loaded = swpr.decode_save(save_path)
            self.assertEqual(loaded["cards"][0]["id"], "Strike_P")

    def test_cli_writes_upgraded_pressure(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            save_path = Path(tmp) / "WATCHER.autosave"
            payload = {
                "cards": [
                    {"id": "Strike_P", "misc": 0, "upgrades": 0},
                    {"id": "Strike_P", "misc": 0, "upgrades": 0},
                    {"id": "Strike_P", "misc": 0, "upgrades": 0},
                    {"id": "Strike_P", "misc": 0, "upgrades": 0},
                ]
            }
            save_path.write_bytes(swpr.encode_save(payload))
            rc = swpr.main(["--save", str(save_path)])
            self.assertEqual(rc, 0)
            loaded = swpr.decode_save(save_path)
            self.assertEqual(len(loaded["cards"]), 4)
            for card in loaded["cards"]:
                self.assertEqual(card["id"], "PathToVictory")
                self.assertEqual(card["upgrades"], 1)


if __name__ == "__main__":
    unittest.main()
