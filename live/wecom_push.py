#!/usr/bin/env python3
"""
TrendMatrix 企业微信推送模块（群机器人方式）
"""

import requests
import json

WEBHOOK_URL = "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=589a7c03-a8a0-4040-9b66-0c5a6fb9f3f0"


def send_text_message(content: str) -> bool:
    """发送文本消息到群机器人"""
    payload = {
        "msgtype": "text",
        "text": {"content": content, "mentioned_list": []}
    }
    try:
        r = requests.post(WEBHOOK_URL, json=payload, timeout=10)
        d = r.json()
        if d.get("errcode") == 0:
            return True
        else:
            print(f"发送失败: {d}")
            return False
    except Exception as e:
        print(f"请求异常: {e}")
        return False


def format_daily_report(output_text: str) -> str:
    """格式化每日报告"""
    lines = output_text.strip().split("\n")
    msg = "📊 TrendMatrix 每日模拟实盘\n\n"
    in_position = False
    for line in lines:
        line = line.strip()
        if not line or line.startswith("="):
            continue
        if any(k in line for k in ["[大盘]", "[汇总]", "[持仓]", "[入场]"]):
            msg += f"\n{line}\n"
        elif line.startswith("→"):
            msg += f"  {line}\n"
        elif "✓" in line or "✗" in line:
            msg += f"  {line}\n"
        elif "现金:" in line or "持仓:" in line or "日期:" in line:
            msg += f"{line}\n"
        elif "只" in line and "无" not in line:
            msg += f"  {line}\n"
    return msg.strip()


def push_report(output_text: str) -> bool:
    """推送报告到企业微信"""
    msg = format_daily_report(output_text)
    success = send_text_message(msg)
    print(f"[企微推送] {'成功' if success else '失败'}")
    return success


def push_simple_msg(content: str) -> bool:
    """推送简单文本消息"""
    return send_text_message(content)


if __name__ == "__main__":
    # 测试
    send_text_message("TrendMatrix 推送测试成功 ✅")
