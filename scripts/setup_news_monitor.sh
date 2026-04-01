#!/bin/bash
# 配置24小时新闻监控定时任务

echo "========================================"
echo "配置24小时新闻监控"
echo "========================================"
echo ""

PROJECT_DIR="/home/gem/workspace/agent/workspace/daily_stock_analysis"

echo "选择监控频率："
echo "1) 每小时检查一次（24小时不间断）"
echo "2) 每2小时检查一次（推荐）"
echo "3) 每4小时检查一次"
echo "4) 仅交易时间（工作日 9:00-15:00，每小时）"
echo ""
read -p "请选择 [1-4]: " choice

case $choice in
    1)
        CRON_EXPR="0 * * * *"
        DESC="每小时检查"
        ;;
    2)
        CRON_EXPR="0 */2 * * *"
        DESC="每2小时检查"
        ;;
    3)
        CRON_EXPR="0 */4 * * *"
        DESC="每4小时检查"
        ;;
    4)
        CRON_EXPR="0 9-15 * * 1-5"
        DESC="交易时间每小时检查"
        ;;
    *)
        echo "无效选择，退出"
        exit 1
        ;;
esac

echo ""
echo "配置预览:"
echo "  频率: $DESC"
echo "  命令: $CRON_EXPR cd $PROJECT_DIR && source .env && /usr/bin/python3 scripts/news_monitor.py --watchlist"
echo ""

read -p "确认添加? (y/n): " confirm

if [ "$confirm" = "y" ] || [ "$confirm" = "Y" ]; then
    # 获取当前crontab
    crontab -l > /tmp/cron_temp 2>/dev/null || touch /tmp/cron_temp
    
    # 删除旧的新闻监控任务
    grep -v "news_monitor" /tmp/cron_temp > /tmp/cron_temp2 || touch /tmp/cron_temp2
    
    # 添加新任务
    echo "$CRON_EXPR cd $PROJECT_DIR && source .env && /usr/bin/python3 scripts/news_monitor.py --watchlist >> logs/news_monitor.log 2>&1" >> /tmp/cron_temp2
    
    # 安装新crontab
    crontab /tmp/cron_temp2
    rm -f /tmp/cron_temp /tmp/cron_temp2
    
    echo ""
    echo "✅ 新闻监控定时任务已添加！"
    echo ""
    echo "当前所有定时任务:"
    crontab -l
else
    echo "已取消"
fi

echo ""
echo "========================================"
echo "手动运行测试"
echo "========================================"
echo "cd $PROJECT_DIR && python3 scripts/news_monitor.py --watchlist"
echo ""
