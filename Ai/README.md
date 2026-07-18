# 《Ai》 Scenario Package

全年龄 · 认知系 · 泣系 · Meta ADV

本目录为《Ai》的创作宪法与详细剧本包。  
气质：陪一个人生活，不是攻略一个人。  
玩家最终记住的是作品本身与那段日子——不是「老婆」。

---

## 分章审阅（请按文件分开看）

| 文档 | 内容 |
|------|------|
| [`script/00_Prologue.md`](./script/00_Prologue.md) | 序章（已定稿气质，勿随意加设定） |
| [`script/01_Chapter1.md`](./script/01_Chapter1.md) | 第一章《日复一日》 |
| [`script/02_Chapter2.md`](./script/02_Chapter2.md) | 第二章 |
| [`script/03_Chapter3.md`](./script/03_Chapter3.md) | 第三章 |
| [`script/04_Endings.md`](./script/04_Endings.md) | Bad / True |

连续阅读可用：[`Ai_演出顺序全本.md`](./Ai_演出顺序全本.md)（由分章自动生成）。

---

## 目录结构

```
Ai/
├── README.md
├── SYNC.md
├── Ai_演出顺序全本.md          # 演出顺序合并稿（同步生成）
├── design/                     # 创作宪法与机制
├── notes/
├── tools/                      # sync_script.py
└── script/                     # ★分章审阅正文（每章独立）
```

---

## 第一章创作纪律（摘要）

- 降低约 70% 哲学对白；说话像生活中的人
- 多写普通细节：喷嚏、喘气、卖完、夹娃娃失败、借橡皮
- 不消费女主：少福利堆叠，多「什么都没发生」的陪伴
- 怪问题可以有（自动门），但不要立刻解释成伏笔

详见 [`design/00_Scenario_Bible.md`](./design/00_Scenario_Bible.md) 与 [`SYNC.md`](./SYNC.md)。

---

## 剧本标注

| 符号 | 含义 |
|------|------|
| `【】` | 立绘 |
| `（）` | 演出 / UI |
| `""` | 对话框文字 |

## 同步

```bash
python3 Ai/tools/sync_script.py split   # 全本 → 分章
python3 Ai/tools/sync_script.py build   # 分章 → 全本
```
