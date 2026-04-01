# 实盘交易测试指南

## 概述

本文档指导如何安全地进行实盘交易测试，确保系统在实际资金操作前经过充分验证。

## 测试前准备

### 1. 环境检查

- [ ] 已安装 Choice 金融终端（策略版）
- [ ] Choice 终端已登录并保持运行
- [ ] 已申请量化交易权限（联系客服 95357）
- [ ] 账户资金充足（建议 ≥ 30万）
- [ ] Python 环境已安装依赖

### 2. 配置检查

```bash
# 检查 .env 文件
cat .env

# 确保包含
FEISHU_WEBHOOK=https://open.feishu.cn/open-apis/bot/v2/hook/xxx
```

## 测试流程

### 阶段一：模拟交易测试（必须）

```bash
cd daily_stock_analysis
python scripts/test_live_trading.py --mode paper
```

**预期输出：**
```
============================================================
模拟交易测试
============================================================
>>> 执行测试: 连接测试
✅ 连接成功

>>> 执行测试: 账户查询测试
✅ 通过: 账户查询测试
...

测试结果汇总:
  ✅ 连接测试
  ✅ 账户查询测试
  ✅ 持仓查询测试
  ...

通过: 10/10
```

### 阶段二：Choice 终端连接测试

```bash
python scripts/test_live_trading.py --mode choice
```

**预期输出：**
```
============================================================
Choice 终端测试
============================================================
✅ 连接成功

账户信息:
  总资产: 350,000.00
  可用资金: 120,000.00

持仓: 3 只股票

平安银行行情:
  最新价: 10.25
  涨跌: 0.15

✅ Choice 测试完成
```

### 阶段三：小额实盘测试

**⚠️ 重要：此阶段涉及真实资金！**

#### 3.1 手动下单测试

在 Choice 终端中：
1. 选择低价股（如银行股，股价 < 20元）
2. 买入 **1手（100股）**
3. 观察成交回报
4. 检查持仓是否正确更新
5. 卖出这1手

#### 3.2 API下单测试

```python
# 在 Python 中测试
from execution.dongcai_choice import ChoiceTrader

trader = ChoiceTrader()
if trader.connect():
    # 以极低价格买入1手（确保不成交）
    order_id = trader.submit_order(
        symbol='000001.SZ',
        action='buy',
        quantity=100,
        price=1.0,  # 低于市价，确保不成交
        order_type='limit'
    )
    
    if order_id:
        print(f"订单提交成功: {order_id}")
        
        # 立即撤单
        trader.cancel_order(order_id)
    
    trader.disconnect()
```

### 阶段四：策略实盘测试

```bash
# 开启实时策略监控
python scripts/live_strategy_runner.py --mode live --test-amount 1000
```

此模式会：
- 生成交易信号
- 发送飞书通知
- 但不自动下单（需手动确认）

## 风险控制

### 测试期间限制

| 限制项 | 数值 | 说明 |
|--------|------|------|
| 单票测试金额 | ≤ 1000元 | 首次测试 |
| 单票最大仓位 | ≤ 20% | 正常交易 |
| 单日最大亏损 | ≤ 3% | 日止损线 |
| 单票止损线 | -5% | 硬止损 |
| 连续亏损天数 | ≤ 3天 | 暂停交易 |

### 紧急处理

如果测试出现问题：

1. **立即断开连接**
   ```python
   trader.disconnect()
   ```

2. **手动平仓**
   在 Choice 终端中手动卖出所有持仓

3. **检查日志**
   ```bash
   tail -f logs/live_trading.log
   ```

4. **联系客服**
   - 东方财富：95357
   - 技术问题：查看 Choice 终端日志

## 常见问题

### Q: 连接失败 "未找到 EmQuantAPI"

**原因：** 未安装 Choice 终端

**解决：**
1. 下载安装 Choice 金融终端（策略版）
2. 确保终端已登录
3. 重启 Python 环境

### Q: "未开通量化权限"

**原因：** 账户未开通量化交易

**解决：**
1. 拨打 95357 联系客服
2. 申请"量化交易权限"
3. 签署相关协议（1-3个工作日）

### Q: 订单提交成功但未成交

**正常情况：**
- 限价单价格偏离市价太远
- 市场流动性不足
- 不在交易时间

**检查：**
```python
# 查询订单状态
status = trader.get_order_status(order_id)
print(status)
```

### Q: 持仓显示不正确

**原因：** 数据同步延迟

**解决：**
```python
# 强制刷新
import time
time.sleep(2)  # 等待2秒
positions = trader.get_positions()
```

## 生产环境部署

### 1. 配置文件

```yaml
# config/trading.yaml
live_trading:
  enabled: true
  broker: dongcai_choice  # 或 dongcai_juejin
  
  # 风控参数
  risk_limits:
    max_position_pct: 0.20      # 单票最大20%
    max_daily_loss_pct: 0.03    # 日最大亏损3%
    max_drawdown_pct: 0.15      # 最大回撤15%
    
  # 交易参数
  trading:
    default_quantity: 1000      # 默认买入数量
    use_limit_order: true       # 使用限价单
    limit_price_offset: 0.005   # 限价单偏移0.5%
```

### 2. 启动实盘交易

```bash
# 方式1：直接启动
python scripts/live_trading_daemon.py

# 方式2：使用nohup后台运行
nohup python scripts/live_trading_daemon.py > logs/live_trading.log 2>&1 &

# 方式3：使用systemd服务（推荐）
sudo systemctl start stock-trading
```

### 3. 监控

```bash
# 查看实时日志
tail -f logs/live_trading.log

# 查看持仓
python scripts/show_positions.py

# 查看当日订单
python scripts/show_orders.py --today
```

## 附录

### 相关脚本

| 脚本 | 用途 |
|------|------|
| `test_live_trading.py` | 完整测试套件 |
| `live_trading_daemon.py` | 实盘交易守护进程 |
| `show_positions.py` | 显示当前持仓 |
| `show_orders.py` | 显示订单历史 |
| `emergency_sell_all.py` | 紧急平仓 |

### 联系支持

- **东方财富客服**：95357
- **掘金量化**：https://www.myquant.cn/
- **Choice 终端**：http://choice.eastmoney.com/

---

⚠️ **风险提示**：实盘交易涉及真实资金损失风险，请确保充分理解风险后再进行操作。