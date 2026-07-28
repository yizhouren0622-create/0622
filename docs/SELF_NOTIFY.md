# Self-change Gmail notify

当你**自己**修改并 push `docs/` 时，也会收到通知。

## 默认（无需配置）

仓库已加 GitHub Action：`.github/workflows/docs-change-notify.yml`

1. 你改 `docs/` 并 push
2. Action 在固定 Issue `[notify] docs/ folder changes` 下留言
3. GitHub 把通知发到你账号绑定的邮箱（Gmail）

请确认：
- GitHub → Settings → Notifications → 打开 Email
- 关注本仓库，或至少开启 Participating / Issues 通知

## 可选：直接发到 Gmail（SMTP）

1. Google 账号开启两步验证
2. 生成 [应用专用密码](https://myaccount.google.com/apppasswords)（Mail）
3. 在仓库 **Settings → Secrets and variables → Actions** 添加：
   - `GMAIL_USER` = `yizhouren0622@gmail.com`
   - `GMAIL_APP_PASSWORD` = 应用专用密码
4. 之后每次 `docs/` 变动会额外发一封 SMTP 邮件

## 说明

- Cursor agent 自己的改动默认会通知；**你自己的 push 以前不会**
- 这个 Action 专门补上「自己改也通知」
- Action 只留言/发信，不改 `docs/`，不会死循环
