# 《Ai》剧本双向同步协议

主编辑文件：`Ai/Ai_演出顺序全本.md`（按演出顺序，GitHub 可直接预览）  
分章库文件：`Ai/script/*.md`

---

## 规则（Agent 必须遵守）

1. **你改全本 md** → 立刻执行 `python3 Ai/tools/sync_script.py split`，写回对应分章 MD。
2. **Agent/库改分章 MD** → 立刻执行 `python3 Ai/tools/sync_script.py build`，刷新全本 md。
3. **同一轮改动必须两侧一致**后再 commit / push。
4. **禁止删除**全本里的同步标记（HTML 注释，预览时不可见，编辑时可见）：
   - `<!-- <<<SYNC id="..." file="...">>> -->`
   - `<!-- <<<END SYNC id="...">>> -->`
5. 可改标记之间的正文；不要改 `id` / `file` 路径，除非同时改 `Ai/tools/sync_manifest.json`。

---

## 命令

```bash
# 分章 → 全本
python3 Ai/tools/sync_script.py build

# 全本 → 分章
python3 Ai/tools/sync_script.py split

# 检查
python3 Ai/tools/sync_script.py check
```

---

## 演出顺序

Prologue → Ch1（主轴 Day + Extra Insert 已交错）→ Ch2 → Ch3 → Endings

---

## 标注规范

| 符号 | 含义 |
|------|------|
| `【】` | 立绘 |
| `（）` | 演出 / UI |
| `""` | 对话框文字 |
