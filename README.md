# Slay the Spire iOS 全解锁（抓取 → 解锁 → 写回）

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
