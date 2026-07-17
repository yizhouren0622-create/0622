#!/usr/bin/env python3
"""Unlock all Slay the Spire meta-progression from a preferences folder.

Works with preference JSON files exported from iOS / Android / PC.
Does not access a phone remotely — place exported files under input/ first.
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent
DEFAULT_TEMPLATES = ROOT / "templates"

CHARACTER_DATA_FILES = (
    "STSDataVagabond",  # Ironclad
    "STSDataTheSilent",
    "STSDataDefect",
    "STSDataWatcher",
)

MERGE_FROM_TEMPLATE = (
    "STSUnlockProgress",
    "STSUnlocks",
    "STSSeenBosses",
    "STSSeenCards",
    "STSSeenRelics",
)

PLAYER_UNLOCK_KEYS = {
    "IRONCLAD_WIN": "true",
    "THE_SILENT_WIN": "true",
    "DEFECT_WIN": "true",
    "WATCHER_WIN": "true",
    "IRONCLAD_SPIRITS": "1",
    "THE_SILENT_SPIRITS": "1",
    "DEFECT_SPIRITS": "1",
    "WATCHER_SPIRITS": "1",
}

CHARACTER_UNLOCK_KEYS = {
    "ASCENSION_LEVEL": "20",
    "LAST_ASCENSION_LEVEL": "20",
    "WIN_COUNT": "1",
    "LOSE_COUNT": "1",
    "HIGHEST_DAILY": "1",
    "TOTAL_FLOORS": "1",
    "ENEMY_KILL": "1",
    "BOSS_KILL": "1",
    "HIGHEST_FLOOR": "1",
}


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    text = path.read_text(encoding="utf-8").strip()
    if not text:
        return {}
    data = json.loads(text)
    if not isinstance(data, dict):
        raise ValueError(f"{path.name} is not a JSON object")
    return {str(k): str(v) if not isinstance(v, str) else v for k, v in data.items()}


def dump_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(data, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def slot_names(base: str, slot: int) -> list[str]:
    """Return candidate filenames for a save slot.

    Slot 0 = default files (STSPlayer)
    Slot 1/2 = prefixed files (1_STSPlayer / 2_STSPlayer)
    Slot -1 = process all present variants.
    """
    if slot < 0:
        return [base, f"1_{base}", f"2_{base}"]
    if slot == 0:
        return [base]
    return [f"{slot}_{base}"]


def resolve_existing(prefs: Path, base: str, slot: int) -> list[Path]:
    found: list[Path] = []
    for name in slot_names(base, slot):
        path = prefs / name
        if path.exists():
            found.append(path)
    return found


def ensure_target(prefs: Path, base: str, slot: int) -> list[Path]:
    """Return paths to edit; create default slot file if missing."""
    existing = resolve_existing(prefs, base, slot)
    if existing:
        return existing
    if slot < 0:
        return [prefs / base]
    return [prefs / slot_names(base, slot)[0]]


def merge_dicts(base: dict[str, Any], overlay: dict[str, Any]) -> dict[str, Any]:
    merged = dict(base)
    merged.update(overlay)
    return merged


def unlock_player(path: Path, template: dict[str, Any], preserve_identity: bool) -> None:
    current = load_json(path)
    identity = {}
    if preserve_identity:
        for key in ("alias", "name"):
            if key in current and current[key]:
                identity[key] = current[key]

    merged = merge_dicts(current, template)
    merged.update(PLAYER_UNLOCK_KEYS)
    if identity:
        merged.update(identity)
    elif "alias" not in merged:
        merged["alias"] = template.get("alias", "unlocked")
    dump_json(path, merged)


def unlock_character(path: Path) -> None:
    current = load_json(path)
    for key, value in CHARACTER_UNLOCK_KEYS.items():
        if key in ("ASCENSION_LEVEL", "LAST_ASCENSION_LEVEL"):
            current[key] = value
            continue
        # Keep larger existing counters; only raise floors for unlock gates.
        try:
            current_val = int(current.get(key, "0"))
            target_val = int(value)
            current[key] = str(max(current_val, target_val))
        except ValueError:
            current[key] = value
    dump_json(path, current)


def unlock_from_template(path: Path, template: dict[str, Any], replace: bool) -> None:
    if replace or not path.exists():
        dump_json(path, template)
        return
    current = load_json(path)
    dump_json(path, merge_dicts(current, template))


def backup_prefs(prefs: Path, backup_dir: Path) -> None:
    if backup_dir.exists():
        shutil.rmtree(backup_dir)
    shutil.copytree(prefs, backup_dir)


def discover_prefs_dir(path: Path) -> Path:
    """Accept either the preferences folder itself or a parent export tree."""
    if (path / "STSPlayer").exists() or (path / "STSUnlockProgress").exists():
        return path
    for candidate in (
        path / "preferences",
        path / "Documents" / "preferences",
        path / "Library" / "preferences",
        path / "AppDomain" / "Documents" / "preferences",
        path / "AppDomain" / "Library" / "Preferences",
    ):
        if candidate.is_dir():
            return candidate
    # Heuristic: first directory containing STS* files
    for child in path.rglob("STSUnlockProgress"):
        return child.parent
    for child in path.rglob("STSPlayer"):
        return child.parent
    return path


def unlock_all(
    prefs_dir: Path,
    templates_dir: Path,
    slot: int = -1,
    replace_seen: bool = True,
    preserve_identity: bool = True,
    dry_run: bool = False,
) -> list[str]:
    prefs = discover_prefs_dir(prefs_dir)
    if not prefs.is_dir():
        raise FileNotFoundError(f"preferences directory not found: {prefs}")

    actions: list[str] = []
    templates = {
        name: load_json(templates_dir / name)
        for name in (*MERGE_FROM_TEMPLATE, "STSPlayer", *CHARACTER_DATA_FILES)
        if (templates_dir / name).exists()
    }

    if dry_run:
        actions.append(f"[dry-run] target preferences: {prefs}")

    for base in MERGE_FROM_TEMPLATE:
        template = templates.get(base, {})
        if not template:
            continue
        targets = ensure_target(prefs, base, slot)
        for target in targets:
            actions.append(f"unlock {target.name}")
            if not dry_run:
                unlock_from_template(
                    target,
                    template,
                    replace=(replace_seen and base.startswith("STSSeen")),
                )

    for target in ensure_target(prefs, "STSPlayer", slot):
        actions.append(f"unlock {target.name}")
        if not dry_run:
            unlock_player(target, templates.get("STSPlayer", {}), preserve_identity)

    for base in CHARACTER_DATA_FILES:
        for target in ensure_target(prefs, base, slot):
            # Seed from template if file is brand new / empty.
            if not dry_run and (not target.exists() or not load_json(target)):
                seed = templates.get(base, {})
                if seed:
                    dump_json(target, seed)
            actions.append(f"unlock {target.name}")
            if not dry_run:
                unlock_character(target)

    return actions


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Unlock all Slay the Spire content in an exported preferences folder.",
    )
    parser.add_argument(
        "prefs",
        nargs="?",
        default=str(ROOT / "input"),
        help="Path to preferences folder or iOS app export (default: ./input)",
    )
    parser.add_argument(
        "-o",
        "--output",
        help="Write unlocked files here instead of modifying prefs in place",
    )
    parser.add_argument(
        "--templates",
        default=str(DEFAULT_TEMPLATES),
        help="Directory containing unlock template JSON files",
    )
    parser.add_argument(
        "--slot",
        type=int,
        default=-1,
        help="Save slot: 0 default, 1/2 for 1_/2_ prefixes, -1 all (default)",
    )
    parser.add_argument(
        "--keep-seen",
        action="store_true",
        help="Merge seen cards/relics/bosses instead of replacing with full templates",
    )
    parser.add_argument(
        "--no-preserve-identity",
        action="store_true",
        help="Do not keep existing STSPlayer alias/name",
    )
    parser.add_argument(
        "--no-backup",
        action="store_true",
        help="Skip automatic backup when modifying in place",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would change without writing files",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    source = Path(args.prefs).expanduser().resolve()
    templates_dir = Path(args.templates).expanduser().resolve()

    if not source.exists():
        print(
            "找不到存档目录。请先把 iOS 导出的 preferences（或整个 App 容器）放到:\n"
            f"  {ROOT / 'input'}\n"
            "或传入路径: python unlock_sts.py /path/to/preferences",
            file=sys.stderr,
        )
        return 1

    if not templates_dir.is_dir():
        print(f"模板目录不存在: {templates_dir}", file=sys.stderr)
        return 1

    if args.output:
        out = Path(args.output).expanduser().resolve()
        if args.dry_run:
            target = source
        else:
            if out.exists():
                shutil.rmtree(out)
            shutil.copytree(source, out)
            target = out
    else:
        target = source
        if not args.dry_run and not args.no_backup:
            prefs_guess = discover_prefs_dir(target)
            backup = prefs_guess.parent / f"{prefs_guess.name}.backup"
            backup_prefs(prefs_guess, backup)
            print(f"已备份到: {backup}")

    actions = unlock_all(
        prefs_dir=target,
        templates_dir=templates_dir,
        slot=args.slot,
        replace_seen=not args.keep_seen,
        preserve_identity=not args.no_preserve_identity,
        dry_run=args.dry_run,
    )

    for action in actions:
        print(action)

    result_dir = discover_prefs_dir(target)
    print(f"\n完成。修改后的 preferences 目录: {result_dir}")
    if args.output:
        print("请把该目录写回 iPhone 上的游戏 App 容器后重启游戏。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
