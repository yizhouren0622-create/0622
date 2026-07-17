#!/usr/bin/env python3
"""End-to-end iOS flow: capture STS prefs -> unlock all -> restore.

Official Slay the Spire stores unlocks locally. Network packet capture cannot
unlock content. This pipeline uses USB HouseArrest / backup extract instead.
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

import sts_device
import unlock_sts


ROOT = Path(__file__).resolve().parent
DEFAULT_WORK = ROOT / "work"
DEFAULT_FAKE_DEVICE = ROOT / "tests" / "fixtures" / "fake_ios_device"
DEFAULT_DEMO_DEVICE = ROOT / "work" / "demo_device"


def _work_paths(work: Path) -> dict[str, Path]:
    return {
        "work": work,
        "capture": work / "capture",
        "unlocked": work / "unlocked_preferences",
        "backup": work / "ios_backup",
        "meta": work / "pipeline_meta.json",
    }


def cmd_doctor(_: argparse.Namespace) -> int:
    print("== STS iOS pipeline doctor ==")
    exe = sts_device.which_pymobiledevice3()
    print(f"pymobiledevice3: {exe or 'NOT FOUND (pip install -r requirements.txt)'}")
    try:
        devices = sts_device.list_usb_devices()
        print(f"USB devices: {len(devices)}")
        for dev in devices[:5]:
            print(f"  - {dev}")
    except sts_device.DeviceError as exc:
        print(f"USB devices: unavailable ({exc})")
    try:
        bundle = sts_device.detect_bundle_id()
        print(f"Slay the Spire bundle: {bundle}")
    except sts_device.DeviceError as exc:
        print(f"Slay the Spire bundle: not detected ({exc})")
    print("\n说明: 官方 STS 解锁数据在本地 preferences，不是网络回包。")
    print("所以这里的「抓取」= USB/备份取出容器，不是 HTTP 抓包。")
    return 0


def _prepare_demo_device(fake_device: Path, work: Path) -> Path:
    """Use a work copy when pointing at the pristine repo fixture."""
    src = Path(fake_device)
    if not src.exists():
        src = DEFAULT_FAKE_DEVICE
    if src.resolve() == DEFAULT_FAKE_DEVICE.resolve():
        dst = work / "demo_device"
        if dst.exists():
            shutil.rmtree(dst)
        shutil.copytree(src, dst)
        return dst
    return src


def cmd_capture(args: argparse.Namespace) -> int:
    paths = _work_paths(Path(args.work))
    paths["work"].mkdir(parents=True, exist_ok=True)

    if args.mode == "demo":
        demo_device = _prepare_demo_device(Path(args.fake_device), paths["work"])
        # Subsequent restore should write to the working demo copy.
        args.fake_device = str(demo_device)
        prefs = sts_device.demo_capture(demo_device, paths["capture"])
        bundle = args.bundle_id or "demo.slaythespire"
        # Fixture layout uses Documents/preferences; keep USB default elsewhere.
        remote = (
            "Documents/preferences"
            if args.remote_prefs in (None, "", "preferences")
            else args.remote_prefs
        )
        documents_only = False
    elif args.mode == "backup":
        bundle = args.bundle_id
        backup_dir = Path(args.backup_dir) if args.backup_dir else paths["backup"]
        prefs = sts_device.capture_via_backup(backup_dir, paths["capture"], bundle_id=bundle)
        remote = args.remote_prefs
        documents_only = "Documents" in remote
    else:
        if not sts_device.list_usb_devices():
            raise sts_device.DeviceError("未检测到 iPhone，请用数据线连接并点「信任」")
        bundle = sts_device.detect_bundle_id(args.bundle_id)
        prefs = sts_device.capture_via_house_arrest(bundle, paths["capture"])
        # Infer remote path relative to container/documents root
        remote = args.remote_prefs
        documents_only = prefs.as_posix().endswith("/documents") or "Documents" in remote

    # Normalize a copy into unlocked staging input
    if paths["unlocked"].exists():
        shutil.rmtree(paths["unlocked"])
    shutil.copytree(prefs, paths["unlocked"])

    meta = {
        "bundle_id": bundle,
        "preferences_dir": str(prefs),
        "unlocked_dir": str(paths["unlocked"]),
        "remote_prefs": remote,
        "documents_only": documents_only,
        "mode": args.mode,
        "fake_device": getattr(args, "fake_device", None),
    }
    paths["meta"].write_text(json.dumps(meta, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"已抓取 preferences: {prefs}")
    print(f"工作副本: {paths['unlocked']}")
    print(f"元数据: {paths['meta']}")
    return 0


def cmd_unlock(args: argparse.Namespace) -> int:
    paths = _work_paths(Path(args.work))
    target = Path(args.prefs) if args.prefs else paths["unlocked"]
    if not target.exists():
        raise sts_device.DeviceError(f"找不到待解锁目录: {target}，请先 capture")
    actions = unlock_sts.unlock_all(
        prefs_dir=target,
        templates_dir=Path(args.templates),
        slot=args.slot,
        replace_seen=not args.keep_seen,
        preserve_identity=True,
        dry_run=args.dry_run,
    )
    for action in actions:
        print(action)
    print(f"解锁完成: {unlock_sts.discover_prefs_dir(target)}")
    return 0


def cmd_restore(args: argparse.Namespace) -> int:
    paths = _work_paths(Path(args.work))
    prefs = Path(args.prefs) if args.prefs else paths["unlocked"]
    prefs = unlock_sts.discover_prefs_dir(prefs)
    if not prefs.exists():
        raise sts_device.DeviceError(f"找不到已解锁目录: {prefs}")

    meta = {}
    if paths["meta"].exists():
        meta = json.loads(paths["meta"].read_text(encoding="utf-8"))

    remote = args.remote_prefs
    # Prefer capture metadata when CLI still has the generic default.
    if remote in (None, "", "preferences") and meta.get("remote_prefs"):
        remote = meta["remote_prefs"]
    remote = remote or "preferences"
    documents_only = args.documents_only
    if documents_only is None:
        documents_only = bool(meta.get("documents_only", False))

    if args.mode == "demo":
        demo_root = Path(meta.get("fake_device") or args.fake_device)
        pushed = sts_device.demo_push(prefs, demo_root, remote_prefs=remote)
    elif args.mode == "backup":
        raise sts_device.DeviceError(
            "backup 模式只负责抓取。写回请用 USB 模式:\n"
            "  python sts_ios_pipeline.py restore --mode usb\n"
            "或手动把解锁后的 preferences 用爱思助手/三方工具写回 App 容器。"
        )
    else:
        bundle = args.bundle_id or meta.get("bundle_id")
        if not bundle:
            bundle = sts_device.detect_bundle_id(None)
        # Try inferred remotes if default fails
        candidates = [remote]
        for alt in ("preferences", "Documents/preferences", "Library/preferences"):
            if alt not in candidates:
                candidates.append(alt)
        last_error: Exception | None = None
        pushed = []
        for candidate in candidates:
            docs = documents_only or candidate.startswith("Documents/")
            try:
                pushed = sts_device.push_preferences(
                    bundle,
                    prefs,
                    remote_prefs=candidate if not docs else candidate.removeprefix("Documents/"),
                    documents_only=docs,
                )
                remote = candidate
                break
            except sts_device.DeviceError as exc:
                last_error = exc
                pushed = []
        if not pushed and last_error:
            raise last_error

    print(f"已写回 {len(pushed)} 个文件 -> {remote}")
    for item in pushed[:20]:
        print(f"  {item}")
    if len(pushed) > 20:
        print(f"  ... 另外 {len(pushed) - 20} 个")
    print("请在 iPhone 上划掉 STS 进程后重开游戏。")
    return 0


def cmd_run(args: argparse.Namespace) -> int:
    # capture -> unlock -> restore
    rc = cmd_capture(args)
    if rc != 0:
        return rc
    unlock_args = argparse.Namespace(
        work=args.work,
        prefs=None,
        templates=args.templates,
        slot=args.slot,
        keep_seen=args.keep_seen,
        dry_run=False,
    )
    rc = cmd_unlock(unlock_args)
    if rc != 0:
        return rc
    restore_args = argparse.Namespace(
        work=args.work,
        prefs=None,
        mode=args.mode,
        bundle_id=args.bundle_id,
        remote_prefs=args.remote_prefs,
        documents_only=None,
        fake_device=args.fake_device,
    )
    return cmd_restore(restore_args)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Slay the Spire iOS: 抓取 -> 全解锁 -> 写回（无需 iMazing）",
    )
    parser.add_argument("--work", default=str(DEFAULT_WORK), help="工作目录，默认 ./work")
    sub = parser.add_subparsers(dest="command", required=True)

    doctor = sub.add_parser("doctor", help="检查 USB / pymobiledevice3 / App 是否可见")
    doctor.set_defaults(func=cmd_doctor)

    def add_common_device_flags(p: argparse.ArgumentParser) -> None:
        p.add_argument(
            "--mode",
            choices=("usb", "backup", "demo"),
            default="usb",
            help="usb=数据线 HouseArrest; backup=未加密备份; demo=本地假设备跑通",
        )
        p.add_argument("--bundle-id", help="手动指定 Bundle ID")
        p.add_argument(
            "--remote-prefs",
            default="preferences",
            help="容器内 preferences 相对路径",
        )
        p.add_argument(
            "--backup-dir",
            help="backup 模式的备份目录（可先手动备份）",
        )
        p.add_argument(
            "--fake-device",
            default=str(DEFAULT_FAKE_DEVICE),
            help="demo 模式假设备根目录",
        )

    capture = sub.add_parser("capture", help="从手机/备份/demo 抓取 preferences")
    add_common_device_flags(capture)
    capture.set_defaults(func=cmd_capture)

    unlock = sub.add_parser("unlock", help="解锁工作目录中的 preferences")
    unlock.add_argument("--prefs", help="默认使用 work/unlocked_preferences")
    unlock.add_argument("--templates", default=str(ROOT / "templates"))
    unlock.add_argument("--slot", type=int, default=-1)
    unlock.add_argument("--keep-seen", action="store_true")
    unlock.add_argument("--dry-run", action="store_true")
    unlock.set_defaults(func=cmd_unlock)

    restore = sub.add_parser("restore", help="把解锁后的 preferences 写回手机/demo")
    add_common_device_flags(restore)
    restore.add_argument("--prefs", help="默认使用 work/unlocked_preferences")
    restore.add_argument(
        "--documents-only",
        dest="documents_only",
        action="store_true",
        default=None,
        help="强制走 VendDocuments",
    )
    restore.set_defaults(func=cmd_restore)

    run = sub.add_parser("run", help="一键: capture -> unlock -> restore")
    add_common_device_flags(run)
    run.add_argument("--templates", default=str(ROOT / "templates"))
    run.add_argument("--slot", type=int, default=-1)
    run.add_argument("--keep-seen", action="store_true")
    run.set_defaults(func=cmd_run)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except sts_device.DeviceError as exc:
        print(f"错误: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
