# 《Ai》剧本双向同步协议

主编辑文件：`Ai/Ai_演出顺序全本.txt`（按演出顺序）  
分章库文件：`Ai/script/*.md`

---

## 规则（Agent 必须遵守）

1. **你改 txt** → 立刻执行 `python3 Ai/tools/sync_script.py split`，把改动写回对应 MD。
2. **Agent/库改 MD** → 立刻执行 `python3 Ai/tools/sync_script.py build`，刷新全本 txt。
3. **同一轮改动必须两侧一致**后再 commit / push。
4. **禁止删除** txt 里的标记行：
   - `<<<SYNC id="..." file="...">>>`
   - `<<<END SYNC id="...">>>`
5. 可改标记之间的正文；不要改 `id` / `file` 路径，除非同时改 `Ai/tools/sync_manifest.json`。

---

## 命令

```bash
# 库 → 全本 txt
python3 Ai/tools/sync_script.py build

# 全本 txt → 库
python3 Ai/tools/sync_script.py split

# 检查标记与可抽取性
python3 Ai/tools/sync_script.py check
```

---

## 演出顺序（全本结构）

Prologue → Ch1（主轴 Day + Extra Insert 已按时间线交错）→ Ch2 → Ch3 → Endings

第一章在 txt 中已按真实演出顺序排好（例如 Day1 → Insert A 夜 → Insert B 扫除 → Day2 冰棒…），不必再对照两份 MD 手工拼时间线。

---

## 标注规范（与库一致）

| 符号 | 含义 |
|------|------|
| `【】` | 立绘 |
| `（）` | 演出 / UI |
| `""` | 对话框文字 |
