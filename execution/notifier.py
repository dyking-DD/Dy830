"""
通知模块 - Notification Module

支持多种通知方式：
- 飞书机器人消息
- 邮件通知（预留）
- 日志记录

【重要】飞书机器人需要设置关键词验证，所有消息标题必须包含"量化"
"""

import os
import json
import logging
import requests
from datetime import datetime
from typing import Optional, Dict

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class NotificationManager:
    """通知管理器"""
    
    # 飞书关键词（必须与机器人设置的关键词一致）
    FEISHU_KEYWORD = "量化"
    
    def __init__(self, webhook_url: str = None):
        """
        初始化通知管理器
        
        Args:
            webhook_url: 飞书机器人Webhook地址（可选，也可通过环境变量设置）
        """
        self.webhook_url = webhook_url or os.environ.get('FEISHU_WEBHOOK', '')
        self.enabled = bool(self.webhook_url)
        
        if self.enabled:
            logger.info(f"飞书通知已启用")
        else:
            logger.warning(f"飞书通知未启用（未配置webhook）")
    
    def _add_keyword(self, text: str) -> str:
        """确保文本包含飞书关键词"""
        if self.FEISHU_KEYWORD not in text:
            return f"{self.FEISHU_KEYWORD} {text}"
        return text
    
    def send_daily_report(self, report_text: str, date: Optional[datetime] = None):
        """
        发送每日报告
        
        Args:
            report_text: 报告文本
            date: 日期
        """
        if date is None:
            date = datetime.now()
        
        # 总是记录到日志
        logger.info(f"\n{'='*60}\n量化日报 - {date.strftime('%Y-%m-%d')}\n{'='*60}")
        logger.info(report_text)
        
        # 如果配置了飞书webhook，发送消息
        if self.enabled:
            # 格式化报告为飞书卡片
            card = self._format_daily_card(report_text, date)
            self._send_feishu_card(card)
    
    def _format_daily_card(self, report_text: str, date: datetime) -> Dict:
        """格式化日报为飞书卡片"""
        return {
            "msg_type": "interactive",
            "card": {
                "config": {"wide_screen_mode": True},
                "header": {
                    "title": {
                        "tag": "plain_text",
                        "content": self._add_keyword(f"📊 交易日报 - {date.strftime('%Y-%m-%d')}")
                    },
                    "template": "blue"
                },
                "elements": [
                    {
                        "tag": "div",
                        "text": {
                            "tag": "plain_text",
                            "content": report_text
                        }
                    }
                ]
            }
        }
    
    def send_trade_alert(self, symbol: str, action: str, quantity: int, price: float, reason: str = ""):
        """
        发送交易信号告警
        
        Args:
            symbol: 股票代码
            action: 操作（buy/sell）
            quantity: 数量
            price: 价格
            reason: 原因
        """
        emoji = "🟢" if action == "buy" else "🔴"
        action_text = "买入" if action == "buy" else "卖出"
        title = self._add_keyword(f"{emoji} {action_text} {symbol}")
        content = f"数量: {quantity}股 | 价格: ¥{price:.2f}"
        if reason:
            content += f"\n原因: {reason}"
        
        logger.info(f"[量化交易信号] {title} - {content}")
        
        if self.enabled:
            card = {
                "msg_type": "interactive",
                "card": {
                    "header": {
                        "title": {"tag": "plain_text", "content": title},
                        "template": "green" if action == "buy" else "red"
                    },
                    "elements": [
                        {
                            "tag": "div",
                            "text": {"tag": "plain_text", "content": content}
                        }
                    ]
                }
            }
            self._send_feishu_card(card)
    
    def send_risk_alert(self, title: str, content: str, level: str = "warning"):
        """
        发送风控告警
        
        Args:
            title: 标题
            content: 内容
            level: 级别 (warning/error)
        """
        emoji = "⚠️" if level == "warning" else "🚨"
        alert_msg = f"{emoji} {title}: {content}"
        
        if level == "error":
            logger.error(alert_msg)
        else:
            logger.warning(alert_msg)
        
        if self.enabled:
            card = {
                "msg_type": "interactive",
                "card": {
                    "header": {
                        "title": {"tag": "plain_text", "content": self._add_keyword(f"{emoji} 风控告警")},
                        "template": "red" if level == "error" else "orange"
                    },
                    "elements": [
                        {
                            "tag": "div",
                            "text": {"tag": "plain_text", "content": f"**{title}**\n{content}"}
                        }
                    ]
                }
            }
            self._send_feishu_card(card)
    
    def send_news_alert(self, symbol: str, stock_name: str, alert_type: str, title: str, content: str, keywords: list = None):
        """
        发送新闻监控警报
        
        Args:
            symbol: 股票代码
            stock_name: 股票名称
            alert_type: 警报类型 (sell/warning/info)
            title: 新闻标题
            content: 新闻内容
            keywords: 匹配到的关键词
        """
        colors = {
            'sell': 'red',
            'warning': 'orange',
            'info': 'blue'
        }
        
        icons = {
            'sell': '🚨',
            'warning': '⚠️',
            'info': 'ℹ️'
        }
        
        action_map = {
            'sell': '卖出警报',
            'warning': '风险警告',
            'info': '信息提醒'
        }
        
        header_title = self._add_keyword(f"{icons.get(alert_type, '🔔')} {action_map.get(alert_type, '提醒')} - {stock_name} ({symbol})")
        
        keyword_text = f"关键词: {', '.join(keywords[:5])}" if keywords else ""
        
        card = {
            "msg_type": "interactive",
            "card": {
                "config": {"wide_screen_mode": True},
                "header": {
                    "title": {
                        "tag": "plain_text",
                        "content": header_title
                    },
                    "template": colors.get(alert_type, 'blue')
                },
                "elements": [
                    {
                        "tag": "div",
                        "text": {
                            "tag": "lark_md",
                            "content": f"**{title}**\n\n{content[:200]}..."
                        }
                    },
                    {
                        "tag": "div",
                        "text": {
                            "tag": "lark_md",
                            "content": keyword_text
                        }
                    }
                ]
            }
        }
        
        self._send_feishu_card(card)
        logger.info(f"[量化新闻警报] {stock_name}: {title[:50]}...")
    
    def _send_feishu_card(self, card: Dict):
        """
        发送飞书卡片消息
        
        Args:
            card: 飞书卡片数据
        """
        if not self.webhook_url:
            logger.warning("未配置飞书webhook，跳过发送")
            return
        
        try:
            response = requests.post(
                self.webhook_url,
                json=card,
                headers={"Content-Type": "application/json"},
                timeout=10
            )
            response.raise_for_status()
            result = response.json()
            
            if result.get("code") == 0:
                logger.info("飞书消息发送成功")
            else:
                logger.error(f"飞书消息发送失败: {result.get('msg')}")
        
        except requests.exceptions.RequestException as e:
            logger.error(f"发送飞书消息失败: {e}")
    
    def send_alert(self, title: str, content: str, level: str = "info"):
        """
        发送告警（兼容旧接口）
        
        Args:
            title: 标题
            content: 内容
            level: 级别 (info/warning/error)
        """
        if level in ["warning", "error"]:
            self.send_risk_alert(title, content, level)
        else:
            logger.info(f"[{title}] {content}")


if __name__ == "__main__":
    # 测试通知模块
    import sys
    
    # 从环境变量或命令行参数获取webhook
    webhook = os.environ.get('FEISHU_WEBHOOK', '')
    if len(sys.argv) > 1:
        webhook = sys.argv[1]
    
    notifier = NotificationManager(webhook_url=webhook)
    
    # 测试报告
    test_report = """【量化测试报告】
初始资金: 100,000.00
当前现金: 90,020.55
总资产: 100,000.00
累计盈亏: 0.00 (+0.00%)
持仓数量: 1 只
现金比例: 90.0%

【持仓明细】
688710.SH: 151股 @ 66.06

【今日成交】
BUY 688710.SH 151股 @ 66.06
"""
    
    print("发送测试日报...")
    notifier.send_daily_report(test_report)
    
    print("\n发送交易信号测试...")
    notifier.send_trade_alert("000001.SZ", "buy", 1000, 10.5, "MA金叉")
    
    print("\n发送风控告警测试...")
    notifier.send_risk_alert("熔断触发", "日内回撤超过5%，已暂停交易", "warning")
    
    print("\n发送新闻警报测试...")
    notifier.send_news_alert(
        "688021.SH", "奥福科技", "sell",
        "公司收到监管问询函", 
        "监管机构对公司财务数据提出质疑，要求说明营收增长原因...",
        ["监管", "问询函"]
    )
    
    print("\n测试完成！")
