#!/bin/bash
# 配置每日定时任务 - Configure Daily Cron Job
# 工作日收盘后自动运行扫描并发送飞书通知

echo "========================================"
echo "配置定时任务 (Cron Job)"
echo "========================================"
echo ""

PROJECT_DIR="/home/gem/workspace/agent/workspace/daily_stock_analysis"
CRON_FILE="/tmp/cron_temp_$$"

# 检查当前crontab
crontab -l > "$CRON_FILE" 2>/dev/null || touch "$CRON_FILE"

echo "当前定时任务："
echo "----------------------------------------"
grep -E "daily_scanner|daily_stock_analysis" "$CRON_FILE" || echo "（无相关任务）"
echo "----------------------------------------"
echo ""

echo "选择扫描模式："
echo "1) 全市场扫描 (约5500只，15-20分钟)"
echo "2) 创业板+科创板 (约1000只，5分钟)"
echo "3) 自选股票池 (config/watchlist.txt)"
echo "4) 自定义参数"
echo ""
read -p "请选择 [1-4]: " choice

case $choice in
    1)
        SCAN_ARGS="--limit 5500"
        SCAN_DESC="全市场扫描"
        ;;
    2)
        SCAN_ARGS="--cyb-kcb --limit 1500"
        SCAN_DESC="创业板+科创板"
        ;;
    3)
        SCAN_ARGS="--watchlist"
        SCAN_DESC="自选股票池"
        ;;
    4)
        echo ""
        read -p "输入扫描参数 (如: --sector cyb --limit 500): " SCAN_ARGS
        SCAN_DESC="自定义: $SCAN_ARGS"
        ;;
    *)
        echo "无效选择，退出"
        rm -f "$CRON_FILE"
        exit 1
        ;;
esac

echo ""
echo "选择运行时间（A股收盘时间 15:00）："
echo "1) 15:30 (收盘后30分钟，数据已更新)"
echo "2) 16:00 (收盘后1小时，数据稳定)"
echo "3) 20:00 (晚上，避开交易高峰)"
echo "4) 自定义时间"
echo ""
read -p "请选择 [1-4]: " time_choice

case $time_choice in
    1) RUN_TIME="30 15" ;;
    2) RUN_TIME="0 16" ;;
    3) RUN_TIME="0 20" ;;
    4)
        read -p "输入分钟 (0-59): " minute
        read -p "输入小时 (0-23): " hour
        RUN_TIME="$minute $hour"
        ;;
    *)
        echo "无效选择，退出"
        rm -f "$CRON_FILE"
        exit 1
        ;;
esac

echo ""
echo "========================================"
echo "配置预览"
echo "========================================"
echo "扫描模式: $SCAN_DESC"
echo "运行时间: 每天 $RUN_TIME (分钟 小时)"
echo "工作日: 周一到周五 (1-5)"
echo "项目目录: $PROJECT_DIR"
echo ""

read -p "确认添加此定时任务? (y/n): " confirm

if [ "$confirm" = "y" ] || [ "$confirm" = "Y" ]; then
    # 删除旧的任务
    grep -v "daily_scanner" "$CRON_FILE" > "$CRON_FILE.tmp" || true
    mv "$CRON_FILE.tmp" "$CRON_FILE"
    
    # 添加新任务
    # 格式: 分钟 小时 * * 星期 命令
    # 1-5 表示周一到周五
    echo "$RUN_TIME * * 1-5 cd $PROJECT_DIR && source .env && /usr/bin/python3 scripts/daily_scanner.py $SCAN_ARGS >> logs/cron.log 2>&1" >> "$CRON_FILE"
    
    # 安装新crontab
    crontab "$CRON_FILE"
    
    echo ""
    echo "✅ 定时任务已添加！"
    echo ""
    echo "查看所有定时任务："
    crontab -l | grep daily_scanner
    echo ""
    echo "手动测试运行："
    echo "  cd $PROJECT_DIR && source .env && python3 scripts/daily_scanner.py $SCAN_ARGS"
else
    echo "已取消"
fi

rm -f "$CRON_FILE"

echo ""
echo "========================================"
echo "提示"
echo "========================================"
echo "- 日志文件: $PROJECT_DIR/logs/cron.log"
echo "- 每日报告: $PROJECT_DIR/logs/daily_report_YYYYMMDD.txt"
echo "- 查看任务: crontab -l"
echo "- 删除任务: crontab -e (删除对应行)"
echo ""
