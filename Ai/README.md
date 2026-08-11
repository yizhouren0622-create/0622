# 《Ai》 Scenario Package

全年龄 · 认知系 · 泣系 · Meta ADV

气质：陪一个人生活，不是攻略一个人。  
玩家最终记住的是作品本身与那段日子——不是「老婆」。

---

## 分章审阅

| 文档 | 内容 |
|------|------|
| [`script/00_序章.md`](./script/00_序章.md) | 序章 |
| [`script/01_第一章_日复一日.md`](./script/01_第一章_日复一日.md) | 第一章 |
| [`script/02_第二章_停止预测的人.md`](./script/02_第二章_停止预测的人.md) | 第二章 |
| [`script/03_第三章_被保存的是你.md`](./script/03_第三章_被保存的是你.md) | 第三章 |
| [`script/04_第四章_Ai_Original.md`](./script/04_第四章_Ai_Original.md) | 第四章・世界构筑／三结局 |
| [`script/postgame/`](./script/postgame/) | HE 后日谈剧本 |
| [`design/ch3/`](./design/ch3/) | 第三章策划备忘 |
| [`design/ch4/`](./design/ch4/) | 第四章世界构筑策划 |
| [`design/postgame/`](./design/postgame/) | 后日谈策划（Beyond／维护／祂线） |

> 分章存放即可审阅；无单独「全策划汇总版」。  
> `剧本汇总_演出顺序全本.md` 由 `script/`（含 postgame）sync 生成。

---

## 目录

```
Ai/
├── design/
│   ├── ch3/
│   ├── ch4/
│   ├── postgame/          # 解锁双门 · Beyond · Maintenance · 祂线
│   └── 00_Scenario_Bible.md …
├── script/
│   ├── 00～04 …
│   └── postgame/          # 05～08
└── …
```

---

## 标注 / 同步

| 符号 | 含义 |
|------|------|
| `【】` | 立绘 |
| `（）` | 演出 / UI |
| `""` | 对话框文字 |

```bash
python3 Ai/tools/sync_script.py split   # 汇总 → 分章
python3 Ai/tools/sync_script.py build   # 分章 → 汇总
```

详见 [`SYNC.md`](./SYNC.md)。
