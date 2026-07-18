# 《Ai》剧本双向同步协议

**分章审阅（主）：** `Ai/script/00`～`04`（每章独立文档）  
**连续阅读（生成）：** `Ai/Ai_演出顺序全本.md`

---

## 规则

1. **审阅/修改某章** → 直接改对应 `script/0x_*.md`，然后 `build` 刷新全本。
2. **改全本** → `split` 写回各章独立文档。
3. 两侧一致后再 commit / push。
4. 不要删除全本里的 `<!-- <<<SYNC>>> -->` 标记。

```bash
python3 Ai/tools/sync_script.py build
python3 Ai/tools/sync_script.py split
python3 Ai/tools/sync_script.py check
```

---

## 分章对照

| id | 文件 |
|----|------|
| prologue | `script/00_Prologue.md` |
| ch1 | `script/01_Chapter1.md` |
| ch2 | `script/02_Chapter2.md` |
| ch3 | `script/03_Chapter3.md` |
| endings | `script/04_Endings.md` |
