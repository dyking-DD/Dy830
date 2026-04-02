# -*- coding: utf-8 -*-
"""
钉钉机器人通知模块
接入方式：将 webhook_url 配置到 DingTalkNotifier 即可使用
"""

import json
import time
import hashlib
import hmac
import base64
import urllib.parse
import urllib.request
from typing import Optional, Dict, List


class DingTalkNotifier:
    """
    钉钉自定义机器人通知

    使用方法：
    1. 在钉钉群 → 群设置 → 智能群助手 → 添加机器人 → 自定义
    2. 选择"加签"安全设置，复制 secret
    3. 获取 webhook URL
    4. 填入下面配置
    """

    def __init__(self, webhook_url: str, secret: str = None):
        """
        :param webhook_url:  机器人 Webhook 地址
        :param secret:        加签密钥（可选，有则更安全）
        """
        self.webhook_url = webhook_url
        self.secret = secret

    def _get_sign(self) -> str:
        """计算签名（钉钉加签算法）"""
        if not self.secret:
            return ""

        timestamp = str(round(time.time() * 1000))
        string_to_sign = f"{timestamp}\n{self.secret}"
        hmac_obj = hmac.new(
            self.secret.encode("utf-8"),
            string_to_sign.encode("utf-8"),
            hashlib.sha256
        )
        sign = base64.b64encode(hmac_obj.digest()).decode("utf-8")
        return urllib.parse.quote(sign)

    def _build_url(self) -> str:
        """构建带签名的完整URL"""
        if not self.secret:
            return self.webhook_url

        sign = self._get_sign()
        timestamp = str(round(time.time() * 1000))
        return f"{self.webhook_url}&timestamp={timestamp}&sign={sign}"

    def send_text(self, content: str, at_phones: List[str] = None, is_at_all: bool = False) -> Dict:
        """
        发送文本消息

        :param content:      消息内容（最长2048字符）
        :param at_phones:    @指定人的手机号列表
        :param is_at_all:    是否 @所有人
        """
        payload = {
            "msgtype": "text",
            "text": {"content": content},
            "at": {
                "atMobiles": at_phones or [],
                "isAtAll": is_at_all
            }
        }
        return self._post(payload)

    def send_markdown(
        self,
        title: str,
        content: str,
        at_phones: List[str] = None,
        is_at_all: bool = False
    ) -> Dict:
        """
        发送 Markdown 消息（支持富文本）

        :param title:    首屏会话透出标题
        :param content:  Markdown 格式内容
                        支持的语法：
                        - # 一级标题
                        - ## 二级标题
                        - **bold**
                        - - 无序列表
                        - 1. 有序列表
                        - `code` 代码块
                        - [链接](http://xxx)
        """
        payload = {
            "msgtype": "markdown",
            "markdown": {
                "title": title,
                "text": content
            },
            "at": {
                "atMobiles": at_phones or [],
                "isAtAll": is_at_all
            }
        }
        return self._post(payload)

    def send_link(
        self,
        title: str,
        text: str,
        message_url: str,
        pic_url: str = ""
    ) -> Dict:
        """发送链接消息"""
        payload = {
            "msgtype": "link",
            "link": {
                "title": title,
                "text": text,
                "messageUrl": message_url,
                "picUrl": pic_url
            }
        }
        return self._post(payload)

    def send_action_card(
        self,
        title: str,
        content: str,
        single_title: str,
        single_url: str,
        btn_orientation: str = "0"
    ) -> Dict:
        """
        发送 ActionCard 消息（卡片消息）

        :param single_title:    按钮名称
        :param single_url:       点击按钮跳转的链接
        :param btn_orientation: 按钮排列方式（0竖直/1横向）
        """
        payload = {
            "msgtype": "actionCard",
            "actionCard": {
                "title": title,
                "text": content,
                "singleTitle": single_title,
                "singleURL": single_url,
                "btnOrientation": btn_orientation
            }
        }
        return self._post(payload)

    def _post(self, payload: Dict) -> Dict:
        """发送POST请求到钉钉"""
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            self._build_url(),
            data=data,
            headers={"Content-Type": "application/json"}
        )

        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                result = json.loads(resp.read().decode("utf-8"))
                if result.get("errcode") == 0:
                    return {"success": True, "message": "发送成功", "data": result}
                else:
                    return {"success": False, "message": f"钉钉返回错误: {result.get('errmsg')}", "data": result}
        except Exception as e:
            return {"success": False, "message": f"请求失败: {str(e)}", "data": None}


# =============================================================================
# 业务场景通知模板（直接调用即可发送）
# =============================================================================

def send_order_notification(
    webhook_url: str,
    secret: str,
    order_id: str,
    customer_name: str,
    stage: str,
    remark: str = ""
) -> Dict:
    """订单阶段变更通知（Markdown格式）"""
    notifier = DingTalkNotifier(webhook_url, secret)

    emoji_map = {
        "已接单": "📥",
        "垫资预审": "💰",
        "垫资审批中": "⏳",
        "垫资通过": "✅",
        "垫资已出账": "💸",
        "银行审批中": "🏦",
        "审批通过": "🎉",
        "放款通知": "📢",
        "待提车": "🚗",
        "已提车": "🎊",
        "GPS安装中": "🛰️",
        "GPS已在线": "✅",
        "资料归档中": "📋",
        "归档完成": "✅",
        "抵押登记中": "📝",
        "已抵押": "🔒",
        "正常还款中": "💳",
        "逾期": "🚨",
        "已结清": "🏆",
        "已完结": "🎊",
    }
    emoji = emoji_map.get(stage, "📌")

    content = f"""### 订单进度更新 {emoji}

**订单号：** `{order_id}`

**客户姓名：** {customer_name}

**当前阶段：** {stage}

**时间：** {time.strftime('%Y-%m-%d %H:%M:%S')}

{"**备注：** " + remark if remark else ""}
"""

    return notifier.send_markdown(
        title=f"📢 订单 {order_id} 进度更新",
        content=content
    )


def send_overdue_alert(
    webhook_url: str,
    secret: str,
    order_id: str,
    customer_name: str,
    phone: str,
    overdue_days: int,
    overdue_amount: float
) -> Dict:
    """逾期告警通知（红色醒目卡片）"""
    notifier = DingTalkNotifier(webhook_url, secret)

    content = f"""### 🚨 垫资逾期告警

**订单号：** `{order_id}`

**客户姓名：** {customer_name}

**联系电话：** {phone}

**逾期天数：** {overdue_days} 天

**逾期金额：** ¥{overdue_amount:,.2f}

**处理建议：** 请立即联系客户处理！

"""

    return notifier.send_markdown(
        title=f"🚨 逾期告警：{customer_name} 逾期{overdue_days}天",
        content=content
    )


def send_gps_alert(
    webhook_url: str,
    secret: str,
    device_id: str,
    imei: str,
    alert_type: str,
    location: str = "未知"
) -> Dict:
    """GPS设备告警通知"""
    notifier = DingTalkNotifier(webhook_url, secret)

    emoji_map = {
        "超速告警": "⚠️",
        "出区域告警": "📍",
        "断电告警": "🔋",
        "拆机告警": "🛠️",
        "低电量告警": "🔋",
        "SOS报警": "🆘",
    }
    emoji = emoji_map.get(alert_type, "⚠️")

    content = f"""### {emoji} GPS设备告警

**设备ID：** `{device_id}`

**IMEI：** {imei}

**告警类型：** {alert_type}

**告警位置：** {location}

**时间：** {time.strftime('%Y-%m-%d %H:%M:%S')}

"""

    return notifier.send_markdown(
        title=f"{emoji} GPS告警：{alert_type}",
        content=content
    )


def send_repayment_reminder(
    webhook_url: str,
    secret: str,
    order_id: str,
    customer_name: str,
    month: str,
    amount: float,
    due_date: str
) -> Dict:
    """还款提醒通知"""
    notifier = DingTalkNotifier(webhook_url, secret)

    content = f"""### 💳 还款提醒

**订单号：** `{order_id}`

**客户姓名：** {customer_name}

**还款月份：** {month}

**应还金额：** ¥{amount:,.2f}

**还款日期：** {due_date}

**温馨提示：** 请确保还款账户余额充足，避免逾期影响信用。

"""

    return notifier.send_markdown(
        title=f"💳 还款提醒：{customer_name} {month}月",
        content=content
    )


# =============================================================================
# 配置说明
# =============================================================================

if __name__ == "__main__":
    # ⚠️  请替换为你的实际钉钉 webhook 地址和 secret
    # 获取方式：钉钉群 → 群设置 → 智能群助手 → 自定义机器人
    WEBHOOK_URL = "https://oapi.dingtalk.com/robot/send?access_token=YOUR_TOKEN"
    SECRET = "YOUR_SECRET"  # 如果没有加签则留空

    # 演示：发送一条测试消息
    notifier = DingTalkNotifier(WEBHOOK_URL, SECRET)
    result = notifier.send_markdown(
        title="🚗 汽车分期管理系统通知测试",
        content="""### 🎉 钉钉通知接入成功！

这是一条来自**汽车分期智能管理平台**的测试消息。

**通知功能：**
- ✅ 订单阶段变更通知
- ✅ 垫资审批/出账通知
- ✅ 逾期告警通知
- ✅ GPS告警通知
- ✅ 还款提醒通知
- ✅ 归档完成通知

所有业务节点均可自动触发钉钉消息，推送给相关人员！
"""
    )

    print(f"发送结果：{result}")
