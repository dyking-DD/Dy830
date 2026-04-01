## 📋 量化系统操作手册

### 1. 每日运行（手动）

```bash
cd daily_stock_analysis

# 方式A: 全量扫描（约5500只，10-15分钟）
python3 scripts/daily_scanner.py

# 方式B: 快速测试（10只，30秒）
python3 scripts/daily_scanner.py --limit 10
```

### 2. 配置飞书通知（推荐）

```bash
# 交互式配置（按提示操作）
bash scripts/setup_feishu.sh

# 测试通知是否生效
python3 scripts/test_notification.py
```

**配置完成后，你将收到：**
- 🟢 实时交易信号（买入/卖出）
- ⚠️ 风控告警（熔断、拦截等）
- 📊 每日收盘报告（账户概览、持仓、成交）

详细配置说明见：`docs/FEISHU_SETUP.md`

### 3. 定时自动运行（Cron）

```bash
# 编辑定时任务
crontab -e

# 添加：工作日收盘后自动运行并发送通知（16:00）
0 16 * * 1-5 cd /home/gem/workspace/agent/workspace/daily_stock_analysis && source .env && python3 scripts/daily_scanner.py
```

### 4. 查看结果

```bash
# 查看最新报告
cat logs/daily_report_$(date +%Y%m%d).txt

# 查看历史日志
ls -la logs/

# 查看持仓状态
cat data/paper_trading_state.json
```

### 5. 系统文件结构

```
daily_stock_analysis/
├── data/              # 股票数据缓存、模拟账户状态
├── logs/              # 每日报告和日志
├── config/            # 风控配置、黑名单
├── execution/         # 模拟交易引擎 + 通知模块
├── risk/              # 风控模块
├── strategies/        # 策略文件
├── scripts/           # 运行脚本
└── docs/              # 文档
```

### 6. 关键配置

**风控配置**: `config/risk_config.yaml`
- 单票仓位: 10%
- 日内熔断: 5%回撤
- 交易间隔: 60秒

**黑名单**: `config/blacklist.txt`
- 自动更新ST股票（178只）
- 可手动添加禁止交易的股票

**飞书通知**: `.env` (由 setup_feishu.sh 创建)
- Webhook地址
- 自动加载到环境变量

---

## 常用命令速查

| 命令 | 说明 |
|------|------|
| `python3 scripts/daily_scanner.py` | 全量扫描 |
| `python3 scripts/daily_scanner.py --limit 10` | 快速测试（10只）|
| `python3 scripts/daily_scanner.py --webhook URL` | 指定webhook运行 |
| `python3 scripts/test_notification.py` | 测试通知 |
| `bash scripts/setup_feishu.sh` | 配置飞书机器人 |
| `python3 scripts/run_backtest.py` | 运行回测 |
| `cat logs/daily_report_*.txt` | 查看报告 |

---

## 下一步选择

**A. 实盘接口（Phase 5）**
- 接入券商API（QMT/Ptrade）
- 需要开通量化交易权限
- 风险: 真实资金交易

**B. 策略优化**
- 新增技术指标策略
- 参数回测优化
- 多因子模型

**C. 监控告警增强**
- 异常波动实时监控
- 大盘风险预警
- 持仓盈亏告警

需要我帮你配置哪一项？