const express = require('express');
const cors = require('cors');
const bodyParser = require('body-parser');
const Database = require('better-sqlite3');
const path = require('path');

const app = express();
const PORT = 3000;

// 中间件
app.use(cors());
app.use(bodyParser.json());
app.use(express.static(path.join(__dirname)));

// SQLite数据库配置
const db = new Database('maslas_loan_system.db');

// 初始化数据库表
function initDatabase() {
    // 报单表
    db.exec(`
        CREATE TABLE IF NOT EXISTS loan_applications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            phone TEXT NOT NULL,
            id_card TEXT NOT NULL,
            salesperson TEXT NOT NULL,
            car_model TEXT NOT NULL,
            car_price REAL NOT NULL,
            down_payment REAL NOT NULL,
            loan_amount REAL NOT NULL,
            loan_term INTEGER NOT NULL,
            notes TEXT,
            submit_time TEXT NOT NULL,
            status TEXT DEFAULT 'pending',
            risk_level TEXT,
            remarks TEXT,
            approval_time TEXT,
            approver TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    `);

    // 业务员表
    db.exec(`
        CREATE TABLE IF NOT EXISTS salespersons (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            phone TEXT UNIQUE NOT NULL,
            status TEXT DEFAULT 'active',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    `);

    // 风控规则表
    db.exec(`
        CREATE TABLE IF NOT EXISTS risk_rules (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            rule_name TEXT NOT NULL,
            rule_type TEXT,
            rule_value TEXT,
            risk_level TEXT NOT NULL,
            is_active INTEGER DEFAULT 1,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    `);

    // 审批日志表
    db.exec(`
        CREATE TABLE IF NOT EXISTS approval_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id TEXT NOT NULL,
            action TEXT NOT NULL,
            operator TEXT NOT NULL,
            remarks TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    `);

    // 通知表
    db.exec(`
        CREATE TABLE IF NOT EXISTS notifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id TEXT NOT NULL,
            recipient TEXT NOT NULL,
            type TEXT NOT NULL,
            title TEXT NOT NULL,
            content TEXT NOT NULL,
            is_read INTEGER DEFAULT 0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    `);

    // 创建索引
    db.exec(`
        CREATE INDEX IF NOT EXISTS idx_order_id ON loan_applications(order_id);
        CREATE INDEX IF NOT EXISTS idx_salesperson ON loan_applications(salesperson);
        CREATE INDEX IF NOT EXISTS idx_status ON loan_applications(status);
        CREATE INDEX IF NOT EXISTS idx_submit_time ON loan_applications(submit_time);
    `);

    // 插入示例数据
    try {
        const stmt = db.prepare('INSERT INTO salespersons (name, phone) VALUES (?, ?)');
        stmt.run('张业务员', '13800138001');
        stmt.run('李业务员', '13800138002');
        stmt.run('王业务员', '13800138003');
    } catch (err) {
        // 如果数据已存在，忽略
    }

    console.log('✅ SQLite数据库初始化完成');
}

// 初始化数据库
initDatabase();

// API路由

// 1. 提交报单
app.post('/api/loan-application', (req, res) => {
    try {
        const {
            orderId,
            name,
            phone,
            idCard,
            salesperson,
            carModel,
            carPrice,
            downPayment,
            loanAmount,
            loanTerm,
            notes
        } = req.body;

        const stmt = db.prepare(`
            INSERT INTO loan_applications (
                order_id, name, phone, id_card, salesperson, car_model,
                car_price, down_payment, loan_amount, loan_term, notes,
                submit_time, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'pending')
        `);

        stmt.run(
            orderId,
            name,
            phone,
            idCard,
            salesperson,
            carModel,
            parseFloat(carPrice),
            parseFloat(downPayment),
            parseFloat(loanAmount),
            parseInt(loanTerm),
            notes || '',
            new Date().toISOString()
        );

        // 创建通知
        const notifyStmt = db.prepare(`
            INSERT INTO notifications (order_id, recipient, type, title, content)
            VALUES (?, ?, 'new_order', '新报单待审批', ?)
        `);
        notifyStmt.run(orderId, '管理员', `业务员${salesperson}提交了新报单: ${orderId}`);

        res.json({
            success: true,
            message: '报单提交成功',
            orderId: orderId
        });
    } catch (err) {
        console.error('提交报单失败:', err);
        res.status(500).json({
            success: false,
            message: '提交失败: ' + err.message
        });
    }
});

// 2. 获取业务员报单列表
app.get('/api/my-orders', (req, res) => {
    try {
        const { salesperson } = req.query;

        const stmt = db.prepare(`
            SELECT * FROM loan_applications
            WHERE salesperson = ?
            ORDER BY submit_time DESC
        `);

        const orders = stmt.all(salesperson);

        res.json({
            success: true,
            orders: orders
        });
    } catch (err) {
        console.error('获取报单列表失败:', err);
        res.status(500).json({
            success: false,
            message: '获取失败: ' + err.message
        });
    }
});

// 3. 获取所有报单（管理员）
app.get('/api/all-orders', (req, res) => {
    try {
        const stmt = db.prepare(`
            SELECT * FROM loan_applications
            ORDER BY submit_time DESC
        `);

        const orders = stmt.all();

        res.json({
            success: true,
            orders: orders
        });
    } catch (err) {
        console.error('获取所有报单失败:', err);
        res.status(500).json({
            success: false,
            message: '获取失败: ' + err.message
        });
    }
});

// 4. 获取统计数据
app.get('/api/statistics', (req, res) => {
    try {
        const today = new Date().toISOString().split('T')[0];

        const stmt = db.prepare(`
            SELECT
                COUNT(*) as total,
                SUM(CASE WHEN status = 'pending' THEN 1 ELSE 0 END) as pending,
                SUM(CASE WHEN status = 'approved' THEN 1 ELSE 0 END) as approved,
                SUM(CASE WHEN status = 'rejected' THEN 1 ELSE 0 END) as rejected
            FROM loan_applications
            WHERE DATE(submit_time) = ?
        `);

        const result = stmt.get(today);

        res.json({
            success: true,
            statistics: {
                today: result.total || 0,
                pending: result.pending || 0,
                approved: result.approved || 0,
                rejected: result.rejected || 0,
                total: result.total || 0
            }
        });
    } catch (err) {
        console.error('获取统计数据失败:', err);
        res.status(500).json({
            success: false,
            message: '获取失败: ' + err.message
        });
    }
});

// 5. 审批报单
app.post('/api/approve-order', (req, res) => {
    try {
        const { orderId, status, riskLevel, remarks, approver } = req.body;

        const stmt = db.prepare(`
            UPDATE loan_applications
            SET status = ?, risk_level = ?, remarks = ?, approver = ?, approval_time = ?
            WHERE order_id = ?
        `);

        stmt.run(
            status,
            riskLevel || 'low',
            remarks || '',
            approver || '管理员',
            new Date().toISOString(),
            orderId
        );

        // 记录审批日志
        const logStmt = db.prepare(`
            INSERT INTO approval_logs (order_id, action, operator, remarks)
            VALUES (?, ?, ?, ?)
        `);
        logStmt.run(orderId, status, approver || '管理员', remarks || '');

        // 创建通知
        const notifyStmt = db.prepare(`
            INSERT INTO notifications (order_id, recipient, type, title, content)
            VALUES (?, ?, ?, ?, ?)
        `);
        const orderStmt = db.prepare('SELECT salesperson FROM loan_applications WHERE order_id = ?');
        const order = orderStmt.get(orderId);

        if (order) {
            notifyStmt.run(
                orderId,
                order.salesperson,
                status,
                `报单${status === 'approved' ? '已通过' : '已拒绝'}`,
                `您的报单 ${orderId} ${status === 'approved' ? '已通过审批' : '已被拒绝'}${remarks ? '：' + remarks : ''}`
            );
        }

        res.json({
            success: true,
            message: '审批成功'
        });
    } catch (err) {
        console.error('审批报单失败:', err);
        res.status(500).json({
            success: false,
            message: '审批失败: ' + err.message
        });
    }
});

// 6. 获取报单详情
app.get('/api/order/:orderId', (req, res) => {
    try {
        const { orderId } = req.params;

        const stmt = db.prepare(`
            SELECT * FROM loan_applications
            WHERE order_id = ?
        `);

        const order = stmt.get(orderId);

        if (!order) {
            return res.status(404).json({
                success: false,
                message: '报单不存在'
            });
        }

        res.json({
            success: true,
            order: order
        });
    } catch (err) {
        console.error('获取报单详情失败:', err);
        res.status(500).json({
            success: false,
            message: '获取失败: ' + err.message
        });
    }
});

// 启动服务器
app.listen(PORT, () => {
    console.log('🚀 MASLAS API服务器已启动');
    console.log(`📍 地址: http://localhost:${PORT}`);
    console.log(`📱 报单表单: http://localhost:${PORT}/loan-form.html`);
    console.log(`📊 我的报单: http://localhost:${PORT}/my-orders.html`);
});