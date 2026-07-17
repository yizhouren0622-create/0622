# 《Ai》 Scenario Package

全年龄 · 认知系 · 泣系 · Meta ADV

本目录为《Ai》的创作宪法与详细剧本包。  
不是传统 Prompt，而是保证 Agent / 编剧始终保持同一种创作思想的 Scenario Bible。

---

## 目录结构

```
Ai/
├── README.md                          # 本文件
├── SYNC.md                            # 全本 ↔ 分章 双向同步协议
├── Ai_演出顺序全本.md                  # ★按演出顺序的完整剧本（主编辑稿）
├── design/                            # 创作宪法与机制（不同步进全本）
├── notes/
├── tools/
│   ├── sync_manifest.json             # 区块映射
│   └── sync_script.py                 # build / split / check
└── script/                            # 分章库（与全本双向同步）
    ├── 00_Prologue.md
    ├── 01_Chapter1.md
    ├── 01_Chapter1_Extra.md
    ├── 02_Chapter2.md
    ├── 03_Chapter3.md
    └── 04_Endings.md
```

> **改剧本请优先改** [`Ai_演出顺序全本.md`](./Ai_演出顺序全本.md)，然后 `python3 Ai/tools/sync_script.py split`。  
> Agent 改 `script/*.md` 后必须 `python3 Ai/tools/sync_script.py build`。详见 [`SYNC.md`](./SYNC.md)。

---

## 剧本标注规范

| 符号 | 含义 |
|------|------|
| `【】` | 立绘变化 / 表情 / 姿势 |
| `（）` | UI / 演出 / 系统行为 / 镜头指示 |
| `""` | 对话框内显示的文字 |
| `＊旁白＊` | 旁白 / 内心独白（无名字框） |
| `＞选项` | 玩家选择 |

---

## 创作优先级（不可颠倒）

**人物 ＞ 情绪 ＞ 日常 ＞ 剧情 ＞ 世界观 ＞ Meta ＞ 反转**

最高规则：

> 所有世界观设定，都必须以「一个女孩正在发生什么变化」来表现，  
> 而不是以「世界发生了什么」来表现。

最终目标体验：

> 玩家通关后第一反应不是「原来世界观是这样」，  
> 而是「原来她一直都是这样」。

---

## 流程

```
Prologue → Chapter1 → Chapter2 → Chapter3 → True / Bad
```

无攻略角色。无真正路线。所有伪分支最终收束。  
结局由玩家是否真正「认识」她决定，不是数值攻略。
