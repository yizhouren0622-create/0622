#!/usr/bin/env python3
"""Patch a PC Slay the Spire Watcher save so starter Strikes become Pressure Points+."""

from __future__ import annotations

import argparse
import base64
import json
import os
import re
import shutil
import sys
from datetime import datetime
from pathlib import Path
from typing import Any


SAVE_KEY = "key"
PRESSURE_POINTS_ID = "PathToVictory"
WATCHER_STRIKE_IDS = {"Strike_P", "Strike"}
DEFAULT_STEAM_PATHS = (
    r"C:\Program Files (x86)\Steam\steamapps\common\SlayTheSpire",
    r"C:\Program Files\Steam\steamapps\common\SlayTheSpire",
    r"D:\SteamLibrary\steamapps\common\SlayTheSpire",
    r"E:\SteamLibrary\steamapps\common\SlayTheSpire",
)


def xor_transform(data: bytes | str, *, encode: bool) -> bytes | str:
    if encode:
        assert isinstance(data, str)
        out = bytearray()
        for i, ch in enumerate(data):
            out.append(ord(ch) ^ ord(SAVE_KEY[i % len(SAVE_KEY)]))
        return base64.b64encode(bytes(out))
    assert isinstance(data, bytes)
    raw = base64.b64decode(data)
    chars: list[str] = []
    for i, byte in enumerate(raw):
        chars.append(chr(byte ^ ord(SAVE_KEY[i % len(SAVE_KEY)])))
    return "".join(chars)


def decode_save(path: Path) -> dict[str, Any]:
    raw = path.read_bytes().strip()
    text = xor_transform(raw, encode=False)
    if isinstance(text, bytes):
        text = text.decode("utf-8")
    return json.loads(text)


def encode_save(data: dict[str, Any]) -> bytes:
    plain = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    encoded = xor_transform(plain, encode=True)
    assert isinstance(encoded, bytes)
    return encoded


def find_game_root(explicit: str | None) -> Path | None:
    if explicit:
        root = Path(explicit).expanduser()
        return root if (root / "saves").is_dir() else None
    for candidate in DEFAULT_STEAM_PATHS:
        root = Path(candidate)
        if (root / "saves").is_dir():
            return root
    return None


def list_watcher_saves(saves_dir: Path) -> list[Path]:
    if not saves_dir.is_dir():
        return []
    pattern = re.compile(r"^(?:\d+_)?WATCHER\.autosave$", re.IGNORECASE)
    return sorted(
        p for p in saves_dir.iterdir() if p.is_file() and pattern.match(p.name)
    )


def pick_save_file(saves_dir: Path, save_path: str | None, slot: int | None) -> Path:
    if save_path:
        path = Path(save_path).expanduser()
        if not path.exists():
            raise FileNotFoundError(f"找不到存档: {path}")
        return path

    candidates = list_watcher_saves(saves_dir)
    if slot is not None:
        prefixed = saves_dir / f"{slot}_WATCHER.autosave"
        if prefixed.exists():
            return prefixed
        raise FileNotFoundError(f"找不到槽位 {slot} 的 WATCHER.autosave")

    if not candidates:
        raise FileNotFoundError(
            "找不到 WATCHER.autosave。\n"
            "请先在游戏里：选观者 -> 开始新游戏 -> 到 Neow 界面（或任意能 Continue 的点），"
            "然后关闭游戏再运行本脚本。"
        )
    if len(candidates) == 1:
        return candidates[0]
    # Prefer unprefixed slot 0, else newest file.
    for preferred in ("WATCHER.autosave", "0_WATCHER.autosave"):
        hit = saves_dir / preferred
        if hit.exists():
            return hit
    return max(candidates, key=lambda p: p.stat().st_mtime)


def card_is_watcher_strike(card: dict[str, Any]) -> bool:
    card_id = str(card.get("id", ""))
    return card_id in WATCHER_STRIKE_IDS


def build_pressure_card(*, upgraded: bool = True) -> dict[str, Any]:
    return {
        "id": PRESSURE_POINTS_ID,
        "misc": 0,
        "upgrades": 1 if upgraded else 0,
    }


def patch_strikes_to_pressure(
    save: dict[str, Any],
    *,
    replace_eruption: bool = False,
    upgraded: bool = True,
) -> tuple[dict[str, Any], int]:
    cards = save.get("cards")
    if not isinstance(cards, list):
        raise ValueError("存档里没有 cards 列表，可能不是有效的 autosave")

    replaced = 0
    new_cards: list[dict[str, Any]] = []
    for card in cards:
        if not isinstance(card, dict):
            new_cards.append(card)
            continue
        card_id = str(card.get("id", ""))
        if card_is_watcher_strike(card) or (replace_eruption and card_id == "Eruption"):
            new_cards.append(build_pressure_card(upgraded=upgraded))
            replaced += 1
        else:
            new_cards.append(card)

    save["cards"] = new_cards
    return save, replaced


def backup_save(path: Path) -> Path:
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = path.with_suffix(path.suffix + f".backup_{stamp}")
    shutil.copy2(path, backup)
    return backup


def print_deck(save: dict[str, Any]) -> None:
    cards = save.get("cards", [])
    print("当前卡组:")
    for idx, card in enumerate(cards, 1):
        if not isinstance(card, dict):
            continue
        card_id = card.get("id", "?")
        upgrades = card.get("upgrades", 0)
        suffix = "+" if upgrades else ""
        print(f"  {idx:2d}. {card_id}{suffix}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="把观者存档里的默认 Strike 全部替换成点穴+（PathToVictory+）",
    )
    parser.add_argument(
        "--game-root",
        help="SlayTheSpire 安装目录（包含 saves/）",
    )
    parser.add_argument(
        "--save",
        help="直接指定 .autosave 文件路径",
    )
    parser.add_argument(
        "--slot",
        type=int,
        help="存档槽位：0=默认，1/2 对应 1_/2_ 前缀",
    )
    parser.add_argument(
        "--replace-eruption",
        action="store_true",
        help="连起始攻击 Eruption 也替换成点穴+",
    )
    parser.add_argument(
        "--no-upgrade",
        action="store_true",
        help="生成未升级的点穴（默认生成点穴+）",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="只预览，不写回存档",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="列出 saves 目录里的 WATCHER.autosave",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    game_root = find_game_root(args.game_root)
    if args.save:
        save_path = pick_save_file(Path("."), args.save, args.slot)
    else:
        if not game_root:
            print(
                "找不到 Steam 版 Slay the Spire 安装目录。\n"
                "请用 --game-root 指定，例如:\n"
                r'  python start_watcher_pressure_run.py --game-root "C:\Program Files (x86)\Steam\steamapps\common\SlayTheSpire"',
                file=sys.stderr,
            )
            return 1
        saves_dir = game_root / "saves"
        if args.list:
            saves = list_watcher_saves(saves_dir)
            if not saves:
                print(f"{saves_dir} 里没有 WATCHER.autosave")
                return 1
            for item in saves:
                print(item)
            return 0
        save_path = pick_save_file(saves_dir, None, args.slot)

    print(f"目标存档: {save_path}")
    save = decode_save(save_path)
    print_deck(save)

    patched, replaced = patch_strikes_to_pressure(
        save,
        replace_eruption=args.replace_eruption,
        upgraded=not args.no_upgrade,
    )
    if replaced == 0:
        print(
            "\n没有找到可替换的 Strike 卡（Strike_P / Strike）。\n"
            "请确认这是观者开局存档，且 deck 里还有默认打击。",
            file=sys.stderr,
        )
        return 1

    print(f"\n将替换 {replaced} 张 Strike -> 点穴{'+' if not args.no_upgrade else ''}")
    print_deck(patched)

    if args.dry_run:
        print("\n[dry-run] 未写回存档。")
        return 0

    backup = backup_save(save_path)
    save_path.write_bytes(encode_save(patched))
    print(f"\n已备份: {backup}")
    print(f"已写回: {save_path}")
    print("\n下一步: 打开 Slay the Spire -> Continue -> 开始这一盘观者。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
