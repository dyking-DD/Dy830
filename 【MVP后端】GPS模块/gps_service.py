"""
GPS 服务模块
包含数据库操作、数据模型定义和业务逻辑
"""
import sqlite3
import os
import random
from pathlib import Path
from datetime import datetime, date, timedelta
from decimal import Decimal
from typing import Optional, List, Dict, Any
from enum import Enum

from pydantic import BaseModel, Field, validator
from fastapi import HTTPException


# ==================== 数据库配置 ====================

# 数据库文件路径
DB_DIR = Path(__file__).parent / "data"
DB_DIR.mkdir(exist_ok=True)
DB_PATH = DB_DIR / "gps_management.db"


def get_db_connection():
    """获取数据库连接"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # 支持字典式访问
    conn.execute("PRAGMA foreign_keys = ON")  # 启用外键约束
    return conn


def init_database():
    """初始化数据库，创建所有表"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # ==================== 订单表（简化版，用于关联） ====================
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_no TEXT UNIQUE NOT NULL,
            customer_name TEXT NOT NULL,
            customer_phone TEXT,
            car_model TEXT,
            status TEXT DEFAULT 'pending',
            pickup_date DATE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # ==================== GPS设备表 ====================
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS gps_devices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            device_id TEXT UNIQUE NOT NULL,
            order_id INTEGER,
            imei TEXT UNIQUE NOT NULL,
            device_type TEXT NOT NULL CHECK(device_type IN ('wired', 'wireless', 'hidden')),
            install_location TEXT,
            install_staff TEXT,
            online_status TEXT DEFAULT '离线' CHECK(online_status IN ('在线', '离线', '告警中')),
            last_heartbeat TIMESTAMP,
            latitude REAL,
            longitude REAL,
            address TEXT,
            install_time TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (order_id) REFERENCES orders(id)
        )
    """)
    
    # ==================== GPS告警表 ====================
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS gps_alerts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            alert_id TEXT UNIQUE NOT NULL,
            device_id TEXT NOT NULL,
            alert_type TEXT NOT NULL CHECK(alert_type IN (
                'overspeed', 'out_of_zone', 'power_off', 
                'tamper', 'low_battery', 'sos'
            )),
            latitude REAL,
            longitude REAL,
            address TEXT,
            alert_time TIMESTAMP NOT NULL,
            handled INTEGER DEFAULT 0,
            handled_by TEXT,
            handle_time TIMESTAMP,
            handle_note TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (device_id) REFERENCES gps_devices(device_id)
        )
    """)
    
    # ==================== 设备心跳记录表（可选，用于历史追踪） ====================
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS gps_heartbeats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            device_id TEXT NOT NULL,
            latitude REAL,
            longitude REAL,
            address TEXT,
            heartbeat_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (device_id) REFERENCES gps_devices(device_id)
        )
    """)
    
    # 创建索引
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_gps_devices_status ON gps_devices(online_status)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_gps_devices_order ON gps_devices(order_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_gps_alerts_device ON gps_alerts(device_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_gps_alerts_handled ON gps_alerts(handled)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_gps_alerts_type ON gps_alerts(alert_type)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_gps_heartbeats_device ON gps_heartbeats(device_id)")
    
    conn.commit()
    conn.close()
    print(f"✅ GPS数据库初始化完成: {DB_PATH}")


# ==================== 枚举类型 ====================

class DeviceType(str, Enum):
    """设备类型"""
    WIRED = "wired"      # 有线
    WIRELESS = "wireless"  # 无线
    HIDDEN = "hidden"    # 隐蔽


class OnlineStatus(str, Enum):
    """在线状态"""
    ONLINE = "在线"
    OFFLINE = "离线"
    ALERTING = "告警中"


class AlertType(str, Enum):
    """告警类型"""
    OVERSPEED = "overspeed"        # 超速告警
    OUT_OF_ZONE = "out_of_zone"    # 出区域告警
    POWER_OFF = "power_off"        # 断电告警
    TAMPER = "tamper"              # 拆机告警
    LOW_BATTERY = "low_battery"    # 低电量告警
    SOS = "sos"                    # SOS报警


# ==================== 告警类型中文映射 ====================

ALERT_TYPE_NAMES = {
    AlertType.OVERSPEED: "超速告警",
    AlertType.OUT_OF_ZONE: "出区域告警",
    AlertType.POWER_OFF: "断电告警",
    AlertType.TAMPER: "拆机告警",
    AlertType.LOW_BATTERY: "低电量告警",
    AlertType.SOS: "SOS报警",
}

DEVICE_TYPE_NAMES = {
    DeviceType.WIRED: "有线",
    DeviceType.WIRELESS: "无线",
    DeviceType.HIDDEN: "隐蔽",
}


# ==================== Pydantic 数据模型 ====================

class LocationModel(BaseModel):
    """位置模型"""
    latitude: float = Field(..., description="纬度")
    longitude: float = Field(..., description="经度")
    address: Optional[str] = Field(None, description="地址描述")


class DeviceCreate(BaseModel):
    """注册GPS设备请求"""
    order_id: int = Field(..., description="关联订单ID")
    imei: str = Field(..., min_length=15, max_length=20, description="设备IMEI号")
    device_type: DeviceType = Field(..., description="设备类型：wired/wireless/hidden")
    install_location: str = Field(..., description="安装位置")
    install_staff: str = Field(..., description="安装人员")


class HeartbeatRequest(BaseModel):
    """设备心跳请求"""
    latitude: float = Field(..., description="当前纬度")
    longitude: float = Field(..., description="当前经度")
    address: Optional[str] = Field(None, description="地址描述")


class AlertCreate(BaseModel):
    """创建告警请求"""
    device_id: str = Field(..., description="设备ID")
    alert_type: AlertType = Field(..., description="告警类型")
    latitude: Optional[float] = Field(None, description="告警位置纬度")
    longitude: Optional[float] = Field(None, description="告警位置经度")
    address: Optional[str] = Field(None, description="告警位置地址")
    alert_time: datetime = Field(default_factory=datetime.now, description="告警时间")


class AlertHandle(BaseModel):
    """处理告警请求"""
    handled_by: str = Field(..., description="处理人")
    handle_note: Optional[str] = Field(None, description="处理备注")


class DeviceResponse(BaseModel):
    """设备响应"""
    id: int
    device_id: str
    order_id: Optional[int]
    customer_name: Optional[str]
    imei: str
    device_type: str
    device_type_name: str
    install_location: str
    install_staff: str
    online_status: str
    last_heartbeat: Optional[datetime]
    latitude: Optional[float]
    longitude: Optional[float]
    address: Optional[str]
    install_time: Optional[datetime]
    created_at: datetime

    class Config:
        from_attributes = True


class AlertResponse(BaseModel):
    """告警响应"""
    id: int
    alert_id: str
    device_id: str
    customer_name: Optional[str]
    imei: Optional[str]
    alert_type: str
    alert_type_name: str
    latitude: Optional[float]
    longitude: Optional[float]
    address: Optional[str]
    alert_time: datetime
    handled: bool
    handled_by: Optional[str]
    handle_time: Optional[datetime]
    handle_note: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class DashboardResponse(BaseModel):
    """GPS驾驶舱响应"""
    total_devices: int = Field(..., description="设备总数")
    online_count: int = Field(..., description="在线数")
    offline_count: int = Field(..., description="离线数")
    alert_count: int = Field(..., description="告警数")
    today_installed: int = Field(..., description="今日安装数")
    pending_install: int = Field(..., description="待安装数（已提车但未安装GPS）")
    recent_alerts: List[dict] = Field(..., description="最近10条未处理告警")


class PollResponse(BaseModel):
    """轮询响应"""
    checked: int = Field(..., description="检查设备数")
    online: int = Field(..., description="在线数")
    offline: int = Field(..., description="离线数")
    alerts_triggered: int = Field(..., description="触发告警数")
    details: List[dict] = Field(default_factory=list, description="详情")


# ==================== 辅助函数 ====================

def generate_device_id() -> str:
    """生成设备ID: GPS-XXXX-XXXX"""
    part1 = random.randint(1000, 9999)
    part2 = random.randint(1000, 9999)
    return f"GPS-{part1}-{part2}"


def generate_alert_id() -> str:
    """生成告警ID: ALT-YYYYMMDD-XXXX"""
    today = datetime.now().strftime("%Y%m%d")
    random_num = random.randint(1000, 9999)
    return f"ALT-{today}-{random_num}"


def row_to_dict(row: sqlite3.Row) -> dict:
    """将 sqlite3.Row 转换为字典"""
    return dict(row)


# ==================== GPS设备服务 ====================

class GPSService:
    """GPS设备服务类"""
    
    @staticmethod
    def create_device(device: DeviceCreate) -> dict:
        """
        注册GPS设备
        - 生成设备ID
        - 关联订单
        - 更新订单状态为"GPS安装中"
        """
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            # 验证订单是否存在
            cursor.execute("SELECT id, customer_name, status FROM orders WHERE id = ?", (device.order_id,))
            order_row = cursor.fetchone()
            if not order_row:
                raise HTTPException(status_code=404, detail="订单不存在")
            
            # 检查IMEI是否已存在
            cursor.execute("SELECT id FROM gps_devices WHERE imei = ?", (device.imei,))
            if cursor.fetchone():
                raise HTTPException(status_code=400, detail="该IMEI已注册")
            
            # 检查订单是否已关联GPS设备
            cursor.execute("SELECT device_id FROM gps_devices WHERE order_id = ?", (device.order_id,))
            if cursor.fetchone():
                raise HTTPException(status_code=400, detail="该订单已关联GPS设备")
            
            # 生成设备ID
            device_id = generate_device_id()
            current_time = datetime.now()
            
            # 插入设备记录
            cursor.execute("""
                INSERT INTO gps_devices (
                    device_id, order_id, imei, device_type,
                    install_location, install_staff, online_status,
                    install_time, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                device_id, device.order_id, device.imei, device.device_type.value,
                device.install_location, device.install_staff, OnlineStatus.OFFLINE.value,
                current_time, current_time, current_time
            ))
            
            # 更新订单状态为"GPS安装中"
            cursor.execute("""
                UPDATE orders SET status = 'gps_installing', updated_at = ? WHERE id = ?
            """, (current_time, device.order_id))
            
            conn.commit()
            
            # 查询创建的设备
            cursor.execute("""
                SELECT d.*, o.customer_name 
                FROM gps_devices d
                LEFT JOIN orders o ON d.order_id = o.id
                WHERE d.device_id = ?
            """, (device_id,))
            
            device_row = cursor.fetchone()
            result = row_to_dict(device_row)
            result["device_type_name"] = DEVICE_TYPE_NAMES.get(
                DeviceType(result["device_type"]), result["device_type"]
            )
            
            return result
            
        except HTTPException:
            raise
        except Exception as e:
            conn.rollback()
            raise HTTPException(status_code=500, detail=f"注册GPS设备失败: {str(e)}")
        finally:
            conn.close()
    
    @staticmethod
    def list_devices(
        page: int = 1,
        page_size: int = 20,
        status: Optional[str] = None
    ) -> dict:
        """获取设备列表（支持分页和状态筛选）"""
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            # 构建查询条件
            where_clauses = []
            params = []
            
            if status:
                where_clauses.append("d.online_status = ?")
                params.append(status)
            
            where_sql = " AND ".join(where_clauses) if where_clauses else "1=1"
            
            # 查询总数
            count_sql = f"""
                SELECT COUNT(*) as total 
                FROM gps_devices d
                WHERE {where_sql}
            """
            cursor.execute(count_sql, params)
            total = cursor.fetchone()["total"]
            
            # 分页查询
            offset = (page - 1) * page_size
            query_sql = f"""
                SELECT d.*, o.customer_name 
                FROM gps_devices d
                LEFT JOIN orders o ON d.order_id = o.id
                WHERE {where_sql}
                ORDER BY d.created_at DESC
                LIMIT ? OFFSET ?
            """
            cursor.execute(query_sql, params + [page_size, offset])
            
            devices = []
            for row in cursor.fetchall():
                device_dict = row_to_dict(row)
                device_dict["device_type_name"] = DEVICE_TYPE_NAMES.get(
                    DeviceType(device_dict["device_type"]), device_dict["device_type"]
                )
                devices.append(device_dict)
            
            return {
                "total": total,
                "page": page,
                "page_size": page_size,
                "devices": devices
            }
            
        finally:
            conn.close()
    
    @staticmethod
    def get_device_detail(device_id: str) -> dict:
        """获取设备详情"""
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                SELECT d.*, o.customer_name, o.order_no, o.car_model
                FROM gps_devices d
                LEFT JOIN orders o ON d.order_id = o.id
                WHERE d.device_id = ?
            """, (device_id,))
            
            row = cursor.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="设备不存在")
            
            result = row_to_dict(row)
            result["device_type_name"] = DEVICE_TYPE_NAMES.get(
                DeviceType(result["device_type"]), result["device_type"]
            )
            
            return result
            
        finally:
            conn.close()
    
    @staticmethod
    def get_device_location(device_id: str) -> dict:
        """获取设备最新位置（模拟）"""
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                SELECT device_id, latitude, longitude, address, last_heartbeat
                FROM gps_devices
                WHERE device_id = ?
            """, (device_id,))
            
            row = cursor.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="设备不存在")
            
            result = row_to_dict(row)
            
            # 如果没有位置数据，模拟一个位置
            if result["latitude"] is None:
                # 模拟中国境内的随机位置
                result["latitude"] = round(30.0 + random.random() * 10, 6)
                result["longitude"] = round(110.0 + random.random() * 20, 6)
                result["address"] = "模拟位置 - 测试数据"
            
            return result
            
        finally:
            conn.close()
    
    @staticmethod
    def device_heartbeat(device_id: str, heartbeat: HeartbeatRequest) -> dict:
        """
        设备心跳
        - 更新在线状态
        - 更新最后心跳时间
        - 更新位置
        """
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            # 检查设备是否存在
            cursor.execute("SELECT device_id FROM gps_devices WHERE device_id = ?", (device_id,))
            if not cursor.fetchone():
                raise HTTPException(status_code=404, detail="设备不存在")
            
            current_time = datetime.now()
            
            # 更新设备状态
            cursor.execute("""
                UPDATE gps_devices
                SET online_status = ?, last_heartbeat = ?,
                    latitude = ?, longitude = ?, address = ?,
                    updated_at = ?
                WHERE device_id = ?
            """, (
                OnlineStatus.ONLINE.value, current_time,
                heartbeat.latitude, heartbeat.longitude, heartbeat.address,
                current_time, device_id
            ))
            
            # 记录心跳历史
            cursor.execute("""
                INSERT INTO gps_heartbeats (device_id, latitude, longitude, address, heartbeat_time)
                VALUES (?, ?, ?, ?, ?)
            """, (device_id, heartbeat.latitude, heartbeat.longitude, heartbeat.address, current_time))
            
            conn.commit()
            
            return {
                "device_id": device_id,
                "online_status": OnlineStatus.ONLINE.value,
                "last_heartbeat": current_time.isoformat(),
                "location": {
                    "latitude": heartbeat.latitude,
                    "longitude": heartbeat.longitude,
                    "address": heartbeat.address
                }
            }
            
        except HTTPException:
            raise
        except Exception as e:
            conn.rollback()
            raise HTTPException(status_code=500, detail=f"心跳更新失败: {str(e)}")
        finally:
            conn.close()
    
    @staticmethod
    def mark_device_offline(device_id: str) -> dict:
        """标记设备离线"""
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("SELECT device_id FROM gps_devices WHERE device_id = ?", (device_id,))
            if not cursor.fetchone():
                raise HTTPException(status_code=404, detail="设备不存在")
            
            current_time = datetime.now()
            
            cursor.execute("""
                UPDATE gps_devices
                SET online_status = ?, updated_at = ?
                WHERE device_id = ?
            """, (OnlineStatus.OFFLINE.value, current_time, device_id))
            
            conn.commit()
            
            return {
                "device_id": device_id,
                "online_status": OnlineStatus.OFFLINE.value,
                "updated_at": current_time.isoformat()
            }
            
        except HTTPException:
            raise
        except Exception as e:
            conn.rollback()
            raise HTTPException(status_code=500, detail=f"标记离线失败: {str(e)}")
        finally:
            conn.close()
    
    @staticmethod
    def check_offline_devices() -> int:
        """
        检查超过5分钟无心跳的设备，自动标记为离线
        返回标记的设备数量
        """
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            # 计算5分钟前的时间
            threshold = datetime.now() - timedelta(minutes=5)
            
            # 查找在线但超时无心跳的设备
            cursor.execute("""
                SELECT device_id FROM gps_devices
                WHERE online_status = ?
                  AND (last_heartbeat IS NULL OR last_heartbeat < ?)
            """, (OnlineStatus.ONLINE.value, threshold))
            
            offline_devices = cursor.fetchall()
            
            if not offline_devices:
                return 0
            
            # 批量更新为离线
            current_time = datetime.now()
            for device in offline_devices:
                cursor.execute("""
                    UPDATE gps_devices
                    SET online_status = ?, updated_at = ?
                    WHERE device_id = ?
                """, (OnlineStatus.OFFLINE.value, current_time, device["device_id"]))
            
            conn.commit()
            
            return len(offline_devices)
            
        except Exception as e:
            conn.rollback()
            raise Exception(f"检查离线设备失败: {str(e)}")
        finally:
            conn.close()


# ==================== GPS告警服务 ====================

class GPSAlertService:
    """GPS告警服务类"""
    
    @staticmethod
    def create_alert(alert: AlertCreate) -> dict:
        """
        创建告警
        - 生成告警ID
        - 更新设备状态为"告警中"
        """
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            # 检查设备是否存在
            cursor.execute("""
                SELECT d.device_id, d.imei, o.customer_name
                FROM gps_devices d
                LEFT JOIN orders o ON d.order_id = o.id
                WHERE d.device_id = ?
            """, (alert.device_id,))
            
            device_row = cursor.fetchone()
            if not device_row:
                raise HTTPException(status_code=404, detail="设备不存在")
            
            # 生成告警ID
            alert_id = generate_alert_id()
            current_time = datetime.now()
            
            # 插入告警记录
            cursor.execute("""
                INSERT INTO gps_alerts (
                    alert_id, device_id, alert_type,
                    latitude, longitude, address, alert_time,
                    handled, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, 0, ?)
            """, (
                alert_id, alert.device_id, alert.alert_type.value,
                alert.latitude, alert.longitude, alert.address, alert.alert_time,
                current_time
            ))
            
            # 更新设备状态为"告警中"
            cursor.execute("""
                UPDATE gps_devices
                SET online_status = ?, updated_at = ?
                WHERE device_id = ?
            """, (OnlineStatus.ALERTING.value, current_time, alert.device_id))
            
            conn.commit()
            
            # 返回创建的告警
            result = {
                "alert_id": alert_id,
                "device_id": alert.device_id,
                "imei": device_row["imei"],
                "customer_name": device_row["customer_name"],
                "alert_type": alert.alert_type.value,
                "alert_type_name": ALERT_TYPE_NAMES.get(alert.alert_type, alert.alert_type.value),
                "latitude": alert.latitude,
                "longitude": alert.longitude,
                "address": alert.address,
                "alert_time": alert.alert_time.isoformat(),
                "handled": False
            }
            
            return result
            
        except HTTPException:
            raise
        except Exception as e:
            conn.rollback()
            raise HTTPException(status_code=500, detail=f"创建告警失败: {str(e)}")
        finally:
            conn.close()
    
    @staticmethod
    def list_alerts(
        page: int = 1,
        page_size: int = 20,
        handled: Optional[bool] = None,
        alert_type: Optional[str] = None
    ) -> dict:
        """获取告警列表"""
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            # 构建查询条件
            where_clauses = []
            params = []
            
            if handled is not None:
                where_clauses.append("a.handled = ?")
                params.append(1 if handled else 0)
            
            if alert_type:
                where_clauses.append("a.alert_type = ?")
                params.append(alert_type)
            
            where_sql = " AND ".join(where_clauses) if where_clauses else "1=1"
            
            # 查询总数
            count_sql = f"""
                SELECT COUNT(*) as total 
                FROM gps_alerts a
                WHERE {where_sql}
            """
            cursor.execute(count_sql, params)
            total = cursor.fetchone()["total"]
            
            # 分页查询
            offset = (page - 1) * page_size
            query_sql = f"""
                SELECT a.*, d.imei, o.customer_name
                FROM gps_alerts a
                LEFT JOIN gps_devices d ON a.device_id = d.device_id
                LEFT JOIN orders o ON d.order_id = o.id
                WHERE {where_sql}
                ORDER BY a.alert_time DESC
                LIMIT ? OFFSET ?
            """
            cursor.execute(query_sql, params + [page_size, offset])
            
            alerts = []
            for row in cursor.fetchall():
                alert_dict = row_to_dict(row)
                alert_dict["alert_type_name"] = ALERT_TYPE_NAMES.get(
                    AlertType(alert_dict["alert_type"]), alert_dict["alert_type"]
                )
                alert_dict["handled"] = bool(alert_dict["handled"])
                alerts.append(alert_dict)
            
            return {
                "total": total,
                "page": page,
                "page_size": page_size,
                "alerts": alerts
            }
            
        finally:
            conn.close()
    
    @staticmethod
    def handle_alert(alert_id: str, handle: AlertHandle) -> dict:
        """
        处理告警
        - 标记为已处理
        - 如果设备无其他未处理告警，恢复为"在线"状态
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
            
            alert_row = cursor.fetchone()
            if not alert_row:
                raise HTTPException(status_code=404, detail="告警不存在")
            
            if alert_row["handled"]:
                raise HTTPException(status_code=400, detail="该告警已处理")
            
            current_time = datetime.now()
            
            # 更新告警状态
            cursor.execute("""
                UPDATE gps_alerts
                SET handled = 1, handled_by = ?, handle_time = ?, handle_note = ?
                WHERE alert_id = ?
            """, (handle.handled_by, current_time, handle.handle_note, alert_id))
            
            # 检查该设备是否还有其他未处理告警
            cursor.execute("""
                SELECT COUNT(*) as count
                FROM gps_alerts
                WHERE device_id = ? AND handled = 0
            """, (alert_row["device_id"],))
            
            unhandled_count = cursor.fetchone()["count"]
            
            # 如果没有其他未处理告警，恢复设备状态为"在线"
            if unhandled_count == 0:
                cursor.execute("""
                    UPDATE gps_devices
                    SET online_status = ?, updated_at = ?
                    WHERE device_id = ?
                """, (OnlineStatus.ONLINE.value, current_time, alert_row["device_id"]))
            
            conn.commit()
            
            # 返回处理结果
            cursor.execute("""
                SELECT a.*, d.imei, o.customer_name
                FROM gps_alerts a
                LEFT JOIN gps_devices d ON a.device_id = d.device_id
                LEFT JOIN orders o ON d.order_id = o.id
                WHERE a.alert_id = ?
            """, (alert_id,))
            
            updated_row = cursor.fetchone()
            result = row_to_dict(updated_row)
            result["alert_type_name"] = ALERT_TYPE_NAMES.get(
                AlertType(result["alert_type"]), result["alert_type"]
            )
            result["handled"] = bool(result["handled"])
            
            return result
            
        except HTTPException:
            raise
        except Exception as e:
            conn.rollback()
            raise HTTPException(status_code=500, detail=f"处理告警失败: {str(e)}")
        finally:
            conn.close()


# ==================== GPS驾驶舱服务 ====================

class GPSDashboardService:
    """GPS驾驶舱服务"""
    
    @staticmethod
    def get_dashboard() -> dict:
        """获取GPS监控驾驶舱数据"""
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            today = date.today()
            
            # 设备总数
            cursor.execute("SELECT COUNT(*) as count FROM gps_devices")
            total_devices = cursor.fetchone()["count"]
            
            # 在线数
            cursor.execute("""
                SELECT COUNT(*) as count FROM gps_devices WHERE online_status = ?
            """, (OnlineStatus.ONLINE.value,))
            online_count = cursor.fetchone()["count"]
            
            # 离线数
            cursor.execute("""
                SELECT COUNT(*) as count FROM gps_devices WHERE online_status = ?
            """, (OnlineStatus.OFFLINE.value,))
            offline_count = cursor.fetchone()["count"]
            
            # 告警数
            cursor.execute("""
                SELECT COUNT(*) as count FROM gps_devices WHERE online_status = ?
            """, (OnlineStatus.ALERTING.value,))
            alert_count = cursor.fetchone()["count"]
            
            # 今日安装数
            cursor.execute("""
                SELECT COUNT(*) as count FROM gps_devices
                WHERE DATE(install_time) = ?
            """, (today,))
            today_installed = cursor.fetchone()["count"]
            
            # 待安装数（已提车但未安装GPS的订单数）
            cursor.execute("""
                SELECT COUNT(*) as count FROM orders o
                WHERE o.status = 'picked_up' 
                   OR (o.pickup_date IS NOT NULL 
                       AND o.pickup_date <= ?
                       AND NOT EXISTS (
                           SELECT 1 FROM gps_devices d WHERE d.order_id = o.id
                       ))
            """, (today,))
            pending_install = cursor.fetchone()["count"]
            
            # 最近10条未处理告警
            cursor.execute("""
                SELECT a.*, d.imei, o.customer_name
                FROM gps_alerts a
                LEFT JOIN gps_devices d ON a.device_id = d.device_id
                LEFT JOIN orders o ON d.order_id = o.id
                WHERE a.handled = 0
                ORDER BY a.alert_time DESC
                LIMIT 10
            """)
            
            recent_alerts = []
            for row in cursor.fetchall():
                alert_dict = row_to_dict(row)
                alert_dict["alert_type_name"] = ALERT_TYPE_NAMES.get(
                    AlertType(alert_dict["alert_type"]), alert_dict["alert_type"]
                )
                alert_dict["handled"] = bool(alert_dict["handled"])
                recent_alerts.append(alert_dict)
            
            return {
                "total_devices": total_devices,
                "online_count": online_count,
                "offline_count": offline_count,
                "alert_count": alert_count,
                "today_installed": today_installed,
                "pending_install": pending_install,
                "recent_alerts": recent_alerts
            }
            
        finally:
            conn.close()


# ==================== GPS轮询模拟服务 ====================

class GPSPollService:
    """GPS轮询模拟服务"""
    
    @staticmethod
    def poll_devices() -> dict:
        """
        模拟轮询所有设备
        - 随机模拟设备状态变化
        - 随机产生告警
        """
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            current_time = datetime.now()
            
            # 获取所有设备
            cursor.execute("SELECT device_id, online_status FROM gps_devices")
            devices = cursor.fetchall()
            
            if not devices:
                return {
                    "checked": 0,
                    "online": 0,
                    "offline": 0,
                    "alerts_triggered": 0,
                    "details": []
                }
            
            details = []
            alerts_triggered = 0
            online_count = 0
            offline_count = 0
            
            # 随机选择1-2个设备产生告警
            alert_devices = random.sample(
                devices, 
                min(random.randint(1, 2), len(devices))
            ) if devices else []
            
            for device in devices:
                device_id = device["device_id"]
                current_status = device["online_status"]
                
                # 随机决定状态变化
                action = random.choice(["heartbeat", "heartbeat", "heartbeat", "offline", "alert"])
                
                if device in alert_devices and action == "alert":
                    # 产生告警
                    alert_type = random.choice(list(AlertType))
                    alert_id = generate_alert_id()
                    
                    # 模拟位置
                    latitude = round(30.0 + random.random() * 10, 6)
                    longitude = round(110.0 + random.random() * 20, 6)
                    
                    # 插入告警
                    cursor.execute("""
                        INSERT INTO gps_alerts (
                            alert_id, device_id, alert_type,
                            latitude, longitude, address, alert_time,
                            handled, created_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, 0, ?)
                    """, (
                        alert_id, device_id, alert_type.value,
                        latitude, longitude, "模拟告警位置", current_time, current_time
                    ))
                    
                    # 更新设备状态
                    cursor.execute("""
                        UPDATE gps_devices
                        SET online_status = ?, updated_at = ?
                        WHERE device_id = ?
                    """, (OnlineStatus.ALERTING.value, current_time, device_id))
                    
                    alerts_triggered += 1
                    details.append({
                        "device_id": device_id,
                        "action": "alert",
                        "alert_type": alert_type.value,
                        "alert_id": alert_id
                    })
                    
                elif action == "heartbeat":
                    # 模拟心跳，更新为在线
                    latitude = round(30.0 + random.random() * 10, 6)
                    longitude = round(110.0 + random.random() * 20, 6)
                    
                    cursor.execute("""
                        UPDATE gps_devices
                        SET online_status = ?, last_heartbeat = ?,
                            latitude = ?, longitude = ?, updated_at = ?
                        WHERE device_id = ?
                    """, (OnlineStatus.ONLINE.value, current_time, latitude, longitude, current_time, device_id))
                    
                    online_count += 1
                    details.append({
                        "device_id": device_id,
                        "action": "heartbeat",
                        "online_status": OnlineStatus.ONLINE.value
                    })
                    
                elif action == "offline":
                    # 标记离线
                    cursor.execute("""
                        UPDATE gps_devices
                        SET online_status = ?, updated_at = ?
                        WHERE device_id = ?
                    """, (OnlineStatus.OFFLINE.value, current_time, device_id))
                    
                    offline_count += 1
                    details.append({
                        "device_id": device_id,
                        "action": "offline",
                        "online_status": OnlineStatus.OFFLINE.value
                    })
                
                else:
                    # 保持当前状态
                    if current_status == OnlineStatus.ONLINE.value:
                        online_count += 1
                    elif current_status == OnlineStatus.OFFLINE.value:
                        offline_count += 1
            
            conn.commit()
            
            return {
                "checked": len(devices),
                "online": online_count,
                "offline": offline_count,
                "alerts_triggered": alerts_triggered,
                "details": details
            }
            
        except Exception as e:
            conn.rollback()
            raise HTTPException(status_code=500, detail=f"轮询失败: {str(e)}")
        finally:
            conn.close()


# 在模块导入时初始化数据库
init_database()
