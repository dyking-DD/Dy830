# 每日量化扫描 - 定时任务配置

## 定时任务设置

已配置定时任务 `daily_quant_scan`，工作日（周一到周五）15:30 自动执行。

### 任务详情
- **名称**: daily_quant_scan
- **执行时间**: 每天 15:30 ( Asia/Shanghai )
- **执行频率**: 周一至周五（工作日）
- **命令**: `python3 scripts/daily_scan.py --mode paper`
- **ID**: a8d6eb2e-26e0-4643-9ebf-678d8149c76d

## 手动执行

```bash
cd /home/gem/workspace/agent/workspace/daily_stock_analysis
python3 scripts/daily_scan.py --mode paper
```

## 参数说明

| 参数 | 说明 | 默认值 |
|------|------|--------|
| --mode | 运行模式 (paper/live) | paper |
| --no-notify | 不发送飞书通知 | False |
| --stocks | 指定扫描的股票列表 | 沪深300前50 |

## 扫描流程

1. **获取市场择时** - 判断市场整体趋势
2. **扫描股票池** - 沪深300成分股前50只
3. **多策略投票** - 5个策略投票生成信号
4. **信号过滤** - 根据市场状态过滤
5. **生成报告** - 格式化Top信号
6. **飞书推送** - 发送扫描结果
7. **保存记录** - 报告保存到 reports/ 目录

## 策略配置

当前组合权重：
- MACD: 25%
- RSI: 20%
- 布林带: 20%
- 多因子共振: 20%
- 动量突破: 15%

信号阈值: 0.5 (半数以上策略同意)
最大持仓: 10只

## 报告内容

- 扫描日期
- 市场状态（趋势/允许做多）
- 扫描股票数
- 生成信号数
- Top 10 信号详情
- 各策略投票情况

## 查看定时任务状态

```bash
openclaw cron list
```

## 管理定时任务

```bash
# 查看任务列表
openclaw cron list

# 立即运行一次
openclaw cron run daily_quant_scan

# 暂停任务
openclaw cron update daily_quant_scan --enabled=false

# 恢复任务
openclaw cron update daily_quant_scan --enabled=true

# 删除任务
openclaw cron remove daily_quant_scan
```
