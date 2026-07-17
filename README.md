# Slay the Spire 全解锁工具（iOS / PC / Android）

我**无法直接读取你的 iPhone 本地数据**。请把游戏存档导出到电脑后，用本工具修改，再写回手机。

本工具会解锁：

- 全部角色（Silent / Defect / Watcher）
- 全部卡牌 / 遗物解锁进度
- Ascension 20
- Act 4（各角色通关标记）
- 每日挑战 / 自定义模式入口所需标记
- 图鉴：已见卡牌 / 遗物 / Boss（模板覆盖）

## 快速开始

```bash
# 1) 把导出的 preferences 放到 input/（或传入路径）
python3 unlock_sts.py input -o output/unlocked_preferences

# 2) 检查结果后，把 output/unlocked_preferences 写回 iPhone
```

原地修改（自动备份为 `preferences.backup`）：

```bash
python3 unlock_sts.py /path/to/preferences
```

运行测试：

```bash
python3 -m unittest discover -s tests -v
```

## iOS 导出 / 写回步骤

官方 App **通常不开放** iTunes/Finder「文件共享」，所以需要从 App 容器里取出 `preferences`。

### 方法 A：iMazing（推荐，无需越狱）

1. 用数据线连接 iPhone，打开 [iMazing](https://imazing.com/)
2. 选择设备 → **管理 App** / **App 数据**
3. 找到 **Slay the Spire**
4. **导出 App 数据**（Export App Data / Backup App Data）到电脑
5. 在导出包中搜索这些文件名之一：
   - `STSPlayer`
   - `STSUnlockProgress`
   - `STSUnlocks`
6. 它们所在目录就是 `preferences`（常见位置类似）：
   - `Documents/preferences`
   - `Library/preferences`
7. 把整个 `preferences` 文件夹复制到本仓库的 `input/`
8. 运行解锁命令
9. 用 iMazing **写回 / 恢复 App 数据**时，用修改后的 `preferences` 覆盖原目录
10. 在手机上**完全划掉游戏进程**后重新打开

### 方法 B：越狱设备

直接进入 App 沙盒，例如：

```text
/var/mobile/Containers/Data/Application/<UUID>/
```

在其中查找 `preferences` 或 `STSPlayer`，复制到电脑修改后再覆盖回去。

### 方法 C：你已有 PC 版存档

若你其实能拿到 PC 的 `preferences`，也可直接对本工具使用：

```text
Steam/.../SlayTheSpire/preferences
```

格式与移动端一致。

## 命令参数

| 参数 | 说明 |
| --- | --- |
| `prefs` | 存档路径（preferences 或整个 iOS 导出包） |
| `-o DIR` | 输出到新目录，不改原文件 |
| `--slot N` | `0` 默认槽；`1`/`2` 对应 `1_`/`2_` 前缀；`-1` 全部 |
| `--keep-seen` | 保留你原来的图鉴进度，只做合并 |
| `--dry-run` | 只预览，不写入 |
| `--no-backup` | 原地修改时不备份 |

## 会改哪些文件

| 文件 | 作用 |
| --- | --- |
| `STSUnlockProgress` | 各角色解锁等级拉满 |
| `STSUnlocks` | 角色与解锁内容标记 |
| `STSPlayer` | Act 4 / spirits；保留你的 `alias`/`name` |
| `STSDataVagabond` 等 | Ascension 20、每日/图鉴入口条件 |
| `STSSeenCards` / `STSSeenRelics` / `STSSeenBosses` | 图鉴全解锁模板 |

多存档槽文件名可能是 `1_STSPlayer`、`2_STSUnlockProgress` 等，工具会自动处理。

## 把文件交给我（Cloud Agent）时

如果你希望由我直接改你的真实存档：

1. 用 iMazing 导出 Slay the Spire App 数据
2. 至少上传 `preferences` 文件夹（或包含 `STSPlayer` 的导出包）
3. 放到本仓库 `input/` 后告诉我

没有这些文件时，我只能提供工具，无法替你修改手机上的进度。

## 注意

- 修改前务必备份
- 写回后若进度被覆盖，确认已完全重启游戏，且恢复的是正确 App 容器
- 仅用于你自己的单机存档
- 模板来源于社区公开的 preferences 解锁文件（见 `templates/`）
