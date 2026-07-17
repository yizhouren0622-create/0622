#!/usr/bin/env python3
"""《Ai》演出顺序全本.md ↔ 分章 MD 双向同步。

用法:
  python3 sync_script.py build   # 分章 MD → 全本.md
  python3 sync_script.py split   # 全本.md → 分章 MD
  python3 sync_script.py check   # 检查两侧标记是否齐全
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]  # Ai/
MANIFEST_PATH = Path(__file__).resolve().parent / "sync_manifest.json"

# 支持 HTML 注释标记（GitHub 预览更干净）与旧版裸标记
BEGIN_RE = re.compile(
    r"^(?:<!--\s*)?<<<SYNC\s+id=\"(?P<id>[^\"]+)\"\s+file=\"(?P<file>[^\"]+)\"\s*>>>(?:\s*-->)?\s*$"
)
END_RE = re.compile(
    r"^(?:<!--\s*)?<<<END\s+SYNC\s+id=\"(?P<id>[^\"]+)\"\s*>>>(?:\s*-->)?\s*$"
)


def load_manifest() -> dict:
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


def full_doc_path(manifest: dict) -> Path:
    rel = manifest.get("full_path") or manifest.get("txt_path")
    if not rel:
        raise KeyError("manifest 缺少 full_path")
    return ROOT / rel


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not text.endswith("\n"):
        text += "\n"
    path.write_text(text, encoding="utf-8")


HEADING_RE = re.compile(r"^(#{1,6})\s+(.*)$")


def heading_level(line: str) -> int | None:
    m = HEADING_RE.match(line.rstrip("\n"))
    return len(m.group(1)) if m else None


def extract_by_heading(file_text: str, heading: str, until_heading: str | None = None) -> str:
    """从指定标题起截取；包含更深级标题；在 until_heading 或同级/更高级标题前停下。"""
    lines = file_text.splitlines(keepends=True)
    start = None
    start_level = None
    for i, line in enumerate(lines):
        if line.rstrip("\n") == heading:
            start = i
            start_level = heading_level(line)
            break
    if start is None:
        raise ValueError(f"找不到段落: {heading!r}")

    end = len(lines)
    for j in range(start + 1, len(lines)):
        raw = lines[j].rstrip("\n")
        if until_heading and raw == until_heading:
            end = j
            break
        lvl = heading_level(lines[j])
        if lvl is not None and start_level is not None and lvl <= start_level:
            end = j
            break
    return "".join(lines[start:end]).rstrip() + "\n"


def extract_from_heading_to_end(file_text: str, heading: str) -> str:
    idx = file_text.find(heading)
    if idx < 0:
        raise ValueError(f"找不到段落: {heading!r}")
    return file_text[idx:]


def get_block_content(item: dict) -> str:
    path = ROOT / item["file"]
    text = read_text(path)
    if "heading" not in item:
        return text
    heading = item["heading"]
    until_heading = item.get("until_heading")
    if item.get("through") == "---" and heading.startswith("# "):
        if not text.lstrip().startswith("#"):
            raise ValueError(f"{item['file']} 缺少一级标题")
        m = re.search(r"^##\s+", text, flags=re.M)
        if not m:
            return text
        return text[: m.start()].rstrip() + "\n"
    if item.get("to_eof"):
        return extract_from_heading_to_end(text, heading)
    if until_heading:
        return extract_by_heading(text, heading, until_heading=until_heading)
    return extract_by_heading(text, heading)


def sync_begin(item_id: str, file_rel: str) -> str:
    return f'<!-- <<<SYNC id="{item_id}" file="{file_rel}">>> -->\n'


def sync_end(item_id: str) -> str:
    return f'<!-- <<<END SYNC id="{item_id}">>> -->\n'


def build_full(manifest: dict) -> Path:
    out_path = full_doc_path(manifest)
    parts: list[str] = []
    parts.append("# 《Ai》演出顺序全本\n\n")
    parts.append("> 按真实演出顺序排列的完整剧本。在 GitHub 上直接预览 / 编辑本文件即可。\n\n")
    parts.append("## 双向同步\n\n")
    parts.append("1. 你改本文件 → `python3 Ai/tools/sync_script.py split`（写回 `script/*.md`）\n")
    parts.append("2. Agent 改分章 MD → `python3 Ai/tools/sync_script.py build`（刷新本文件）\n")
    parts.append("3. **不要删除** HTML 注释里的 `<<<SYNC>>>` / `<<<END SYNC>>>` 标记\n")
    parts.append("4. 标注：`【立绘】` `（演出/UI）` `\"对白\"`\n\n")
    parts.append("---\n\n")

    for item in manifest["performance_order"]:
        content = get_block_content(item).rstrip() + "\n"
        parts.append(sync_begin(item["id"], item["file"]))
        parts.append(f'## {item["title"]}\n\n')
        parts.append(content)
        if not content.endswith("\n"):
            parts.append("\n")
        parts.append(sync_end(item["id"]))
        parts.append("\n")

    write_text(out_path, "".join(parts))
    return out_path


def parse_full(doc: str) -> dict[str, dict]:
    lines = doc.splitlines(keepends=True)
    blocks: dict[str, dict] = {}
    i = 0
    while i < len(lines):
        m = BEGIN_RE.match(lines[i].rstrip("\n"))
        if not m:
            i += 1
            continue
        block_id = m.group("id")
        file_path = m.group("file")
        i += 1
        # 跳过本工具注入的导航标题（## title）
        if i < len(lines) and lines[i].startswith("## "):
            i += 1
            if i < len(lines) and lines[i].strip() == "":
                i += 1
        body_lines: list[str] = []
        while i < len(lines):
            end = END_RE.match(lines[i].rstrip("\n"))
            if end:
                if end.group("id") != block_id:
                    raise ValueError(f"END 标记 id 不匹配: {end.group('id')} != {block_id}")
                i += 1
                break
            body_lines.append(lines[i])
            i += 1
        else:
            raise ValueError(f"缺少 END SYNC: {block_id}")
        body = "".join(body_lines).rstrip() + "\n"
        blocks[block_id] = {"file": file_path, "body": body}
    return blocks


def rebuild_files(manifest: dict, blocks: dict[str, dict]) -> list[Path]:
    file_section_order: dict[str, list[str]] = {
        "script/00_Prologue.md": ["prologue"],
        "script/01_Chapter1.md": [
            "ch1_header",
            "ch1_day1",
            "ch1_day2",
            "ch1_day3",
            "ch1_day4",
            "ch1_day5",
            "ch1_day6",
            "ch1_day7",
            "ch1_day8_part1",
            "ch1_day8_part2",
        ],
        "script/01_Chapter1_Extra.md": [
            "ch1_insert_a",
            "ch1_insert_b",
            "ch1_insert_c",
            "ch1_insert_d",
            "ch1_insert_e",
            "ch1_insert_f",
            "ch1_insert_g",
            "ch1_insert_h",
            "ch1_insert_i",
            "ch1_insert_j",
            "ch1_insert_k",
            "ch1_insert_l",
            "ch1_insert_m",
            "ch1_insert_n",
            "ch1_extra_header_check",
        ],
        "script/02_Chapter2.md": ["ch2"],
        "script/03_Chapter3.md": ["ch3"],
        "script/04_Endings.md": ["endings"],
    }

    extra_header = (
        "# Chapter 1 扩写卷｜日常变奏（插入用）\n\n"
        "本文件为第一章的时长补强。  \n"
        "插入位置见各节标注。与主文件 `01_Chapter1.md` 同一时间线，不新增设定。  \n"
        "目标：把 Ch1 从「大纲密度」拉到约 70 分钟可玩文本。\n\n"
        "---\n\n"
    )

    written: list[Path] = []
    for file_rel, ids in file_section_order.items():
        missing = [i for i in ids if i not in blocks]
        if missing:
            raise ValueError(f"{file_rel} 缺少区块: {missing}")
        chunks = [blocks[i]["body"].rstrip() + "\n" for i in ids]
        if file_rel == "script/01_Chapter1_Extra.md":
            first = chunks[0]
            if first.lstrip().startswith("# Chapter 1 扩写卷"):
                text = "\n".join(chunk.rstrip() for chunk in chunks) + "\n"
            else:
                text = extra_header + "\n".join(chunk.rstrip() + "\n" for chunk in chunks)
                if not text.endswith("\n"):
                    text += "\n"
        elif file_rel == "script/01_Chapter1.md":
            text = "\n".join(chunk.rstrip() + "\n" for chunk in chunks)
        else:
            text = chunks[0] if len(chunks) == 1 else "\n".join(c.rstrip() + "\n" for c in chunks)
        path = ROOT / file_rel
        write_text(path, text)
        written.append(path)
    return written


def cmd_build() -> None:
    manifest = load_manifest()
    path = build_full(manifest)
    print(f"[build] wrote {path}")


def cmd_split() -> None:
    manifest = load_manifest()
    path = full_doc_path(manifest)
    blocks = parse_full(read_text(path))
    expected = {item["id"] for item in manifest["performance_order"]}
    got = set(blocks)
    if expected != got:
        missing = sorted(expected - got)
        extra = sorted(got - expected)
        raise SystemExit(f"[split] 标记不匹配 missing={missing} extra={extra}")
    written = rebuild_files(manifest, blocks)
    for p in written:
        print(f"[split] updated {p}")


def cmd_check() -> None:
    manifest = load_manifest()
    path = full_doc_path(manifest)
    if not path.exists():
        raise SystemExit(f"[check] 全本不存在，请先 build: {path}")
    blocks = parse_full(read_text(path))
    expected = [item["id"] for item in manifest["performance_order"]]
    ok = True
    for i in expected:
        if i not in blocks:
            print(f"[check] MISSING in full doc: {i}")
            ok = False
    for item in manifest["performance_order"]:
        try:
            get_block_content(item)
        except Exception as e:
            print(f"[check] MD extract fail {item['id']}: {e}")
            ok = False
    if ok:
        print(f"[check] OK — {len(expected)} blocks")
    else:
        raise SystemExit(1)


def main() -> None:
    if len(sys.argv) != 2 or sys.argv[1] not in {"build", "split", "check"}:
        print(__doc__)
        raise SystemExit(2)
    {"build": cmd_build, "split": cmd_split, "check": cmd_check}[sys.argv[1]]()


if __name__ == "__main__":
    main()
