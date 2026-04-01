#!/bin/bash
# Mac模拟交易盘 - 双击启动
cd ~/daily_stock_analysis 2>/dev/null || cd ~/workspace/agent/workspace/daily_stock_analysis 2>/dev/null || cd "$(dirname "$0")"
python3 trading_desk.py
