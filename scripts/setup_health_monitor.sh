#!/bin/bash
# 设置每日系统监测定时任务

echo "🦞 设置量化系统每日健康检查..."

PROJECT_DIR="/home/gem/workspace/agent/workspace/daily_stock_analysis"
PYTHON="python3"

# 健康检查脚本路径
HEALTH_SCRIPT="$PROJECT_DIR/scripts/health_check.py"

# 创建日志目录
mkdir -p "$PROJECT_DIR/logs/health"

# 设置每小时检查（9:00, 12:00, 15:00, 18:00）
# 同时每天早上9点发送日报
CRON_ENTRIES="
# 量化系统健康检查 - 每小时一次（工作时间）
0 9,12,15,18 * * * cd $PROJECT_DIR && $PYTHON $HEALTH_SCRIPT >> $PROJECT_DIR/logs/health/health_\$(date +\%Y\%m\%d).log 2>&1

# 量化系统每日健康报告 - 每天早上9点
0 9 * * * cd $PROJECT_DIR && $PYTHON $HEALTH_SCRIPT --daily-report >> $PROJECT_DIR/logs/health/daily_report_\$(date +\%Y\%m\%d).log 2>&1
"

# 先备份当前crontab
crontab -l > /tmp/crontab_backup_$(date +%Y%m%d_%H%M%S).txt 2>/dev/null

# 检查是否已存在健康检查任务
if crontab -l 2>/dev/null | grep -q "health_check.py"; then
    echo "⚠️ 健康检查任务已存在，跳过添加"
else
    # 添加新任务
    (crontab -l 2>/dev/null; echo "$CRON_ENTRIES") | crontab -
    echo "✅ 健康检查定时任务已添加"
fi

# 显示当前crontab
echo ""
echo "当前定时任务:"
echo "-------------------"
crontab -l | grep -E "(health_check|daily_scanner|news_monitor)" || echo "暂无相关任务"
echo "-------------------"

# 测试运行一次
echo ""
echo "🧪 运行一次健康检查测试..."
cd "$PROJECT_DIR" && $PYTHON "$HEALTH_SCRIPT"

echo ""
echo "✅ 设置完成！"
echo ""
echo "📋 检查计划:"
echo "  • 每工作日 9:00, 12:00, 15:00, 18:00 - 系统健康检查"
echo "  • 每天早上 9:00 - 完整健康报告"
echo "  • 日志保存: logs/health/"
echo ""
echo "🚨 如果发现问题，会立即发送飞书告警"
