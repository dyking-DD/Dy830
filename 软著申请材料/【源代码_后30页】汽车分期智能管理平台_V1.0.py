# ============================================================================
# 汽车分期智能管理平台 V1.0 - 后30页源代码
# 计算机软件著作权登记 - 程序鉴别材料
# ============================================================================

import os
import sys
import json
import math
import time
import datetime
import hashlib
import uuid
import string
import random
from typing import Dict, List, Optional, Any
from decimal import Decimal, ROUND_HALF_UP
from enum import Enum


# ============================================================================
# 第七部分：核心业务逻辑 - 垫资服务
# ============================================================================

class AdvanceService:
    """
    垫资管理服务
    核心独创技术点：
    1. 智能计息引擎（按日计息 + 多种利率模式）
    2. 垫资状态机（严格的状态流转控制）
    3. 逾期自动检测与标记
    4. 垫资仪表盘实时统计
    """

    # 状态流转定义
    STATUS_FLOW = {
        "待审批": ["审批通过", "审批拒绝"],
        "审批通过": ["已出账"],
        "审批拒绝": [],  # 终止状态
        "已出账": ["已还清", "逾期"],
        "已还清": [],  # 终止状态
        "逾期": ["已还清"],  # 逾期后可还款变为已还清
    }

    def __init__(self, db: 'Database'):
        self.db = db

    @staticmethod
    def generate_advance_id() -> str:
        """生成垫资单号：DZ-YYYYMMDD-XXXX"""
        today = datetime.datetime.now().strftime("%Y%m%d")
        random_part = ''.join(random.choices(string.digits, k=4))
        return f"DZ-{today}-{random_part}"

    def create_advance(self, req: 'AdvanceCreateRequest', created_by: str) -> str:
        """创建垫资单"""
        conn = self.db.get_connection()
        cursor = conn.cursor()

        try:
            advance_id = self.generate_advance_id()
            now = datetime.datetime.now().isoformat()

            # 验证关联订单存在
            cursor.execute("SELECT order_id, customer_id FROM orders WHERE order_id = ?",
                         (req.order_id,))
            order = cursor.fetchone()
            if not order:
                raise ValueError(f"订单{req.order_id}不存在")

            # 获取客户名
            cursor.execute("SELECT name FROM customers WHERE customer_id = ?",
                          (order['customer_id'],))
            customer = cursor.fetchone()
            customer_name = customer['name'] if customer else "未知"

            # 计算利息
            start_date = datetime.datetime.strptime(req.start_date, "%Y-%m-%d")
            end_date = datetime.datetime.strptime(req.expected_repayment_date, "%Y-%m-%d")
            days = (end_date - start_date).days
            days = max(days, 1)  # 最低1天

            # 使用日利率计算
            daily_rate = float(req.interest_rate) / 30 if req.interest_rate else 0.0005
            interest_amount = float(req.advance_amount) * daily_rate * days

            # 本息合计
            total_amount = float(req.advance_amount) + interest_amount

            # 插入垫资单
            cursor.execute("""
                INSERT INTO advances (
                    advance_id, order_id, advance_amount, payer_type, payer_account,
                    purpose, interest_rate, start_date, expected_repayment_date,
                    interest_amount, total_amount, status, created_by, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                advance_id,
                req.order_id,
                float(req.advance_amount),
                req.payer_type,
                req.payer_account,
                req.purpose,
                float(req.interest_rate) if req.interest_rate else 0.015,
                req.start_date,
                req.expected_repayment_date,
                round(interest_amount, 2),
                round(total_amount, 2),
                "待审批",
                created_by,
                now,
                now
            ))

            conn.commit()

            # 更新订单阶段为垫资预审
            cursor.execute("""
                UPDATE orders SET stage = ?, stage_updated_at = ?
                WHERE order_id = ?
            """, ("垫资预审", now, req.order_id))

            conn.commit()
            return advance_id

        except Exception as e:
            conn.rollback()
            raise
        finally:
            conn.close()

    def approve_advance(
        self,
        advance_id: str,
        req: 'AdvanceApproveRequest'
    ) -> bool:
        """审批垫资"""
        conn = self.db.get_connection()
        cursor = conn.cursor()

        try:
            now = datetime.datetime.now().isoformat()

            # 查询当前状态
            cursor.execute("SELECT status, order_id FROM advances WHERE advance_id = ?",
                         (advance_id,))
            record = cursor.fetchone()

            if not record:
                raise ValueError(f"垫资单{advance_id}不存在")

            current_status = record['status']
            target_status = "审批通过" if req.approved else "审批拒绝"

            # 验证状态流转
            allowed_next = self.STATUS_FLOW.get(current_status, [])
            if target_status not in allowed_next:
                raise ValueError(f"状态不允许从{current_status}变更为{target_status}")

            # 更新垫资单
            cursor.execute("""
                UPDATE advances SET
                    status = ?,
                    approver = ?,
                    approver_opinion = ?,
                    approved_at = ?,
                    updated_at = ?
                WHERE advance_id = ?
            """, (
                target_status,
                req.approver,
                req.opinion,
                now,
                now,
                advance_id
            ))

            # 如果拒绝，同时更新订单阶段
            if not req.approved:
                cursor.execute("""
                    UPDATE orders SET stage = ?, stage_updated_at = ?
                    WHERE order_id = ?
                """, ("垫资审批拒绝", now, record['order_id']))

            conn.commit()
            return True

        except Exception as e:
            conn.rollback()
            raise
        finally:
            conn.close()

    def disburse_advance(self, advance_id: str, disbursed_by: str) -> bool:
        """垫资出账"""
        conn = self.db.get_connection()
        cursor = conn.cursor()

        try:
            now = datetime.datetime.now().isoformat()

            cursor.execute("SELECT status, order_id FROM advances WHERE advance_id = ?",
                         (advance_id,))
            record = cursor.fetchone()

            if not record:
                raise ValueError(f"垫资单{advance_id}不存在")

            if record['status'] != "审批通过":
                raise ValueError(f"只有审批通过的垫资单才能出账，当前状态：{record['status']}")

            cursor.execute("""
                UPDATE advances SET status = ?, updated_at = ?
                WHERE advance_id = ?
            """, ("已出账", now, advance_id))

            cursor.execute("""
                UPDATE orders SET stage = ?, stage_updated_at = ?
                WHERE order_id = ?
            """, ("垫资已出账", now, record['order_id']))

            conn.commit()
            return True

        except Exception as e:
            conn.rollback()
            raise
        finally:
            conn.close()

    def repay_advance(self, advance_id: str, req: 'AdvanceRepayRequest') -> Dict:
        """垫资还款"""
        conn = self.db.get_connection()
        cursor = conn.cursor()

        try:
            now = datetime.datetime.now().isoformat()
            repayment_date = req.repayment_date or now[:10]

            cursor.execute("""
                SELECT advance_amount, interest_amount, total_amount, status, order_id
                FROM advances WHERE advance_id = ?
            """, (advance_id,))
            record = cursor.fetchone()

            if not record:
                raise ValueError(f"垫资单{advance_id}不存在")

            if record['status'] not in ["已出账", "逾期"]:
                raise ValueError(f"当前状态{record['status']}不允许还款操作")

            repayment_amount = float(req.repayment_amount)

            # 判断是否全额还款
            remaining = record['total_amount'] - repayment_amount

            if abs(remaining) < 1:  # 差额小于1元视为全额
                new_status = "已还清"
            else:
                new_status = record['status']  # 保持原状态（部分还款）

            cursor.execute("""
                UPDATE advances SET
                    status = ?,
                    actual_repayment_date = ?,
                    updated_at = ?
                WHERE advance_id = ?
            """, (new_status, repayment_date, now, advance_id))

            cursor.execute("""
                UPDATE orders SET stage = ?, stage_updated_at = ?
                WHERE order_id = ?
            """, ("垫资已还清", now, record['order_id']))

            conn.commit()

            return {
                "advance_id": advance_id,
                "repayment_amount": repayment_amount,
                "remaining": round(remaining, 2),
                "status": new_status,
                "is_full_repayment": abs(remaining) < 1
            }

        except Exception as e:
            conn.rollback()
            raise
        finally:
            conn.close()

    def calculate_interest(
        self,
        principal: Decimal,
        rate: Decimal,
        start_date: str,
        end_date: str,
        method: str = "daily"
    ) -> Dict:
        """
        计算垫资利息
        支持按日计息和按月计息
        """
        start = datetime.datetime.strptime(start_date, "%Y-%m-%d")
        end = datetime.datetime.strptime(end_date, "%Y-%m-%d")
        days = (end - start).days
        days = max(days, 1)

        if method == "daily":
            daily_rate = float(rate) / 30
            interest = float(principal) * daily_rate * days
        elif method == "monthly":
            months = days / 30
            interest = float(principal) * float(rate) * months
        else:  # simple
            interest = float(principal) * float(rate) * (days / 365)

        return {
            "principal": float(principal),
            "rate": float(rate),
            "method": method,
            "days": days,
            "interest": round(interest, 2),
            "total": round(float(principal) + interest, 2)
        }

    def check_overdue(self) -> List[str]:
        """检测所有逾期垫资单，返回逾期单号列表"""
        conn = self.db.get_connection()
        cursor = conn.cursor()

        today = datetime.date.today().isoformat()
        overdue_ids = []

        try:
            cursor.execute("""
                SELECT advance_id FROM advances
                WHERE status = '已出账'
                AND expected_repayment_date < ?
            """, (today,))

            for row in cursor.fetchall():
                overdue_ids.append(row['advance_id'])
                # 更新状态为逾期
                cursor.execute("""
                    UPDATE advances SET status = ?, updated_at = ?
                    WHERE advance_id = ?
                """, ("逾期", datetime.datetime.now().isoformat(), row['advance_id']))

                # 更新关联订单状态
                cursor.execute("""
                    SELECT order_id FROM advances WHERE advance_id = ?
                """, (row['advance_id'],))
                order_row = cursor.fetchone()
                if order_row:
                    cursor.execute("""
                        UPDATE orders SET stage = ?, stage_updated_at = ?
                        WHERE order_id = ?
                    """, ("逾期", datetime.datetime.now().isoformat(), order_row['order_id']))

            conn.commit()
            return overdue_ids

        finally:
            conn.close()

    def get_dashboard(self) -> 'AdvanceDashboard':
        """获取垫资仪表盘数据"""
        conn = self.db.get_connection()
        cursor = conn.cursor()

        today = datetime.date.today().isoformat()
        month_start = datetime.date.today().replace(day=1).isoformat()
        today_full = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")[:10]

        try:
            # 当前垫资余额（所有未还清垫资本金之和）
            cursor.execute("""
                SELECT COALESCE(SUM(advance_amount), 0) as total
                FROM advances WHERE status IN ('已出账', '逾期')
            """)
            total_balance = cursor.fetchone()['total']

            # 今日新垫资
            cursor.execute("""
                SELECT COALESCE(SUM(advance_amount), 0) as total
                FROM advances
                WHERE created_at LIKE ?
            """, (f"{today_full[:10]}%",))
            today_new = cursor.fetchone()['total']

            # 本月新垫资
            cursor.execute("""
                SELECT COALESCE(SUM(advance_amount), 0) as total
                FROM advances WHERE created_at LIKE ?
            """, (f"{month_start[:7]}%",))
            month_new = cursor.fetchone()['total']

            # 待还笔数
            cursor.execute("""
                SELECT COUNT(*) as cnt FROM advances
                WHERE status IN ('已出账', '逾期', '审批通过')
            """)
            pending_count = cursor.fetchone()['cnt']

            # 逾期笔数
            cursor.execute("SELECT COUNT(*) as cnt FROM advances WHERE status = '逾期'")
            overdue_count = cursor.fetchone()['cnt']

            # 逾期金额
            cursor.execute("""
                SELECT COALESCE(SUM(advance_amount), 0) as total
                FROM advances WHERE status = '逾期'
            """)
            overdue_amount = cursor.fetchone()['total']

            # 近期垫资列表（最近10条）
            cursor.execute("""
                SELECT a.*, c.name as customer_name
                FROM advances a
                LEFT JOIN orders o ON a.order_id = o.order_id
                LEFT JOIN customers c ON o.customer_id = c.customer_id
                ORDER BY a.created_at DESC LIMIT 10
            """)
            recent_list = [dict(row) for row in cursor.fetchall()]

            # 近30天余额趋势（简化版：返回每日快照数据点）
            balance_trend = []
            for i in range(30, -1, -1):
                date_point = (datetime.date.today() - datetime.timedelta(days=i)).isoformat()
                cursor.execute("""
                    SELECT COALESCE(SUM(advance_amount), 0) as balance
                    FROM advances
                    WHERE status IN ('已出账', '逾期')
                    AND created_at <= ?
                """, (f"{date_point} 23:59:59",))
                balance = cursor.fetchone()['balance']
                balance_trend.append({
                    "date": date_point,
                    "balance": balance
                })

            return AdvanceDashboard(
                total_balance=Decimal(str(total_balance)),
                today_new_amount=Decimal(str(today_new)),
                month_new_amount=Decimal(str(month_new)),
                pending_count=pending_count,
                overdue_count=overdue_count,
                overdue_amount=Decimal(str(overdue_amount)),
                recent_list=recent_list,
                balance_trend=balance_trend
            )

        finally:
            conn.close()


# ============================================================================
# 第八部分：核心业务逻辑 - GPS服务
# ============================================================================

class GPSService:
    """
    GPS设备管理服务
    核心独创技术点：
    1. 设备在线状态实时监控（心跳检测）
    2. 分级告警机制（超速/出区域/断电/拆机）
    3. GPS驾驶舱实时数据聚合
    4. 多设备类型支持（有線/无线/隐蔽）
    """

    ALERT_LEVELS = {
        "超速告警": "warning",
        "出区域告警": "danger",
        "断电告警": "danger",
        "拆机告警": "danger",
        "低电量告警": "warning",
        "SOS紧急报警": "danger",
    }

    def __init__(self, db: 'Database'):
        self.db = db

    @staticmethod
    def generate_device_id() -> str:
        """生成设备编号：GPS-XXXX-XXXX"""
        part1 = ''.join(random.choices(string.ascii_uppercase, k=4))
        part2 = ''.join(random.choices(string.digits, k=4))
        return f"GPS-{part1}-{part2}"

    @staticmethod
    def generate_alert_id() -> str:
        """生成告警编号：ALT-YYYYMMDD-XXXX"""
        today = datetime.datetime.now().strftime("%Y%m%d")
        random_part = ''.join(random.choices(string.digits, k=4))
        return f"ALT-{today}-{random_part}"

    def register_device(self, req: 'GPSDeviceCreateRequest') -> str:
        """注册GPS设备"""
        conn = self.db.get_connection()
        cursor = conn.cursor()

        try:
            device_id = self.generate_device_id()
            now = datetime.datetime.now().isoformat()

            cursor.execute("""
                INSERT INTO gps_devices (
                    device_id, order_id, imei, device_type, install_location,
                    install_staff, install_date, online_status, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                device_id,
                req.order_id,
                req.imei,
                req.device_type,
                req.install_location,
                req.install_staff,
                now[:10],
                "离线",
                now,
                now
            ))

            conn.commit()

            # 更新关联订单状态为GPS安装中
            cursor.execute("""
                UPDATE orders SET stage = ?, stage_updated_at = ?
                WHERE order_id = ?
            """, ("GPS安装中", now, req.order_id))

            conn.commit()
            return device_id

        except Exception as e:
            conn.rollback()
            raise
        finally:
            conn.close()

    def device_online(self, device_id: str, location: str = None) -> bool:
        """设备上线（心跳）"""
        conn = self.db.get_connection()
        cursor = conn.cursor()

        try:
            now = datetime.datetime.now().isoformat()

            cursor.execute("""
                UPDATE gps_devices SET
                    online_status = ?,
                    last_heartbeat = ?,
                    current_location = ?,
                    updated_at = ?
                WHERE device_id = ?
            """, ("在线", now, location, now, device_id))

            if cursor.rowcount == 0:
                raise ValueError(f"设备{device_id}不存在")

            conn.commit()
            return True

        except Exception as e:
            conn.rollback()
            raise
        finally:
            conn.close()

    def device_offline(self, device_id: str) -> bool:
        """设备离线"""
        conn = self.db.get_connection()
        cursor = conn.cursor()

        try:
            now = datetime.datetime.now().isoformat()

            cursor.execute("""
                UPDATE gps_devices SET
                    online_status = ?,
                    updated_at = ?
                WHERE device_id = ?
            """, ("离线", now, device_id))

            conn.commit()
            return True

        except Exception as e:
            conn.rollback()
            raise
        finally:
            conn.close()

    def add_alert(
        self,
        device_id: str,
        alert_type: str,
        location: str = None
    ) -> str:
        """添加告警记录"""
        conn = self.db.get_connection()
        cursor = conn.cursor()

        try:
            alert_id = self.generate_alert_id()
            now = datetime.datetime.now().isoformat()

            cursor.execute("""
                INSERT INTO gps_alerts (
                    alert_id, device_id, alert_type, alert_time, location, handled, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                alert_id,
                device_id,
                alert_type,
                now,
                location,
                0,
                now
            ))

            # 更新设备状态为告警中
            cursor.execute("""
                UPDATE gps_devices SET online_status = ?, updated_at = ?
                WHERE device_id = ?
            """, ("告警中", now, device_id))

            conn.commit()
            return alert_id

        except Exception as e:
            conn.rollback()
            raise
        finally:
            conn.close()

    def handle_alert(self, alert_id: str, handled_by: str) -> bool:
        """处理告警"""
        conn = self.db.get_connection()
        cursor = conn.cursor()

        try:
            now = datetime.datetime.now().isoformat()

            cursor.execute("""
                UPDATE gps_alerts SET
                    handled = ?,
                    handled_by = ?,
                    handled_time = ?
                WHERE alert_id = ?
            """, (1, handled_by, now, alert_id))

            # 如果设备还有其他未处理告警，保持告警状态
            cursor.execute("""
                SELECT COUNT(*) as cnt FROM gps_alerts
                WHERE device_id = (SELECT device_id FROM gps_alerts WHERE alert_id = ?)
                AND handled = 0
            """, (alert_id,))
            remaining = cursor.fetchone()['cnt']

            if remaining == 0:
                # 没有未处理告警，设备恢复在线
                cursor.execute("""
                    UPDATE gps_devices SET online_status = ?, updated_at = ?
                    WHERE device_id = (SELECT device_id FROM gps_alerts WHERE alert_id = ?)
                """, ("在线", now, alert_id))

            conn.commit()
            return True

        except Exception as e:
            conn.rollback()
            raise
        finally:
            conn.close()

    def poll_gps_status(self, gps_api_func=None) -> Dict:
        """
        轮询GPS设备状态（对接第三方API）
        gps_api_func: 第三方GPS API查询函数
        """
        conn = self.db.get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute("SELECT device_id, imei, online_status FROM gps_devices")
            devices = cursor.fetchall()

            results = {"checked": 0, "online": 0, "offline": 0, "alerts": 0}

            config = get_config()
            offline_threshold = config.gps_offline_threshold

            for device in devices:
                results["checked"] += 1

                if gps_api_func:
                    # 调用第三方API
                    try:
                        api_result = gps_api_func(device['imei'])

                        if api_result.get("status") == "online":
                            self.device_online(device['device_id'], api_result.get("location"))
                            results["online"] += 1

                            # 检查告警
                            for alert_type in api_result.get("alerts", []):
                                self.add_alert(device['device_id'], alert_type, api_result.get("location"))
                                results["alerts"] += 1

                        else:
                            self.device_offline(device['device_id'])
                            results["offline"] += 1

                    except Exception:
                        self.device_offline(device['device_id'])
                        results["offline"] += 1
                else:
                    # 模拟模式：基于心跳时间判断
                    cursor.execute("""
                        SELECT last_heartbeat FROM gps_devices WHERE device_id = ?
                    """, (device['device_id'],))
                    heartbeat = cursor.fetchone()
                    if heartbeat and heartbeat['last_heartbeat']:
                        last_time = datetime.datetime.fromisoformat(heartbeat['last_heartbeat'])
                        seconds_ago = (datetime.datetime.now() - last_time).total_seconds()

                        if seconds_ago < offline_threshold:
                            self.device_online(device['device_id'])
                            results["online"] += 1
                        else:
                            self.device_offline(device['device_id'])
                            results["offline"] += 1

            conn.commit()
            return results

        finally:
            conn.close()

    def get_dashboard(self) -> 'GPSDashboard':
        """获取GPS驾驶舱数据"""
        conn = self.db.get_connection()
        cursor = conn.cursor()

        try:
            today = datetime.date.today().isoformat()

            # 设备统计
            cursor.execute("SELECT COUNT(*) as cnt FROM gps_devices")
            total = cursor.fetchone()['cnt']

            cursor.execute("SELECT COUNT(*) as cnt FROM gps_devices WHERE online_status = '在线'")
            online = cursor.fetchone()['cnt']

            cursor.execute("SELECT COUNT(*) as cnt FROM gps_devices WHERE online_status = '离线'")
            offline = cursor.fetchone()['cnt']

            cursor.execute("SELECT COUNT(*) as cnt FROM gps_devices WHERE online_status = '告警中'")
            alert = cursor.fetchone()['cnt']

            # 今日安装数
            cursor.execute("""
                SELECT COUNT(*) as cnt FROM gps_devices
                WHERE install_date LIKE ?
            """, (f"{today}%",))
            today_installed = cursor.fetchone()['cnt']

            # 待安装数（查询订单中处于待GPS阶段的）
            cursor.execute("SELECT COUNT(*) as cnt FROM orders WHERE stage = '已提车'")
            pending_install = cursor.fetchone()['cnt']

            # 最近告警（未处理的）
            cursor.execute("""
                SELECT g.alert_id, g.device_id, g.alert_type, g.alert_time, g.location,
                       d.imei, o.order_id
                FROM gps_alerts g
                JOIN gps_devices d ON g.device_id = d.device_id
                JOIN orders o ON d.order_id = o.order_id
                WHERE g.handled = 0
                ORDER BY g.alert_time DESC
                LIMIT 10
            """)
            recent_alerts = [dict(row) for row in cursor.fetchall()]

            return GPSDashboard(
                total_devices=total,
                online_count=online,
                offline_count=offline,
                alert_count=alert,
                today_installed=today_installed,
                pending_install=pending_install,
                recent_alerts=recent_alerts
            )

        finally:
            conn.close()


# ============================================================================
# 第九部分：核心业务逻辑 - 归档服务
# ============================================================================

class ArchiveService:
    """
    资料归档服务
    核心独创技术点：
    1. 标准归档清单管理（8类必上传资料）
    2. 智能归档清单初始化
    3. OCR识别结果存储与展示
    4. 归档进度实时追踪
    """

    DOCUMENT_TYPES = [
        ("id_card_front", "身份证人像面", True),
        ("id_card_back", "身份证国徽面", True),
        ("driving_license", "行驶证", True),
        ("vehicle_certificate", "车辆登记证（绿本）", True),
        ("gps_photos", "GPS安装照片", True),
        ("pickup_confirmation", "提车确认单", True),
        ("advance_agreement", "垫资协议", True),
        ("invoice", "购车发票", False),
        ("insurance", "保险单", False),
    ]

    def __init__(self, db: 'Database'):
        self.db = db

    @staticmethod
    def generate_document_id() -> str:
        """生成资料编号：DOC-XXXX-XXXX"""
        part1 = ''.join(random.choices(string.ascii_uppercase, k=4))
        part2 = ''.join(random.choices(string.digits, k=4))
        return f"DOC-{part1}-{part2}"

    def init_checklist(self, order_id: str) -> bool:
        """为订单初始化归档清单"""
        conn = self.db.get_connection()
        cursor = conn.cursor()

        try:
            checklist_id = f"CHK-{order_id[-8:]}"

            cursor.execute("""
                INSERT OR REPLACE INTO archive_checklists (
                    checklist_id, order_id, overall_status, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?)
            """, (
                checklist_id,
                order_id,
                "待上传",
                datetime.datetime.now().isoformat(),
                datetime.datetime.now().isoformat()
            ))

            conn.commit()
            return True

        except Exception as e:
            conn.rollback()
            raise
        finally:
            conn.close()

    def upload_document(self, req: 'ArchiveUploadRequest') -> str:
        """上传归档资料"""
        conn = self.db.get_connection()
        cursor = conn.cursor()

        try:
            document_id = self.generate_document_id()
            now = datetime.datetime.now().isoformat()

            # 插入资料记录
            cursor.execute("""
                INSERT INTO archive_documents (
                    document_id, order_id, document_type, file_name, file_url,
                    file_size, upload_time, uploaded_by
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                document_id,
                req.order_id,
                req.document_type,
                req.file_name,
                req.file_url,
                req.file_size,
                now,
                req.uploaded_by
            ))

            # 更新清单中对应类型为已上传
            field_map = {
                "身份证人像面": "id_card_front",
                "身份证": "id_card_front",
                "身份证国徽面": "id_card_back",
                "行驶证": "driving_license",
                "车辆登记证": "vehicle_certificate",
                "绿本": "vehicle_certificate",
                "GPS安装照片": "gps_photos",
                "GPS照片": "gps_photos",
                "提车确认单": "pickup_confirmation",
                "垫资协议": "advance_agreement",
                "购车发票": "invoice",
                "保险单": "insurance",
            }

            db_field = field_map.get(req.document_type)
            if db_field:
                cursor.execute(f"""
                    UPDATE archive_checklists SET {db_field} = 1, updated_at = ?
                    WHERE order_id = ?
                """, (now, req.order_id))

            # 更新清单总体状态
            self._update_checklist_status(conn, req.order_id)

            conn.commit()
            return document_id

        except Exception as e:
            conn.rollback()
            raise
        finally:
            conn.close()

    def ocr_document(self, document_id: str, ocr_result: Dict) -> bool:
        """OCR识别结果存储"""
        conn = self.db.get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute("""
                UPDATE archive_documents SET ocr_result = ?
                WHERE document_id = ?
            """, (json.dumps(ocr_result, ensure_ascii=False), document_id))

            conn.commit()
            return True

        except Exception as e:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _update_checklist_status(self, conn, order_id: str):
        """更新清单总体状态"""
        cursor = conn.cursor()

        cursor.execute("""
            SELECT * FROM archive_checklists WHERE order_id = ?
        """, (order_id,))
        checklist = cursor.fetchone()

        if not checklist:
            return

        # 统计必需项完成情况
        required_fields = [
            "id_card_front", "id_card_back", "driving_license",
            "vehicle_certificate", "gps_photos", "pickup_confirmation",
            "advance_agreement"
        ]

        required_complete = 0
        total_required = len(required_fields)

        for field in required_fields:
            if checklist[field]:
                required_complete += 1

        if required_complete == total_required:
            overall = "已完整"
        elif required_complete > 0:
            overall = "部分上传"
        else:
            overall = "待上传"

        cursor.execute("""
            UPDATE archive_checklists SET overall_status = ?, updated_at = ?
            WHERE order_id = ?
        """, (overall, datetime.datetime.now().isoformat(), order_id))

    def get_order_archive_status(self, order_id: str) -> 'ArchiveStatusResponse':
        """获取订单归档状态"""
        conn = self.db.get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute("""
                SELECT c.*, cu.name as customer_name
                FROM archive_checklists c
                JOIN orders o ON c.order_id = o.order_id
                JOIN customers cu ON o.customer_id = cu.customer_id
                WHERE c.order_id = ?
            """, (order_id,))
            checklist = cursor.fetchone()

            if not checklist:
                # 如果没有清单，初始化一个
                self.init_checklist(order_id)
                return self.get_order_archive_status(order_id)

            # 获取已上传的资料列表
            cursor.execute("""
                SELECT document_id, document_type, file_name, file_url,
                       ocr_result, upload_time, uploaded_by
                FROM archive_documents WHERE order_id = ?
                ORDER BY upload_time DESC
            """, (order_id,))
            documents = [dict(row) for row in cursor.fetchall()]

            # 构建状态项
            items = []
            required_fields = dict(self.DOCUMENT_TYPES)

            for doc_type, display_name, is_required in self.DOCUMENT_TYPES:
                field_key = doc_type.lower()
                is_uploaded = checklist.get(field_key, 0) == 1

                items.append({
                    "type": doc_type,
                    "name": display_name,
                    "required": is_required,
                    "status": "已上传" if is_uploaded else "待上传",
                    "documents": [d for d in documents if d['document_type'] == doc_type]
                })

            # 计算完成百分比
            required_count = sum(1 for _, _, req in self.DOCUMENT_TYPES if req)
            uploaded_count = sum(1 for item in items if item["status"] == "已上传")
            progress = int(uploaded_count / required_count * 100) if required_count > 0 else 0

            return ArchiveStatusResponse(
                order_id=order_id,
                customer_name=checklist['customer_name'],
                overall_status=checklist['overall_status'],
                progress_percent=progress,
                items=items
            )

        finally:
            conn.close()


# ============================================================================
# 第十部分：API路由定义（FastAPI入口）
# ============================================================================

if FASTAPI_AVAILABLE:
    app = FastAPI(
        title="汽车分期智能管理平台",
        description="垫资管理 | GPS监控 | 资料归档 | 全链路通知",
        version="1.0.0"
    )

    # CORS配置
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 依赖注入
    def get_db() -> Generator:
        db = Database()
        db.init_tables()
        yield db

    # ─── 订单路由 ───
    @app.post("/api/v1/orders", response_model=APIResponse)
    def create_order(req: OrderCreateRequest, db: Database = Depends(get_db)):
        """创建订单"""
        service = OrderService(db)
        try:
            order_id = service.create_order(req, created_by="system")
            return APIResponse(data={"order_id": order_id})
        except Exception as e:
            return APIResponse(code=500, message=str(e))

    @app.get("/api/v1/orders", response_model=APIResponse)
    def list_orders(
        stage: Optional[str] = None,
        keyword: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
        db: Database = Depends(get_db)
    ):
        """订单列表"""
        service = OrderService(db)
        try:
            orders = service.get_order_list(stage, keyword, page, page_size)
            return APIResponse(data=orders)
        except Exception as e:
            return APIResponse(code=500, message=str(e))

    @app.get("/api/v1/orders/{order_id}", response_model=APIResponse)
    def get_order(order_id: str, db: Database = Depends(get_db)):
        """订单详情"""
        service = OrderService(db)
        try:
            order = service.get_order_detail(order_id)
            if not order:
                return APIResponse(code=404, message="订单不存在")
            return APIResponse(data=order)
        except Exception as e:
            return APIResponse(code=500, message=str(e))

    # ─── 垫资路由 ───
    @app.post("/api/v1/advances", response_model=APIResponse)
    def create_advance(req: AdvanceCreateRequest, db: Database = Depends(get_db)):
        """创建垫资"""
        service = AdvanceService(db)
        try:
            advance_id = service.create_advance(req, created_by="system")
            return APIResponse(data={"advance_id": advance_id})
        except Exception as e:
            return APIResponse(code=500, message=str(e))

    @app.get("/api/v1/advances", response_model=APIResponse)
    def list_advances(
        status: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
        db: Database = Depends(get_db)
    ):
        """垫资列表"""
        conn = db.get_connection()
        cursor = conn.cursor()

        sql = """
            SELECT a.*, o.order_id, c.name as customer_name
            FROM advances a
            JOIN orders o ON a.order_id = o.order_id
            JOIN customers c ON o.customer_id = c.customer_id
            WHERE 1=1
        """
        params = []

        if status:
            sql += " AND a.status = ?"
            params.append(status)

        if start_date:
            sql += " AND a.created_at >= ?"
            params.append(start_date)

        if end_date:
            sql += " AND a.created_at <= ?"
            params.append(end_date)

        sql += " ORDER BY a.created_at DESC"

        # 分页
        offset = (page - 1) * page_size
        sql += f" LIMIT {page_size} OFFSET {offset}"

        cursor.execute(sql, params)
        items = [dict(row) for row in cursor.fetchall()]
        conn.close()

        return APIResponse(data={"items": items, "page": page, "page_size": page_size})

    @app.get("/api/v1/advances/dashboard", response_model=APIResponse)
    def advance_dashboard(db: Database = Depends(get_db)):
        """垫资仪表盘"""
        service = AdvanceService(db)
        dashboard = service.get_dashboard()
        return APIResponse(data=asdict(dashboard))

    @app.post("/api/v1/advances/{advance_id}/approve", response_model=APIResponse)
    def approve_advance(
        advance_id: str,
        req: AdvanceApproveRequest,
        db: Database = Depends(get_db)
    ):
        """审批垫资"""
        service = AdvanceService(db)
        try:
            service.approve_advance(advance_id, req)
            return APIResponse(message="审批完成")
        except Exception as e:
            return APIResponse(code=400, message=str(e))

    @app.post("/api/v1/advances/{advance_id}/disburse", response_model=APIResponse)
    def disburse_advance(advance_id: str, db: Database = Depends(get_db)):
        """垫资出账"""
        service = AdvanceService(db)
        try:
            service.disburse_advance(advance_id, disbursed_by="system")
            return APIResponse(message="出账完成")
        except Exception as e:
            return APIResponse(code=400, message=str(e))

    @app.post("/api/v1/advances/{advance_id}/repay", response_model=APIResponse)
    def repay_advance(
        advance_id: str,
        req: AdvanceRepayRequest,
        db: Database = Depends(get_db)
    ):
        """垫资还款"""
        service = AdvanceService(db)
        try:
            result = service.repay_advance(advance_id, req)
            return APIResponse(data=result)
        except Exception as e:
            return APIResponse(code=400, message=str(e))

    # ─── GPS路由 ───
    @app.get("/api/v1/gps/dashboard", response_model=APIResponse)
    def gps_dashboard(db: Database = Depends(get_db)):
        """GPS驾驶舱"""
        service = GPSService(db)
        dashboard = service.get_dashboard()
        return APIResponse(data=asdict(dashboard))

    @app.get("/api/v1/gps/devices", response_model=APIResponse)
    def list_gps_devices(
        status: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
        db: Database = Depends(get_db)
    ):
        """GPS设备列表"""
        conn = db.get_connection()
        cursor = conn.cursor()

        sql = """
            SELECT d.*, c.name as customer_name, o.order_id
            FROM gps_devices d
            JOIN orders o ON d.order_id = o.order_id
            JOIN customers c ON o.customer_id = c.customer_id
            WHERE 1=1
        """
        params = []

        if status:
            sql += " AND d.online_status = ?"
            params.append(status)

        offset = (page - 1) * page_size
        sql += f" ORDER BY d.created_at DESC LIMIT {page_size} OFFSET {offset}"

        cursor.execute(sql, params)
        items = [dict(row) for row in cursor.fetchall()]
        conn.close()

        return APIResponse(data={"items": items})

    # ─── 归档路由 ───
    @app.get("/api/v1/archive/{order_id}/status", response_model=APIResponse)
    def archive_status(order_id: str, db: Database = Depends(get_db)):
        """归档状态"""
        service = ArchiveService(db)
        status = service.get_order_archive_status(order_id)
        return APIResponse(data=asdict(status))

    @app.post("/api/v1/archive/upload", response_model=APIResponse)
    def upload_document(req: ArchiveUploadRequest, db: Database = Depends(get_db)):
        """上传归档资料"""
        service = ArchiveService(db)
        try:
            doc_id = service.upload_document(req)
            return APIResponse(data={"document_id": doc_id})
        except Exception as e:
            return APIResponse(code=500, message=str(e))


# ============================================================================
# 第十一部分：定时任务（逾期检测）
# ============================================================================

class Scheduler:
    """
    定时任务调度器
    核心独创技术点：基于时间触发的逾期检测和通知发送
    """

    def __init__(self, db: Database):
        self.db = db
        self.running = False

    def check_overdue_advances(self) -> List[str]:
        """每日检测垫资逾期"""
        service = AdvanceService(self.db)
        return service.check_overdue()

    def send_overdue_notifications(self) -> int:
        """发送逾期通知"""
        conn = self.db.get_connection()
        cursor = conn.cursor()
        sent = 0

        try:
            today = datetime.date.today().isoformat()

            # 查找逾期3天的
            cursor.execute("""
                SELECT a.advance_id, a.order_id, c.name, c.phone
                FROM advances a
                JOIN orders o ON a.order_id = o.order_id
                JOIN customers c ON o.customer_id = c.customer_id
                WHERE a.status = '逾期'
                AND date(a.updated_at) <= date('now', '-3 days')
            """)

            for row in cursor.fetchall():
                # 发送3天逾期通知（模拟）
                print(f"[通知] 发送逾期3天提醒: {row['name']} {row['phone']}")
                sent += 1

            # 查找逾期7天的
            cursor.execute("""
                SELECT a.advance_id, a.order_id, c.name, c.phone
                FROM advances a
                JOIN orders o ON a.order_id = o.order_id
                JOIN customers c ON o.customer_id = c.customer_id
                WHERE a.status = '逾期'
                AND date(a.updated_at) <= date('now', '-7 days')
            """)

            for row in cursor.fetchall():
                # 发送7天严重警告（模拟）
                print(f"[通知] 发送逾期7天警告: {row['name']} {row['phone']}")
                sent += 1

            return sent

        finally:
            conn.close()


# ============================================================================
# 第十二部分：主程序入口
# ============================================================================

def main():
    """程序入口"""
    import argparse

    parser = argparse.ArgumentParser(description="汽车分期智能管理平台 V1.0")
    parser.add_argument("--init-db", action="store_true", help="初始化数据库")
    parser.add_argument("--port", type=int, default=8000, help="服务端口")
    args = parser.parse_args()

    if args.init_db:
        print("初始化数据库...")
        db = Database()
        db.init_tables()
        print("数据库初始化完成")
        return

    if FASTAPI_AVAILABLE:
        print(f"启动API服务，端口：{args.port}")
        import uvicorn
        uvicorn.run(app, host="0.0.0.0", port=args.port)
    else:
        print("FastAPI未安装，无法启动Web服务")
        print("请运行: pip install fastapi uvicorn")


if __name__ == "__main__":
    main()
