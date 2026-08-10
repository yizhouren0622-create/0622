# 《Ai》 Scenario Package

全年龄 · 认知系 · 泣系 · Meta ADV

气质：陪一个人生活，不是攻略一个人。  
玩家最终记住的是作品本身与那段日子——不是「老婆」。

---

## 分章审阅（文件名 = 章节）

| 文档 | 内容 |
|------|------|
| [`script/00_序章.md`](./script/00_序章.md) | 序章（对齐定稿） |
| [`script/01_第一章_日复一日.md`](./script/01_第一章_日复一日.md) | 第一章 |
| [`script/02_第二章_停止预测的人.md`](./script/02_第二章_停止预测的人.md) | 第二章 |
| [`script/03_第三章_被保存的是你.md`](./script/03_第三章_被保存的是你.md) | 第三章 |
| [`script/04_第四章_Ai_Original.md`](./script/04_第四章_Ai_Original.md) | 第四章・世界构筑／三结局 |
| [`design/04_Chapter4_World_Construction.md`](./design/04_Chapter4_World_Construction.md) | 轻肉鸽系统设计 |

> `Ai/剧本汇总_演出顺序全本.md` 仅由 `Ai/script/` 生成；分章正文以 `script/` 为准。

---

## 目录

```
Ai/
├── README.md
├── SYNC.md
├── 剧本汇总_演出顺序全本.md   # 汇总（演出顺序）
├── art/                       # 图标 / 标题 UI 备选
│   ├── icons/
│   └── ui/
├── design/
├── notes/
├── tools/
└── script/                    # ★分章正文
    ├── 00_序章.md
    ├── 01_第一章_日复一日.md
    ├── 02_第二章_停止预测的人.md
    ├── 03_第三章_被保存的是你.md
    └── 04_结局_Bad与True.md
```

美术备选说明见 [`art/README.md`](./art/README.md)。

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

详见 [`SYNC.md`](./SYNC.md) 与 [`design/00_Scenario_Bible.md`](./design/00_Scenario_Bible.md)。
