# 飞书通知配置指南

## 快速开始

### 1. 创建飞书机器人

1. 打开飞书，进入你想接收通知的群聊
2. 点击右上角 **···** → **设置** → **群机器人**
3. 点击 **添加机器人** → 选择 **自定义机器人**
4. 给机器人起名字（如：量化交易助手）
5. 复制 **Webhook地址**（格式：`https://open.feishu.cn/open-apis/bot/v2/hook/xxxxxxxx`）

### 2. 配置Webhook

**方式一：交互式配置（推荐）**

```bash
cd daily_stock_analysis
bash scripts/setup_feishu.sh
```

按提示粘贴Webhook地址，可立即测试。

**方式二：环境变量**

```bash
export FEISHU_WEBHOOK="https://open.feishu.cn/open-apis/bot/v2/hook/xxxxxxxx"
```

添加到 `~/.bashrc` 可永久生效。

**方式三：命令行参数**

```bash
python3 scripts/daily_scanner.py --webhook "https://open.feishu.cn/..."
```

### 3. 测试通知

```bash
# 使用环境变量中的配置
python3 scripts/test_notification.py

# 或使用命令行指定
python3 scripts/test_notification.py --webhook "https://..."
```

成功后会收到3条测试消息：
- 🟢 交易信号通知
- ⚠️ 风控告警通知  
- 📊 每日报告

---

## 通知类型

### 1. 交易信号通知

**触发时机**：执行买入/卖出操作时

**消息格式**：
```
🟢 BUY 000001.SZ
数量: 1000股 | 价格: ¥10.50
原因: MA5上穿MA20金叉
```

### 2. 风控告警通知

**触发时机**：
- 风控拦截交易
- 熔断机制触发
- 系统异常

**消息格式**：
```
⚠️ 风控告警
熔断触发：日内回撤超过5%，已暂停交易
```

### 3. 每日报告

**触发时机**：每日扫描完成后

**消息格式**：
```
📊 量化交易日报 - 2026-03-29

【账户概览】
初始资金: 100,000.00
当前现金: 90,020.55
总资产: 100,000.00
累计盈亏: 0.00 (+0.00%)
...
```

---

## 定时任务配置

### Linux/macOS (crontab)

```bash
# 编辑定时任务
crontab -e

# 添加：工作日收盘后自动运行并发送通知（16:00）
0 16 * * 1-5 cd /path/to/daily_stock_analysis && /bin/bash scripts/daily_run.sh

# 或带飞书通知（需先配置环境变量）
0 16 * * 1-5 cd /path/to/daily_stock_analysis && source .env && python3 scripts/daily_scanner.py
```

### Windows (任务计划程序)

1. 创建批处理文件 `daily_run.bat`：
```batch
@echo off
cd /d C:\path\to\daily_stock_analysis
set FEISHU_WEBHOOK=https://open.feishu.cn/open-apis/bot/v2/hook/xxxxxxxx
python3 scripts\daily_scanner.py
```

2. 打开「任务计划程序」→ 创建基本任务
3. 触发器：每天 16:00，仅工作日
4. 操作：启动程序，选择 `daily_run.bat`

---

## 常见问题

### Q: 测试消息发送失败？

**检查清单**：
1. Webhook地址是否完整复制（包含 `https://`）
2. 机器人是否被移出群聊
3. 网络是否可以访问 `open.feishu.cn`

**调试命令**：
```bash
curl -X POST -H "Content-Type: application/json" \
  -d '{"msg_type":"text","content":{"text":"测试"}}' \
  https://open.feishu.cn/open-apis/bot/v2/hook/xxxxxxxx
```

### Q: 如何关闭通知？

1. 临时关闭：不设置 `FEISHU_WEBHOOK` 环境变量
2. 永久关闭：删除 `.env` 文件中的配置
3. 保留日志：通知失败时会自动记录到 `logs/` 目录

### Q: 可以发送到多个群吗？

目前不支持单个机器人发送到多个群。如需多群通知：
1. 在每个群分别创建机器人
2. 在脚本中配置多个 webhook
3. 或使用飞书「消息转发」功能

---

## 安全提示

⚠️ **Webhook地址是私密凭证，请妥善保管**：
- 不要提交到Git仓库
- 不要分享给他人
- 如泄露，在飞书中删除机器人重新创建

`.env` 文件已添加到 `.gitignore`，不会被提交。
