#!/bin/bash
# 每日量化交易定时任务
# 建议添加到 crontab: 0 16 * * 1-5 /bin/bash /path/to/daily_run.sh

cd /home/gem/workspace/agent/workspace/daily_stock_analysis

# 设置环境
export PYTHONPATH=/home/gem/workspace/agent/workspace/daily_stock_analysis:$PYTHONPATH

# 记录日志
LOG_FILE="logs/cron_$(date +%Y%m%d_%H%M%S).log"

echo "========================================" >> $LOG_FILE
echo "开始执行: $(date)" >> $LOG_FILE
echo "========================================" >> $LOG_FILE

# 运行每日扫描
python3 scripts/daily_scanner.py >> $LOG_FILE 2>&1

echo "执行完成: $(date)" >> $LOG_FILE
echo "" >> $LOG_FILE

# 可选：发送飞书通知（需配置 webhook）
# curl -X POST -H "Content-Type: application/json" \
#   -d "{\"msg_type\":\"text\",\"content\":{\"text\":\"量化交易日报已生成\"}}" \
#   $FEISHU_WEBHOOK_URL
