# -*- coding: utf-8 -*-
"""
GPS服务模块
处理GPS设备的注册、心跳、告警等业务逻辑
"""
from datetime import datetime, date, timedelta
from typing import Optional, List, Dict, Any
import random
import sys
import os

# 添加父目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database import get_db_connection, generate_id


def row_to_dict(row) -> dict:
    """将 sqlite3.Row 转换为字典"""
    return dict(row) if row else None


# ==================== 设备类型映射 ====================

DEVICE_TYPE_NAMES = {
    "有线": "有线GPS",
    "无线": "无线GPS",
    "隐蔽": "隐蔽式GPS",
}

ALERT_TYPE_NAMES = {
    "超速告警": "超速告警",
    "出区域告警": "出区域告警",
    "断电告警": "断电告警",
    "拆机告警": "拆机告警",
    "低电量告警": "低电量告警",
    "SOS报警": "SOS报警",
}


# ==================== GPS设备服务 ====================

def register_device(data: dict) -> dict:
    """
    注册GPS设备
    
    Args:
        data: 包含订单ID、IMEI、设备类型、安装位置、安装人员等信息
        
    Returns:
        注册结果
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # 检查订单是否存在
        cursor.execute("""
            SELECT o.order_id, c.name as customer_name
            FROM orders o
            LEFT JOIN customers c ON o.customer_id = c.customer_id
            WHERE o.order_id = ?
        """, (data.get("order_id"),))
        
        order = cursor.fetchone()
        if not order:
            return {"success": False, "message": "订单不存在"}
        
        # 检查IMEI是否已存在
        cursor.execute("SELECT device_id FROM gps_devices WHERE imei = ?", (data.get("imei"),))
        if cursor.fetchone():
            return {"success": False, "message": "该IMEI已注册"}
        
        # 检查订单是否已关联GPS设备
        cursor.execute("SELECT device_id FROM gps_devices WHERE order_id = ?", (data.get("order_id"),))
        if cursor.fetchone():
            return {"success": False, "message": "该订单已关联GPS设备"}
        
        # 生成设备ID
        device_id = generate_id("GPS")
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # 插入设备记录
        cursor.execute("""
            INSERT INTO gps_devices (
                device_id, order_id, imei, device_type, install_location,
                install_staff, install_date, online_status, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            device_id, data.get("order_id"), data.get("imei"), data.get("device_type"),
            data.get("install_location"), data.get("install_staff"),
            data.get("install_date", now.split()[0]), "离线", now, now
        ))
        
        # 更新订单阶段
        cursor.execute("""
            UPDATE orders SET stage = 'GPS安装中', stage_updated_at = ?
            WHERE order_id = ?
        """, (now, data.get("order_id")))
        
        conn.commit()
        
        # 查询创建的设备
        cursor.execute("""
            SELECT d.*, c.name as customer_name
            FROM gps_devices d
            LEFT JOIN orders o ON d.order_id = o.order_id
            LEFT JOIN customers c ON o.customer_id = c.customer_id
            WHERE d.device_id = ?
        """, (device_id,))
        
        device = cursor.fetchone()
        
        return {
            "success": True,
            "message": "设备注册成功",
            "data": row_to_dict(device)
        }
    except Exception as e:
        conn.rollback()
        return {"success": False, "message": f"注册失败: {str(e)}"}
    finally:
        conn.close()


def heartbeat(device_id: str, latitude: float, longitude: float, location: str = None) -> dict:
    """
    设备心跳
    
    Args:
        device_id: 设备ID
        latitude: 纬度
        longitude: 经度
        location: 位置描述
        
    Returns:
        心跳处理结果
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # 检查设备是否存在
        cursor.execute("SELECT device_id FROM gps_devices WHERE device_id = ?", (device_id,))
        if not cursor.fetchone():
            return {"success": False, "message": "设备不存在"}
        
        # 更新设备状态
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        location_str = location or f"{latitude},{longitude}"
        
        cursor.execute("""
            UPDATE gps_devices
            SET online_status = '在线', last_heartbeat = ?, current_location = ?, updated_at = ?
            WHERE device_id = ?
        """, (now, location_str, now, device_id))
        
        conn.commit()
        
        return {
            "success": True,
            "message": "心跳更新成功",
            "data": {
                "device_id": device_id,
                "online_status": "在线",
                "last_heartbeat": now,
                "location": location_str
            }
        }
    except Exception as e:
        conn.rollback()
        return {"success": False, "message": f"心跳处理失败: {str(e)}"}
    finally:
        conn.close()


def add_alert(data: dict) -> dict:
    """
    添加GPS告警
    
    Args:
        data: 包含设备ID、告警类型、位置等信息
        
    Returns:
        告警创建结果
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # 检查设备是否存在
        cursor.execute("""
            SELECT d.device_id, d.imei, c.name as customer_name
            FROM gps_devices d
            LEFT JOIN orders o ON d.order_id = o.order_id
            LEFT JOIN customers c ON o.customer_id = c.customer_id
            WHERE d.device_id = ?
        """, (data.get("device_id"),))
        
        device = cursor.fetchone()
        if not device:
            return {"success": False, "message": "设备不存在"}
        
        # 生成告警ID
        alert_id = generate_id("ALT")
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # 插入告警记录
        cursor.execute("""
            INSERT INTO gps_alerts (
                alert_id, device_id, alert_type, alert_time, location, handled, created_at
            ) VALUES (?, ?, ?, ?, ?, 0, ?)
        """, (
            alert_id, data.get("device_id"), data.get("alert_type"),
            data.get("alert_time", now), data.get("location"), now
        ))
        
        # 更新设备状态为告警中
        cursor.execute("""
            UPDATE gps_devices SET online_status = '告警中', updated_at = ?
            WHERE device_id = ?
        """, (now, data.get("device_id")))
        
        conn.commit()
        
        result = {
            "alert_id": alert_id,
            "device_id": data.get("device_id"),
            "imei": device["imei"],
            "customer_name": device["customer_name"],
            "alert_type": data.get("alert_type"),
            "alert_type_name": ALERT_TYPE_NAMES.get(data.get("alert_type"), data.get("alert_type")),
            "location": data.get("location"),
            "alert_time": data.get("alert_time", now),
            "handled": False
        }
        
        return {
            "success": True,
            "message": "告警创建成功",
            "data": result
        }
    except Exception as e:
        conn.rollback()
        return {"success": False, "message": f"创建告警失败: {str(e)}"}
    finally:
        conn.close()


def handle_alert(alert_id: str, handled_by: str, handle_note: str = None) -> dict:
    """
    处理GPS告警
    
    Args:
        alert_id: 告警ID
        handled_by: 处理人
        handle_note: 处理备注
        
    Returns:
        处理结果
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # 查询告警
        cursor.execute("""
            SELECT a.*, d.device_id as dev_id
            FROM gps_alerts a
            LEFT JOIN gps_devices d ON a.device_id = d.device_id
            WHERE a.alert_id = ?
        """, (alert_id,))
        
        alert = cursor.fetchone()
        if not alert:
            return {"success": False, "message": "告警不存在"}
        
        if alert["handled"]:
            return {"success": False, "message": "该告警已处理"}
        
        # 更新告警状态
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        cursor.execute("""
            UPDATE gps_alerts
            SET handled = 1, handled_by = ?, handled_time = ?
            WHERE alert_id = ?
        """, (handled_by, now, alert_id))
        
        # 检查该设备是否还有其他未处理告警
        cursor.execute("""
            SELECT COUNT(*) as count FROM gps_alerts
            WHERE device_id = ? AND handled = 0
        """, (alert["device_id"],))
        
        unhandled_count = cursor.fetchone()["count"]
        
        # 如果没有其他未处理告警，恢复设备状态
        if unhandled_count == 0:
            cursor.execute("""
                UPDATE gps_devices SET online_status = '在线', updated_at = ?
                WHERE device_id = ?
            """, (now, alert["device_id"]))
        
        conn.commit()
        
        return {
            "success": True,
            "message": "告警处理成功",
            "data": {
                "alert_id": alert_id,
                "handled": True,
                "handled_by": handled_by,
                "handled_time": now
            }
        }
    except Exception as e:
        conn.rollback()
        return {"success": False, "message": f"处理失败: {str(e)}"}
    finally:
        conn.close()


def get_device_list(status: str = None, page: int = 1, page_size: int = 20) -> dict:
    """获取设备列表"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        conditions = []
        params = []
        
        if status:
            conditions.append("d.online_status = ?")
            params.append(status)
        
        where_clause = " AND ".join(conditions) if conditions else "1=1"
        
        # 查询总数
        count_sql = f"SELECT COUNT(*) as total FROM gps_devices d WHERE {where_clause}"
        cursor.execute(count_sql, params)
        total = cursor.fetchone()["total"]
        
        # 分页查询
        offset = (page - 1) * page_size
        list_sql = f"""
            SELECT d.*, c.name as customer_name
            FROM gps_devices d
            LEFT JOIN orders o ON d.order_id = o.order_id
            LEFT JOIN customers c ON o.customer_id = c.customer_id
            WHERE {where_clause}
            ORDER BY d.created_at DESC
            LIMIT ? OFFSET ?
        """
        cursor.execute(list_sql, params + [page_size, offset])
        
        devices = []
        for row in cursor.fetchall():
            device = row_to_dict(row)
            device["device_type_name"] = DEVICE_TYPE_NAMES.get(device["device_type"], device["device_type"])
            devices.append(device)
        
        return {
            "success": True,
            "data": {
                "total": total,
                "page": page,
                "page_size": page_size,
                "items": devices
            }
        }
    finally:
        conn.close()


def get_alert_list(handled: bool = None, alert_type: str = None, page: int = 1, page_size: int = 20) -> dict:
    """获取告警列表"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        conditions = []
        params = []
        
        if handled is not None:
            conditions.append("a.handled = ?")
            params.append(1 if handled else 0)
        
        if alert_type:
            conditions.append("a.alert_type = ?")
            params.append(alert_type)
        
        where_clause = " AND ".join(conditions) if conditions else "1=1"
        
        # 查询总数
        count_sql = f"SELECT COUNT(*) as total FROM gps_alerts a WHERE {where_clause}"
        cursor.execute(count_sql, params)
        total = cursor.fetchone()["total"]
        
        # 分页查询
        offset = (page - 1) * page_size
        list_sql = f"""
            SELECT a.*, d.imei, c.name as customer_name
            FROM gps_alerts a
            LEFT JOIN gps_devices d ON a.device_id = d.device_id
            LEFT JOIN orders o ON d.order_id = o.order_id
            LEFT JOIN customers c ON o.customer_id = c.customer_id
            WHERE {where_clause}
            ORDER BY a.alert_time DESC
            LIMIT ? OFFSET ?
        """
        cursor.execute(list_sql, params + [page_size, offset])
        
        alerts = []
        for row in cursor.fetchall():
            alert = row_to_dict(row)
            alert["alert_type_name"] = ALERT_TYPE_NAMES.get(alert["alert_type"], alert["alert_type"])
            alert["handled"] = bool(alert["handled"])
            alerts.append(alert)
        
        return {
            "success": True,
            "data": {
                "total": total,
                "page": page,
                "page_size": page_size,
                "items": alerts
            }
        }
    finally:
        conn.close()


def get_dashboard() -> dict:
    """获取GPS驾驶舱数据"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        today = datetime.now().strftime("%Y-%m-%d")
        
        # 设备总数
        cursor.execute("SELECT COUNT(*) as count FROM gps_devices")
        total_devices = cursor.fetchone()["count"]
        
        # 在线数
        cursor.execute("SELECT COUNT(*) as count FROM gps_devices WHERE online_status = '在线'")
        online_count = cursor.fetchone()["count"]
        
        # 离线数
        cursor.execute("SELECT COUNT(*) as count FROM gps_devices WHERE online_status = '离线'")
        offline_count = cursor.fetchone()["count"]
        
        # 告警数
        cursor.execute("SELECT COUNT(*) as count FROM gps_devices WHERE online_status = '告警中'")
        alert_count = cursor.fetchone()["count"]
        
        # 今日安装数
        cursor.execute("SELECT COUNT(*) as count FROM gps_devices WHERE DATE(install_date) = ?", (today,))
        today_installed = cursor.fetchone()["count"]
        
        # 待安装数（已提车但未安装GPS的订单）
        cursor.execute("""
            SELECT COUNT(*) as count FROM orders o
            WHERE o.stage IN ('已提车', 'GPS安装中')
              AND NOT EXISTS (SELECT 1 FROM gps_devices d WHERE d.order_id = o.order_id)
        """)
        pending_install = cursor.fetchone()["count"]
        
        # 最近10条未处理告警
        cursor.execute("""
            SELECT a.*, d.imei, c.name as customer_name
            FROM gps_alerts a
            LEFT JOIN gps_devices d ON a.device_id = d.device_id
            LEFT JOIN orders o ON d.order_id = o.order_id
            LEFT JOIN customers c ON o.customer_id = c.customer_id
            WHERE a.handled = 0
            ORDER BY a.alert_time DESC
            LIMIT 10
        """)
        
        recent_alerts = []
        for row in cursor.fetchall():
            alert = row_to_dict(row)
            alert["alert_type_name"] = ALERT_TYPE_NAMES.get(alert["alert_type"], alert["alert_type"])
            alert["handled"] = bool(alert["handled"])
            recent_alerts.append(alert)
        
        return {
            "success": True,
            "data": {
                "total_devices": total_devices,
                "online_count": online_count,
                "offline_count": offline_count,
                "alert_count": alert_count,
                "today_installed": today_installed,
                "pending_install": pending_install,
                "recent_alerts": recent_alerts
            }
        }
    finally:
        conn.close()


def poll_status() -> dict:
    """模拟轮询设备状态"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # 获取所有设备
        cursor.execute("SELECT device_id, online_status FROM gps_devices")
        devices = cursor.fetchall()
        
        if not devices:
            return {
                "success": True,
                "data": {
                    "checked": 0,
                    "online": 0,
                    "offline": 0,
                    "alerts_triggered": 0,
                    "details": []
                }
            }
        
        details = []
        alerts_triggered = 0
        online_count = 0
        offline_count = 0
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # 随机模拟一些状态变化
        for device in devices:
            device_id = device["device_id"]
            action = random.choice(["heartbeat", "heartbeat", "heartbeat", "offline", "alert"])
            
            if action == "heartbeat":
                # 模拟心跳
                latitude = round(30.0 + random.random() * 10, 6)
                longitude = round(110.0 + random.random() * 20, 6)
                location = f"模拟位置-{latitude},{longitude}"
                
                cursor.execute("""
                    UPDATE gps_devices
                    SET online_status = '在线', last_heartbeat = ?, current_location = ?, updated_at = ?
                    WHERE device_id = ?
                """, (now, location, now, device_id))
                
                online_count += 1
                details.append({"device_id": device_id, "action": "heartbeat", "online_status": "在线"})
                
            elif action == "offline":
                cursor.execute("""
                    UPDATE gps_devices SET online_status = '离线', updated_at = ?
                    WHERE device_id = ?
                """, (now, device_id))
                
                offline_count += 1
                details.append({"device_id": device_id, "action": "offline", "online_status": "离线"})
                
            elif action == "alert":
                # 产生告警
                alert_type = random.choice(list(ALERT_TYPE_NAMES.keys()))
                alert_id = generate_id("ALT")
                location = f"模拟告警位置-{random.randint(100, 999)}"
                
                cursor.execute("""
                    INSERT INTO gps_alerts (alert_id, device_id, alert_type, alert_time, location, handled, created_at)
                    VALUES (?, ?, ?, ?, ?, 0, ?)
                """, (alert_id, device_id, alert_type, now, location, now))
                
                cursor.execute("""
                    UPDATE gps_devices SET online_status = '告警中', updated_at = ?
                    WHERE device_id = ?
                """, (now, device_id))
                
                alerts_triggered += 1
                details.append({
                    "device_id": device_id,
                    "action": "alert",
                    "alert_type": alert_type,
                    "alert_id": alert_id
                })
        
        conn.commit()
        
        return {
            "success": True,
            "data": {
                "checked": len(devices),
                "online": online_count,
                "offline": offline_count,
                "alerts_triggered": alerts_triggered,
                "details": details
            }
        }
    except Exception as e:
        conn.rollback()
        return {"success": False, "message": f"轮询失败: {str(e)}"}
    finally:
        conn.close()
