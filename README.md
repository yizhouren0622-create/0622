# Slay the Spire 工具集

本仓库包含两类工具：

1. **iOS / 全解锁**：`sts_ios_pipeline.py` / `unlock_sts.py`
2. **PC 观者点穴+ 开局**：`start_watcher_pressure_run.py`（本文后半段）

---

## PC：观者默认攻击全改成「点穴+」

把 Steam 版观者存档里的 4 张默认 **Strike** 替换成 **点穴+**（内部 ID：`PathToVictory`），然后你在游戏里点 **Continue** 开这一盘。

### 重要限制

- 云 Agent **不能**直接操作你电脑上的 `C:\Users\...\Downloads\0622-cursor-sts-unlock-all-83e0`
- 也**不能**远程读取你本机已插线的 iPhone / 已打开的 Steam 游戏
- 需要你在 **Windows 本机**双击脚本运行

### 最快用法（Windows，推荐虚拟环境）

1. 打开 Steam 版 **Slay the Spire**
2. 选 **观者 Watcher** → **开始新游戏**
3. 到 **Neow** 界面（或任意能 **Continue** 的位置）
4. **完全退出游戏**（不要后台挂着）
5. 进入仓库目录，双击：

```bat
run_watcher_pressure.bat
```

脚本会自动：

- 创建 `.venv` 虚拟环境
- 查找 `SlayTheSpire\saves\WATCHER.autosave`
- 备份原存档
- 把 4 张 Strike 改成点穴+
- 提示你重新打开游戏 Continue

### 手动命令（PowerShell / CMD）

```bat
cd C:\Users\30974\Downloads\0622-cursor-sts-unlock-all-83e0
py -3 -m venv .venv
.venv\Scripts\python.exe -m pip install -U pip
.venv\Scripts\python.exe start_watcher_pressure_run.py
```

Steam 不在默认路径时：

```bat
.venv\Scripts\python.exe start_watcher_pressure_run.py --game-root "D:\SteamLibrary\steamapps\common\SlayTheSpire"
```

或直接指定存档：

```bat
.venv\Scripts\python.exe start_watcher_pressure_run.py --save "C:\...\SlayTheSpire\saves\WATCHER.autosave"
```

预览不改文件：

```bat
.venv\Scripts\python.exe start_watcher_pressure_run.py --dry-run
```

### 观者起始卡组说明

| 卡牌 | 是否会被替换 |
| --- | --- |
| 4× Strike（Strike_P） | 是 → 点穴+ |
| 4× Defend | 否 |
| 1× Eruption | 否（除非加 `--replace-eruption`） |
| 1× Vigilance | 否 |

### 常见报错

| 报错 | 处理 |
| --- | --- |
| 找不到 WATCHER.autosave | 先在游戏里开一盘观者并退出 |
| 找不到 Steam 安装目录 | 加 `--game-root` |
| `python` 不是内部命令 | 安装 Python 3.10+ 并勾选 Add to PATH，或用 `py -3` |
| venv 创建失败 | 以管理员安装 Python，或运行 `py -3 -m pip install virtualenv` |

---

## iOS 全解锁（抓取 → 解锁 → 写回）

**结论先说清楚：**

1. 我这边的云环境**连不上你的 iPhone**，也不能替你装 iMazing。
2. 官方 STS 的解锁进度在**本地 `preferences`**，**不是网络回包**。HTTP/HTTPS 抓包改响应，跑不通解锁。
3. 这里的「抓包」按可落地流程实现为：**USB/备份抓取 App 容器 → 本地解锁 → 写回手机**。

本仓库提供一条不依赖 iMazing 的开源流程（`pymobiledevice3`）。

## 一键跑通（推荐先看 demo）

无需手机，先验证整条链路：

```bash
pip install -r requirements.txt
python3 sts_ios_pipeline.py run --mode demo
```

成功后，假设备里的解锁文件会变成满解锁：

`tests/fixtures/fake_ios_device/Documents/preferences/`

单元测试：

```bash
python3 -m unittest discover -s tests -v
```

## 真机流程（Windows / macOS）

### 0. 准备

- 安装 Python 3.10+
- iPhone 用数据线连接电脑
- 手机解锁，弹窗点 **信任此电脑**
- 安装依赖：

```bash
cd 本仓库
pip install -r requirements.txt
```

Windows 若 usbmux 异常，可再装 [iTunes](https://www.apple.com/itunes/)（只为驱动）。

### 1. 检查环境

```bash
python3 sts_ios_pipeline.py doctor
```

应能看到 USB 设备，并尽量识别到 Slay the Spire 的 Bundle ID（常见 `com.humble.SlayTheSpire`）。

### 2. 一键：抓取 → 全解锁 → 写回

```bash
python3 sts_ios_pipeline.py run --mode usb
```

若自动路径不对，可指定：

```bash
python3 sts_ios_pipeline.py run --mode usb \
  --bundle-id com.humble.SlayTheSpire \
  --remote-prefs preferences
```

写回后：**在 iPhone 上划掉游戏进程，再重新打开**。

### 3. 分步执行（排查用）

```bash
python3 sts_ios_pipeline.py capture --mode usb
python3 sts_ios_pipeline.py unlock
python3 sts_ios_pipeline.py restore --mode usb
```

工作目录默认 `work/`：

| 路径 | 含义 |
| --- | --- |
| `work/capture/` | 从手机抓到的原始容器/备份提取 |
| `work/unlocked_preferences/` | 解锁后的 preferences |
| `work/pipeline_meta.json` | Bundle ID / 远程路径等元数据 |

## USB 失败时：未加密备份模式

部分系统上 HouseArrest 会被拒绝，可改备份抓取：

```bash
# 自动尝试备份（或先用 Finder/iTunes 做「未加密」备份）
python3 sts_ios_pipeline.py capture --mode backup --backup-dir work/ios_backup
python3 sts_ios_pipeline.py unlock
python3 sts_ios_pipeline.py restore --mode usb
```

说明：`backup` 模式负责**取出**；写回仍走 USB `restore`。若 USB 写回也失败，把 `work/unlocked_preferences/` 用爱思助手等工具手动塞回 App 容器即可。

## 不想用命令行时

可用免费/常见国产工具代替 iMazing 做「导出/导入 App 数据」：

- 爱思助手
- 3uTools

导出后把 `preferences`（内含 `STSPlayer`）放到 `input/`，再：

```bash
python3 unlock_sts.py input -o output/unlocked_preferences
```

然后手动写回。

## 只解锁本地目录

```bash
python3 unlock_sts.py /path/to/preferences -o output/unlocked_preferences
```

## 会解锁什么

- 全部角色
- 卡牌 / 遗物解锁进度
- Ascension 20
- Act 4
- 每日挑战 / 自定义模式入口条件
- 图鉴（Seen cards / relics / bosses）

## 为什么不是「网络抓包改回包」

官方 STS 进度校验与解锁标记都在本地 JSON preferences，没有「请求服务器返回已解锁列表」这种可改链路。对官方客户端，改抓包回包无法稳定解锁；改本地 preferences 才是正确路径。

## 把真机文件交给 Cloud Agent

如果你希望我继续直接改你的真实存档：

1. 在你自己电脑上执行 `capture`（或爱思导出）
2. 把 `work/unlocked_preferences` 之前的原始 `preferences` 上传到仓库 `input/`
3. 告诉我一声

没有这些文件时，我只能把流程工具准备好，无法隔空改手机。
