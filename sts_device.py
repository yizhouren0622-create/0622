#!/usr/bin/env python3
"""iOS device capture / restore helpers for Slay the Spire preferences.

Primary path: pymobiledevice3 HouseArrest (USB, no iMazing).
Fallback path: unencrypted iTunes/Finder backup Manifest.db extract.
Demo path: local fake device directory for end-to-end dry runs.
"""

from __future__ import annotations

import json
import re
import shutil
import sqlite3
import subprocess
import sys
from pathlib import Path
from typing import Any, Iterable


BUNDLE_CANDIDATES = (
    "com.humble.SlayTheSpire",
    "com.humblebundle.SlayTheSpire",
    "com.megacrit.cardcrawl",
    "com.megacrit.SlayTheSpire",
)

PREFERENCE_MARKERS = (
    "STSPlayer",
    "STSUnlockProgress",
    "STSUnlocks",
)


class DeviceError(RuntimeError):
    pass


def which_pymobiledevice3() -> str | None:
    from shutil import which

    return which("pymobiledevice3")


def run_cmd(args: list[str], *, check: bool = True) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(
            args,
            check=check,
            text=True,
            capture_output=True,
        )
    except FileNotFoundError as exc:
        raise DeviceError(
            "未找到 pymobiledevice3。请先安装: pip install -r requirements.txt"
        ) from exc


def list_usb_devices() -> list[dict[str, Any]]:
    """Return connected devices via usbmux JSON list."""
    exe = which_pymobiledevice3()
    if not exe:
        raise DeviceError("未安装 pymobiledevice3")
    proc = run_cmd([exe, "usbmux", "list", "--no-color"], check=False)
    if proc.returncode != 0:
        raise DeviceError(proc.stderr.strip() or "无法列出 USB 设备，请检查数据线/信任本电脑")
    text = proc.stdout.strip()
    if not text:
        return []
    # CLI may print a JSON list or python-ish output; prefer JSON.
    try:
        data = json.loads(text)
        if isinstance(data, list):
            return data
    except json.JSONDecodeError:
        pass
    # Fallback: treat non-empty stdout as "some device present"
    return [{"raw": text}]


def list_apps_text() -> str:
    exe = which_pymobiledevice3()
    if not exe:
        raise DeviceError("未安装 pymobiledevice3")
    proc = run_cmd([exe, "apps", "list", "--no-color"], check=False)
    if proc.returncode != 0:
        raise DeviceError(proc.stderr.strip() or "无法列出 App，请解锁手机并点信任")
    return proc.stdout


def detect_bundle_id(preferred: str | None = None) -> str:
    if preferred:
        return preferred
    text = list_apps_text()
    # Exact candidates first
    for bundle in BUNDLE_CANDIDATES:
        if bundle in text:
            return bundle
    # Fuzzy match lines containing slay/spire
    matches = re.findall(
        r"([A-Za-z0-9_.]*(?:[Ss]lay|[Ss]pire|cardcrawl)[A-Za-z0-9_.]*)",
        text,
    )
    for match in matches:
        if match.count(".") >= 2:
            return match
    raise DeviceError(
        "手机上未找到 Slay the Spire。请确认已安装官方 App。\n"
        f"也可手动指定: --bundle-id {BUNDLE_CANDIDATES[0]}"
    )


def _house_arrest_pull(bundle_id: str, remote: str, local: Path, documents_only: bool) -> None:
    exe = which_pymobiledevice3()
    if not exe:
        raise DeviceError("未安装 pymobiledevice3")
    local.parent.mkdir(parents=True, exist_ok=True)
    args = [exe, "apps", "pull", bundle_id, remote, str(local)]
    if documents_only:
        args.append("--documents")
    proc = run_cmd(args, check=False)
    if proc.returncode != 0:
        raise DeviceError(proc.stderr.strip() or f"pull 失败: {remote}")


def _house_arrest_push(bundle_id: str, local: Path, remote: str, documents_only: bool) -> None:
    exe = which_pymobiledevice3()
    if not exe:
        raise DeviceError("未安装 pymobiledevice3")
    args = [exe, "apps", "push", bundle_id, str(local), remote]
    if documents_only:
        args.append("--documents")
    proc = run_cmd(args, check=False)
    if proc.returncode != 0:
        raise DeviceError(proc.stderr.strip() or f"push 失败: {remote}")


def find_preferences_dir(root: Path) -> Path | None:
    if not root.exists():
        return None
    for marker in PREFERENCE_MARKERS:
        direct = root / marker
        if direct.exists():
            return root
        nested = root / "preferences" / marker
        if nested.exists():
            return root / "preferences"
    for marker in PREFERENCE_MARKERS:
        hits = list(root.rglob(marker))
        if hits:
            return hits[0].parent
    # Empty preferences directory still counts
    for candidate in root.rglob("preferences"):
        if candidate.is_dir():
            return candidate
    return None


def capture_via_house_arrest(bundle_id: str, out_dir: Path) -> Path:
    """Pull app container and return local preferences directory."""
    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True)

    errors: list[str] = []
    # Try full container first, then Documents-only.
    for documents_only, remote_guesses in (
        (False, ["/", "preferences", "Documents/preferences", "Library/preferences"]),
        (True, ["/", "preferences", "Documents/preferences"]),
    ):
        container = out_dir / ("documents" if documents_only else "container")
        container.mkdir(parents=True, exist_ok=True)
        try:
            _house_arrest_pull(bundle_id, "/", container, documents_only=documents_only)
        except DeviceError as exc:
            errors.append(str(exc))
            continue
        prefs = find_preferences_dir(container)
        if prefs:
            return prefs
        # Targeted pulls if recursive root pull didn't expose markers
        for remote in remote_guesses:
            target = container / remote.replace("/", "_").strip("_")
            try:
                _house_arrest_pull(bundle_id, remote, target, documents_only=documents_only)
            except DeviceError as exc:
                errors.append(str(exc))
                continue
            prefs = find_preferences_dir(target) or find_preferences_dir(container)
            if prefs:
                return prefs

    raise DeviceError(
        "HouseArrest 未能读到 preferences。\n"
        "可改用备份模式: python sts_ios_pipeline.py capture --mode backup\n"
        + "\n".join(errors[:5])
    )


def push_preferences(
    bundle_id: str,
    prefs_dir: Path,
    *,
    remote_prefs: str,
    documents_only: bool,
    files: Iterable[str] | None = None,
) -> list[str]:
    """Push preference files back into the app container."""
    pushed: list[str] = []
    names = list(files) if files is not None else [p.name for p in prefs_dir.iterdir() if p.is_file()]
    for name in names:
        local = prefs_dir / name
        if not local.is_file():
            continue
        remote = f"{remote_prefs.rstrip('/')}/{name}"
        _house_arrest_push(bundle_id, local, remote, documents_only=documents_only)
        pushed.append(remote)
    if not pushed:
        raise DeviceError("没有可写回的 preference 文件")
    return pushed


def _backup_file_path(backup_dir: Path, file_id: str) -> Path:
    # iOS 10+ hashed layout: XX/FILEID
    nested = backup_dir / file_id[:2] / file_id
    if nested.exists():
        return nested
    flat = backup_dir / file_id
    if flat.exists():
        return flat
    raise FileNotFoundError(file_id)


def extract_preferences_from_backup(backup_dir: Path, out_dir: Path, bundle_id: str | None = None) -> Path:
    """Extract STS preferences from an unencrypted iOS backup."""
    manifest = backup_dir / "Manifest.db"
    if not manifest.exists():
        raise DeviceError(f"备份目录缺少 Manifest.db: {backup_dir}")

    conn = sqlite3.connect(f"file:{manifest}?mode=ro", uri=True)
    try:
        rows = conn.execute(
            "SELECT fileID, domain, relativePath FROM Files "
            "WHERE relativePath LIKE '%STS%' OR relativePath LIKE '%preferences%'"
        ).fetchall()
    finally:
        conn.close()

    if bundle_id:
        rows = [r for r in rows if bundle_id in (r[1] or "")]
    else:
        filtered = [
            r
            for r in rows
            if any(key in (r[1] or "").lower() for key in ("slay", "spire", "humble", "megacrit", "cardcrawl"))
            or any(marker in (r[2] or "") for marker in PREFERENCE_MARKERS)
        ]
        rows = filtered or rows

    if out_dir.exists():
        shutil.rmtree(out_dir)
    prefs_out = out_dir / "preferences"
    prefs_out.mkdir(parents=True)

    copied = 0
    for file_id, domain, rel in rows:
        if not rel or rel.endswith("/"):
            continue
        name = Path(rel).name
        if not (name.startswith("STS") or name.startswith("1_STS") or name.startswith("2_STS")):
            # Keep only STS* preference-like files when possible
            if "preferences" not in rel.replace("\\", "/").lower():
                continue
            if not name.startswith("STS") and not name.startswith(("1_", "2_")):
                continue
        try:
            src = _backup_file_path(backup_dir, file_id)
        except FileNotFoundError:
            continue
        # iOS backup files are often binary plists wrapping content; STS prefs are raw JSON files.
        data = src.read_bytes()
        # Skip Apple backup record wrapper if present by probing JSON
        try:
            text = data.decode("utf-8")
            json.loads(text)
            prefs_out.joinpath(name).write_bytes(data)
            copied += 1
            continue
        except Exception:
            pass
        # Some backups store raw file body after a binary plist header; try last JSON object.
        try:
            start = data.find(b"{")
            end = data.rfind(b"}")
            if start >= 0 and end > start:
                blob = data[start : end + 1]
                json.loads(blob.decode("utf-8"))
                prefs_out.joinpath(name).write_bytes(blob)
                copied += 1
        except Exception:
            continue

    if copied == 0:
        raise DeviceError(
            "备份里没有解析到 STS preferences。\n"
            "请确认: 1) 备份未加密或已解密 2) 备份包含 Slay the Spire\n"
            f"bundle 线索: {bundle_id or 'auto'}"
        )
    return prefs_out


def capture_via_backup(backup_dir: Path, out_dir: Path, bundle_id: str | None = None) -> Path:
    exe = which_pymobiledevice3()
    if exe and not (backup_dir / "Manifest.db").exists():
        backup_dir.mkdir(parents=True, exist_ok=True)
        print("正在创建未加密备份（手机需解锁）...", file=sys.stderr)
        proc = run_cmd([exe, "backup2", "backup", "--full", str(backup_dir)], check=False)
        if proc.returncode != 0:
            raise DeviceError(
                "自动备份失败。请先在 Finder/iTunes 做一次【未加密】备份，"
                f"再把备份目录传给 --backup-dir。\n{proc.stderr.strip()}"
            )
    return extract_preferences_from_backup(backup_dir, out_dir, bundle_id=bundle_id)


def demo_capture(fake_device: Path, out_dir: Path) -> Path:
    """Copy preferences from a local fake device tree."""
    src_prefs = find_preferences_dir(fake_device)
    if not src_prefs:
        raise DeviceError(f"demo 假设备中没有 preferences: {fake_device}")
    if out_dir.exists():
        shutil.rmtree(out_dir)
    dst = out_dir / "preferences"
    shutil.copytree(src_prefs, dst)
    return dst


def demo_push(prefs_dir: Path, fake_device: Path, remote_prefs: str = "Documents/preferences") -> list[str]:
    target = fake_device / remote_prefs
    target.mkdir(parents=True, exist_ok=True)
    pushed: list[str] = []
    for path in prefs_dir.iterdir():
        if path.is_file():
            shutil.copy2(path, target / path.name)
            pushed.append(f"{remote_prefs.rstrip('/')}/{path.name}")
    return pushed
