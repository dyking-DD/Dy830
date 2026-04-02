"""
业务逻辑层
"""
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from dateutil.relativedelta import relativedelta
import database as db

# ==================== 订单状态流转规则 ====================

# 定义订单阶段流转规则（阶段: 允许的下一阶段列表）
STAGE_TRANSITIONS = {
    "已接单": ["垫资预审", "银行审批中"],
    "垫资预审": ["垫资审批中"],
    "垫资审批中": ["垫资通过", "垫资已出账"],
    "垫资通过": ["垫资已出账"],
    "垫资已出账": ["垫资已还清", "银行审批中"],
    "垫资已还清": ["银行审批中"],
    "银行审批中": ["审批通过", "审批拒绝"],
    "审批通过": ["放款通知"],
    "审批拒绝": ["已接单"],  # 重新开始
    "放款通知": ["待提车"],
    "待提车": ["已提车"],
    "已提车": ["GPS安装中"],
    "GPS安装中": ["GPS已在线"],
    "GPS已在线": ["资料归档中"],
    "资料归档中": ["归档完成"],
    "归档完成": ["抵押登记中"],
    "抵押登记中": ["已抵押"],
    "已抵押": ["正常还款中"],
    "正常还款中": ["逾期", "已结清"],
    "逾期": ["正常还款中", "已结清"],
    "已结清": ["已完结"],
    "已完结": []  # 终态
}

def can_transition_to(current_stage: str, new_stage: str) -> bool:
    """检查是否可以从当前阶段流转到新阶段"""
    allowed_next_stages = STAGE_TRANSITIONS.get(current_stage, [])
    return new_stage in allowed_next_stages

# ==================== 订单管理服务 ====================

class OrderService:
    """订单管理服务"""
    
    @staticmethod
    def create_order(order_data: dict) -> dict:
        """创建订单"""
        conn = db.get_db_connection()
        cursor = conn.cursor()
        
        order_id = db.generate_id("ORD")
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        cursor.execute("""
            INSERT INTO orders (
                order_id, customer_name, customer_phone, customer_id_number,
                car_brand, car_model, car_vin, car_plate_number, car_price,
                stage, loan_amount, down_payment, loan_period, monthly_payment,
                interest_rate, bank_name, created_by, created_at, stage_updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            order_id, order_data.get("customer_name"), order_data.get("customer_phone"),
            order_data.get("customer_id_number"), order_data.get("car_brand"),
            order_data.get("car_model"), order_data.get("car_vin"),
            order_data.get("car_plate_number"), order_data.get("car_price"),
            "已接单", order_data.get("loan_amount"), order_data.get("down_payment"),
            order_data.get("loan_period"), order_data.get("monthly_payment"),
            order_data.get("interest_rate"), order_data.get("bank_name"),
            order_data.get("created_by"), now, now
        ))
        
        conn.commit()
        conn.close()
        
        return {"order_id": order_id, "created_at": now}
    
    @staticmethod
    def get_orders_list(
        page: int = 1,
        page_size: int = 20,
        stage: Optional[str] = None,
        keyword: Optional[str] = None,
        date_start: Optional[str] = None,
        date_end: Optional[str] = None
    ) -> dict:
        """获取订单列表（支持分页、筛选、搜索）"""
        conn = db.get_db_connection()
        cursor = conn.cursor()
        
        # 构建查询条件
        conditions = []
        params = []
        
        if stage:
            conditions.append("stage = ?")
            params.append(stage)
        
        if keyword:
            conditions.append("(order_id LIKE ? OR customer_name LIKE ? OR car_plate_number LIKE ?)")
            keyword_pattern = f"%{keyword}%"
            params.extend([keyword_pattern, keyword_pattern, keyword_pattern])
        
        if date_start:
            conditions.append("created_at >= ?")
            params.append(date_start)
        
        if date_end:
            conditions.append("created_at <= ?")
            params.append(date_end + " 23:59:59")
        
        where_clause = " AND ".join(conditions) if conditions else "1=1"
        
        # 查询总数
        count_sql = f"SELECT COUNT(*) as total FROM orders WHERE {where_clause}"
        cursor.execute(count_sql, params)
        total = cursor.fetchone()["total"]
        
        # 查询列表
        offset = (page - 1) * page_size
        list_sql = f"""
            SELECT order_id, customer_name, customer_phone, car_brand, car_model,
                   loan_amount, stage, created_at
            FROM orders
            WHERE {where_clause}
            ORDER BY created_at DESC
            LIMIT ? OFFSET ?
        """
        params.extend([page_size, offset])
        cursor.execute(list_sql, params)
        rows = cursor.fetchall()
        
        orders = [dict(row) for row in rows]
        conn.close()
        
        return {
            "total": total,
            "page": page,
            "page_size": page_size,
            "items": orders
        }
    
    @staticmethod
    def get_order_detail(order_id: str) -> Optional[dict]:
        """获取订单详情"""
        conn = db.get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM orders WHERE order_id = ?
        """, (order_id,))
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return dict(row)
        return None
    
    @staticmethod
    def update_order_stage(order_id: str, new_stage: str, remark: Optional[str] = None) -> dict:
        """更新订单阶段"""
        # 先获取当前订单信息
        order = OrderService.get_order_detail(order_id)
        if not order:
            return {"success": False, "message": "订单不存在"}
        
        current_stage = order["stage"]
        
        # 检查状态流转是否合法
        if not can_transition_to(current_stage, new_stage):
            return {
                "success": False,
                "message": f"不允许从【{current_stage}】直接流转到【{new_stage}】"
            }
        
        # 更新订单阶段
        conn = db.get_db_connection()
        cursor = conn.cursor()
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        cursor.execute("""
            UPDATE orders
            SET stage = ?, stage_remark = ?, stage_updated_at = ?
            WHERE order_id = ?
        """, (new_stage, remark, now, order_id))
        
        conn.commit()
        conn.close()
        
        return {
            "success": True,
            "message": "订单阶段更新成功",
            "order_id": order_id,
            "old_stage": current_stage,
            "new_stage": new_stage,
            "updated_at": now
        }

# ==================== 还款管理服务 ====================

class RepaymentService:
    """还款管理服务"""
    
    @staticmethod
    def generate_repayment_plans(
        order_id: str,
        loan_amount: float,
        loan_period: int,
        start_date: str,
        monthly_payment: float
    ) -> dict:
        """生成还款计划"""
        conn = db.get_db_connection()
        cursor = conn.cursor()
        
        # 获取订单客户名
        cursor.execute("SELECT customer_name FROM orders WHERE order_id = ?", (order_id,))
        order_row = cursor.fetchone()
        if not order_row:
            conn.close()
            return {"success": False, "message": "订单不存在"}
        
        customer_name = order_row["customer_name"]
        plans = []
        start_dt = datetime.strptime(start_date, "%Y-%m-%d")
        
        for i in range(loan_period):
            plan_id = db.generate_id("RPP")
            # 计算每月还款日
            due_date = start_dt + relativedelta(months=i)
            
            cursor.execute("""
                INSERT INTO repayment_plans (
                    plan_id, order_id, period_number, due_date, due_amount, status, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                plan_id, order_id, i + 1, due_date.strftime("%Y-%m-%d"),
                monthly_payment, "正常", datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            ))
            
            plans.append({
                "plan_id": plan_id,
                "period_number": i + 1,
                "due_date": due_date.strftime("%Y-%m-%d"),
                "due_amount": monthly_payment
            })
        
        conn.commit()
        conn.close()
        
        return {
            "success": True,
            "message": f"成功生成{loan_period}期还款计划",
            "customer_name": customer_name,
            "plans": plans
        }
    
    @staticmethod
    def get_repayment_plans(
        order_id: Optional[str] = None,
        status: Optional[str] = None,
        page: int = 1,
        page_size: int = 20
    ) -> dict:
        """获取还款计划列表"""
        conn = db.get_db_connection()
        cursor = conn.cursor()
        
        # 构建查询条件
        conditions = []
        params = []
        
        if order_id:
            conditions.append("rp.order_id = ?")
            params.append(order_id)
        
        if status:
            conditions.append("rp.status = ?")
            params.append(status)
        
        where_clause = " AND ".join(conditions) if conditions else "1=1"
        
        # 查询总数
        count_sql = f"""
            SELECT COUNT(*) as total
            FROM repayment_plans rp
            WHERE {where_clause}
        """
        cursor.execute(count_sql, params)
        total = cursor.fetchone()["total"]
        
        # 查询列表
        offset = (page - 1) * page_size
        list_sql = f"""
            SELECT rp.plan_id, rp.order_id, o.customer_name, rp.period_number,
                   rp.due_date, rp.due_amount, rp.actual_date, rp.actual_amount,
                   rp.status, rp.overdue_days
            FROM repayment_plans rp
            LEFT JOIN orders o ON rp.order_id = o.order_id
            WHERE {where_clause}
            ORDER BY rp.due_date DESC
            LIMIT ? OFFSET ?
        """
        params.extend([page_size, offset])
        cursor.execute(list_sql, params)
        rows = cursor.fetchall()
        
        plans = [dict(row) for row in rows]
        conn.close()
        
        return {
            "total": total,
            "page": page,
            "page_size": page_size,
            "items": plans
        }
    
    @staticmethod
    def get_repayment_plan_detail(plan_id: str) -> Optional[dict]:
        """获取还款计划详情"""
        conn = db.get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT rp.*, o.customer_name, o.customer_phone, o.car_brand, o.car_model
            FROM repayment_plans rp
            LEFT JOIN orders o ON rp.order_id = o.order_id
            WHERE rp.plan_id = ?
        """, (plan_id,))
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return dict(row)
        return None
    
    @staticmethod
    def create_repayment_record(record_data: dict) -> dict:
        """录入还款记录"""
        conn = db.get_db_connection()
        cursor = conn.cursor()
        
        plan_id = record_data.get("plan_id")
        
        # 获取还款计划信息
        cursor.execute("SELECT * FROM repayment_plans WHERE plan_id = ?", (plan_id,))
        plan = cursor.fetchone()
        if not plan:
            conn.close()
            return {"success": False, "message": "还款计划不存在"}
        
        plan_dict = dict(plan)
        order_id = plan_dict["order_id"]
        due_date = plan_dict["due_date"]
        due_amount = plan_dict["due_amount"]
        
        # 计算是否逾期
        repayment_date = record_data.get("repayment_date")
        due_dt = datetime.strptime(due_date, "%Y-%m-%d")
        repayment_dt = datetime.strptime(repayment_date, "%Y-%m-%d")
        
        is_overdue = repayment_dt > due_dt
        overdue_days = (repayment_dt - due_dt).days if is_overdue else 0
        
        # 生成还款记录
        record_id = db.generate_id("RPR")
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        cursor.execute("""
            INSERT INTO repayment_records (
                record_id, plan_id, order_id, actual_amount, repayment_date,
                payment_method, remark, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            record_id, plan_id, order_id, record_data.get("actual_amount"),
            repayment_date, record_data.get("payment_method"),
            record_data.get("remark"), now
        ))
        
        # 更新还款计划状态
        new_status = "逾期" if is_overdue else "已还清"
        cursor.execute("""
            UPDATE repayment_plans
            SET actual_date = ?, actual_amount = ?, status = ?, overdue_days = ?
            WHERE plan_id = ?
        """, (repayment_date, record_data.get("actual_amount"), new_status, overdue_days, plan_id))
        
        # 检查是否所有期数都已还清
        cursor.execute("""
            SELECT COUNT(*) as total, 
                   SUM(CASE WHEN status = '已还清' THEN 1 ELSE 0 END) as repaid
            FROM repayment_plans
            WHERE order_id = ?
        """, (order_id,))
        
        stats = cursor.fetchone()
        if stats["total"] == stats["repaid"]:
            # 更新订单状态为"已结清"
            cursor.execute("""
                UPDATE orders SET stage = '已结清', stage_updated_at = ?
                WHERE order_id = ?
            """, (now, order_id))
        
        conn.commit()
        conn.close()
        
        return {
            "success": True,
            "message": "还款记录录入成功",
            "record_id": record_id,
            "overdue_days": overdue_days
        }
    
    @staticmethod
    def get_repayment_records(
        order_id: Optional[str] = None,
        date_start: Optional[str] = None,
        date_end: Optional[str] = None,
        page: int = 1,
        page_size: int = 20
    ) -> dict:
        """获取还款记录列表"""
        conn = db.get_db_connection()
        cursor = conn.cursor()
        
        # 构建查询条件
        conditions = []
        params = []
        
        if order_id:
            conditions.append("rr.order_id = ?")
            params.append(order_id)
        
        if date_start:
            conditions.append("rr.repayment_date >= ?")
            params.append(date_start)
        
        if date_end:
            conditions.append("rr.repayment_date <= ?")
            params.append(date_end)
        
        where_clause = " AND ".join(conditions) if conditions else "1=1"
        
        # 查询总数
        count_sql = f"""
            SELECT COUNT(*) as total
            FROM repayment_records rr
            WHERE {where_clause}
        """
        cursor.execute(count_sql, params)
        total = cursor.fetchone()["total"]
        
        # 查询列表
        offset = (page - 1) * page_size
        list_sql = f"""
            SELECT rr.*, o.customer_name
            FROM repayment_records rr
            LEFT JOIN orders o ON rr.order_id = o.order_id
            WHERE {where_clause}
            ORDER BY rr.repayment_date DESC
            LIMIT ? OFFSET ?
        """
        params.extend([page_size, offset])
        cursor.execute(list_sql, params)
        rows = cursor.fetchall()
        
        records = [dict(row) for row in rows]
        conn.close()
        
        return {
            "total": total,
            "page": page,
            "page_size": page_size,
            "items": records
        }
    
    @staticmethod
    def check_overdue() -> dict:
        """检测逾期还款计划"""
        conn = db.get_db_connection()
        cursor = conn.cursor()
        today = datetime.now().strftime("%Y-%m-%d")
        
        # 查找所有应还日期<今天且status=正常的计划
        cursor.execute("""
            SELECT plan_id, due_amount
            FROM repayment_plans
            WHERE due_date < ? AND status = '正常'
        """, (today,))
        
        overdue_plans = cursor.fetchall()
        overdue_ids = []
        overdue_amount = 0
        
        for plan in overdue_plans:
            plan_dict = dict(plan)
            overdue_ids.append(plan_dict["plan_id"])
            overdue_amount += plan_dict["due_amount"]
            
            # 计算逾期天数
            due_dt = datetime.strptime(plan_dict["due_date"], "%Y-%m-%d")
            today_dt = datetime.strptime(today, "%Y-%m-%d")
            overdue_days = (today_dt - due_dt).days
            
            # 更新状态为逾期
            cursor.execute("""
                UPDATE repayment_plans
                SET status = '逾期', overdue_days = ?
                WHERE plan_id = ?
            """, (overdue_days, plan_dict["plan_id"]))
        
        conn.commit()
        conn.close()
        
        return {
            "overdue_count": len(overdue_ids),
            "overdue_plan_ids": overdue_ids,
            "overdue_amount": overdue_amount
        }
    
    @staticmethod
    def get_repayment_stats() -> dict:
        """获取还款统计"""
        conn = db.get_db_connection()
        cursor = conn.cursor()
        
        today = datetime.now().strftime("%Y-%m-%d")
        month_start = datetime.now().replace(day=1).strftime("%Y-%m-%d")
        month_end = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")
        
        # 今日待还总额
        cursor.execute("""
            SELECT COALESCE(SUM(due_amount), 0) as total
            FROM repayment_plans
            WHERE due_date = ? AND status = '正常'
        """, (today,))
        today_repayment = cursor.fetchone()["total"]
        
        # 本月待还总额
        cursor.execute("""
            SELECT COALESCE(SUM(due_amount), 0) as total
            FROM repayment_plans
            WHERE due_date >= ? AND due_date <= ? AND status = '正常'
        """, (month_start, month_end))
        month_repayment = cursor.fetchone()["total"]
        
        # 本月实际已还总额
        cursor.execute("""
            SELECT COALESCE(SUM(actual_amount), 0) as total
            FROM repayment_records
            WHERE repayment_date >= ?
        """, (month_start,))
        today_actual = cursor.fetchone()["total"]
        
        # 逾期统计
        cursor.execute("""
            SELECT COUNT(*) as count, COALESCE(SUM(due_amount), 0) as amount
            FROM repayment_plans
            WHERE status = '逾期'
        """)
        overdue_stats = cursor.fetchone()
        overdue_count = overdue_stats["count"]
        overdue_amount = overdue_stats["amount"]
        
        # 逾期3天内笔数
        cursor.execute("""
            SELECT COUNT(*) as count
            FROM repayment_plans
            WHERE status = '逾期' AND overdue_days <= 3
        """)
        overdue_3d_count = cursor.fetchone()["count"]
        
        # 逾期7天内笔数
        cursor.execute("""
            SELECT COUNT(*) as count
            FROM repayment_plans
            WHERE status = '逾期' AND overdue_days <= 7
        """)
        overdue_7d_count = cursor.fetchone()["count"]
        
        # 正常笔数
        cursor.execute("""
            SELECT COUNT(*) as count
            FROM repayment_plans
            WHERE status = '正常'
        """)
        normal_count = cursor.fetchone()["count"]
        
        conn.close()
        
        return {
            "today_repayment": today_repayment,
            "month_repayment": month_repayment,
            "today_actual": today_actual,
            "overdue_count": overdue_count,
            "overdue_amount": overdue_amount,
            "overdue_3d_count": overdue_3d_count,
            "overdue_7d_count": overdue_7d_count,
            "normal_count": normal_count
        }

# ==================== 抵押管理服务 ====================

class MortgageService:
    """抵押管理服务"""
    
    @staticmethod
    def create_mortgage(mortgage_data: dict) -> dict:
        """创建抵押登记"""
        conn = db.get_db_connection()
        cursor = conn.cursor()
        
        mortgage_id = db.generate_id("MTG")
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        cursor.execute("""
            INSERT INTO mortgage (
                mortgage_id, order_id, mortgage_bank, register_date,
                expire_date, certificate_number, status, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            mortgage_id, mortgage_data.get("order_id"),
            mortgage_data.get("mortgage_bank"), mortgage_data.get("register_date"),
            mortgage_data.get("expire_date"), mortgage_data.get("certificate_number"),
            "抵押中", now
        ))
        
        conn.commit()
        conn.close()
        
        return {
            "mortgage_id": mortgage_id,
            "created_at": now
        }
    
    @staticmethod
    def get_mortgages(
        order_id: Optional[str] = None,
        status: Optional[str] = None
    ) -> List[dict]:
        """获取抵押列表"""
        conn = db.get_db_connection()
        cursor = conn.cursor()
        
        # 构建查询条件
        conditions = []
        params = []
        
        if order_id:
            conditions.append("m.order_id = ?")
            params.append(order_id)
        
        if status:
            conditions.append("m.status = ?")
            params.append(status)
        
        where_clause = " AND ".join(conditions) if conditions else "1=1"
        
        cursor.execute(f"""
            SELECT m.*, o.customer_name, o.car_brand, o.car_model
            FROM mortgage m
            LEFT JOIN orders o ON m.order_id = o.order_id
            WHERE {where_clause}
            ORDER BY m.created_at DESC
        """, params)
        
        rows = cursor.fetchall()
        mortgages = [dict(row) for row in rows]
        conn.close()
        
        return mortgages
    
    @staticmethod
    def get_mortgage_by_order(order_id: str) -> Optional[dict]:
        """根据订单ID获取抵押详情"""
        conn = db.get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT m.*, o.customer_name, o.car_brand, o.car_model
            FROM mortgage m
            LEFT JOIN orders o ON m.order_id = o.order_id
            WHERE m.order_id = ?
        """, (order_id,))
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return dict(row)
        return None
    
    @staticmethod
    def release_mortgage(order_id: str, release_date: str) -> dict:
        """解除抵押"""
        conn = db.get_db_connection()
        cursor = conn.cursor()
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # 更新抵押状态
        cursor.execute("""
            UPDATE mortgage
            SET status = '已解押', release_date = ?
            WHERE order_id = ? AND status = '抵押中'
        """, (release_date, order_id))
        
        if cursor.rowcount == 0:
            conn.close()
            return {"success": False, "message": "抵押记录不存在或已解押"}
        
        # 更新订单状态为"已完结"
        cursor.execute("""
            UPDATE orders SET stage = '已完结', stage_updated_at = ?
            WHERE order_id = ?
        """, (now, order_id))
        
        conn.commit()
        conn.close()
        
        return {
            "success": True,
            "message": "抵押解除成功",
            "order_id": order_id,
            "release_date": release_date
        }
    
    @staticmethod
    def get_mortgage_stats() -> dict:
        """获取抵押统计"""
        conn = db.get_db_connection()
        cursor = conn.cursor()
        
        # 抵押总笔数
        cursor.execute("SELECT COUNT(*) as count FROM mortgage")
        total = cursor.fetchone()["count"]
        
        # 抵押中笔数
        cursor.execute("SELECT COUNT(*) as count FROM mortgage WHERE status = '抵押中'")
        mortgaged_count = cursor.fetchone()["count"]
        
        # 已解押笔数
        cursor.execute("SELECT COUNT(*) as count FROM mortgage WHERE status = '已解押'")
        released_count = cursor.fetchone()["count"]
        
        # 30天内到期笔数
        today = datetime.now()
        expire_soon_date = (today + timedelta(days=30)).strftime("%Y-%m-%d")
        
        cursor.execute("""
            SELECT COUNT(*) as count
            FROM mortgage
            WHERE status = '抵押中' AND expire_date <= ?
        """, (expire_soon_date,))
        expire_soon_count = cursor.fetchone()["count"]
        
        conn.close()
        
        return {
            "total": total,
            "mortgaged_count": mortgaged_count,
            "released_count": released_count,
            "expire_soon_count": expire_soon_count
        }

# ==================== 驾驶舱服务 ====================

class DashboardService:
    """驾驶舱服务"""
    
    @staticmethod
    def get_dashboard() -> dict:
        """获取全局驾驶舱数据"""
        conn = db.get_db_connection()
        cursor = conn.cursor()
        
        today = datetime.now().strftime("%Y-%m-%d")
        month_start = datetime.now().replace(day=1).strftime("%Y-%m-%d")
        
        # 订单统计
        cursor.execute("SELECT COUNT(*) as count FROM orders")
        total_orders = cursor.fetchone()["count"]
        
        cursor.execute("SELECT COUNT(*) as count FROM orders WHERE created_at >= ?", (today,))
        today_orders = cursor.fetchone()["count"]
        
        cursor.execute("SELECT COUNT(*) as count FROM orders WHERE created_at >= ?", (month_start,))
        month_orders = cursor.fetchone()["count"]
        
        orders_stats = {
            "today_new": today_orders,
            "month_new": month_orders,
            "total": total_orders
        }
        
        # 垫资统计（简化版，实际需要关联垫资表）
        advances_stats = {
            "balance": 0,
            "today_advance": 0,
            "overdue_count": 0
        }
        
        # GPS统计（简化版，实际需要关联GPS表）
        gps_stats = {
            "online": 0,
            "offline": 0,
            "alert": 0
        }
        
        # 归档统计（简化版）
        cursor.execute("""
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN archive_status = '完成' THEN 1 ELSE 0 END) as completed
            FROM orders
            WHERE stage IN ('归档完成', '抵押登记中', '已抵押', '正常还款中', '逾期', '已结清', '已完结')
        """)
        archive_row = cursor.fetchone()
        archive_total = archive_row["total"] if archive_row["total"] else 0
        archive_completed = archive_row["completed"] if archive_row["completed"] else 0
        
        archive_stats = {
            "completion_rate": round(archive_completed / archive_total * 100, 2) if archive_total > 0 else 0,
            "pending": archive_total - archive_completed
        }
        
        # 还款统计
        repayment_stats = RepaymentService.get_repayment_stats()
        
        # 抵押统计
        mortgage_stats = MortgageService.get_mortgage_stats()
        
        conn.close()
        
        return {
            "orders_stats": orders_stats,
            "advances_stats": advances_stats,
            "gps_stats": gps_stats,
            "archive_stats": archive_stats,
            "repayment_stats": repayment_stats,
            "mortgage_stats": mortgage_stats
        }
