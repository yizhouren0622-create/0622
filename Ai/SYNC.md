# 《Ai》剧本双向同步协议

**分章审阅（主）：** `Ai/script/`（文件名与章节一一对应）  
**剧本汇总（生成）：** `Ai/剧本汇总_演出顺序全本.md`

---

## 分章对照

| id | 文件 |
|----|------|
| prologue | `script/00_序章.md` |
| ch1 | `script/01_第一章_日复一日.md` |
| ch2 | `script/02_第二章_停止预测的人.md` |
| ch3 | `script/03_第三章_被保存的是你.md` |
| endings | `script/04_结局_Bad与True.md` |

---

## 规则

1. **审阅/修改某章** → 改对应分章文件，再 `build` 刷新汇总。
2. **改汇总** → `split` 写回各章。
3. 两侧一致后再 commit / push。
4. 不要删除汇总里的 `<!-- <<<SYNC>>> -->` 标记。

```bash
python3 Ai/tools/sync_script.py build
python3 Ai/tools/sync_script.py split
python3 Ai/tools/sync_script.py check
```
