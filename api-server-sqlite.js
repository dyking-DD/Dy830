const express = require('express');
const cors = require('cors');
const bodyParser = require('body-parser');
const path = require('path');
const fs = require('fs');
const initSqlJs = require('sql.js');

const app = express();
const PORT = process.env.PORT || 3000;

let db = null;
const DB_PATH = path.join(__dirname, 'maslas_loan_system.db');

// 中间件
app.use(cors());
app.use(bodyParser.json());
app.use(express.static(path.join(__dirname)));

// 初始化SQLite数据库
async function initDatabase() {
    try {
        const SQL = await initSqlJs();
        
        // 尝试加载现有数据库
        if (fs.existsSync(DB_PATH)) {
            const buffer = fs.readFileSync(DB_PATH);
            db = new SQL.Database(buffer);
            console.log('✅ 数据库加载成功');
        } else {
            db = new SQL.Database();
            console.log('✅ 新数据库创建成功');
        }
        
        // 创建表
        db.run(`
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
        
        db.run(`
            CREATE TABLE IF NOT EXISTS salespersons (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                phone TEXT UNIQUE NOT NULL,
                status TEXT DEFAULT 'active',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        `);
        
        db.run(`
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
        
        db.run(`
            CREATE TABLE IF NOT EXISTS approval_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_id TEXT NOT NULL,
                action TEXT NOT NULL,
                operator TEXT NOT NULL,
                remarks TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        `);
        
        saveDatabase();
        console.log('✅ 数据表初始化完成');
        
    } catch (error) {
        console.error('❌ 数据库初始化失败:', error);
    }
}

// 保存数据库到文件
function saveDatabase() {
    if (db) {
        const data = db.export();
        const buffer = Buffer.from(data);
        fs.writeFileSync(DB_PATH, buffer);
    }
}

// 生成订单ID
function generateOrderId() {
    const timestamp = Date.now();
    const random = Math.floor(Math.random() * 1000).toString().padStart(3, '0');
    return `ORD${timestamp}${random}`;
}

// API路由

// 获取统计数据
app.get('/api/statistics', (req, res) => {
    if (!db) return res.json({ success: false, message: '数据库未初始化' });
    
    try {
        const today = new Date().toISOString().split('T')[0];
        
        const totalResult = db.exec("SELECT COUNT(*) as count FROM loan_applications");
        const todayResult = db.exec(`SELECT COUNT(*) as count FROM loan_applications WHERE DATE(submit_time) = '${today}'`);
        const pendingResult = db.exec(`SELECT COUNT(*) as count FROM loan_applications WHERE status = 'pending'`);
        const approvedResult = db.exec(`SELECT COUNT(*) as count FROM loan_applications WHERE status = 'approved'`);
        const rejectedResult = db.exec(`SELECT COUNT(*) as count FROM loan_applications WHERE status = 'rejected'`);
        
        const getCount = (result) => result.length > 0 ? result[0].values[0][0] : 0;
        
        res.json({
            success: true,
            statistics: {
                today: getCount(todayResult),
                pending: getCount(pendingResult),
                approved: getCount(approvedResult),
                rejected: getCount(rejectedResult),
                total: getCount(totalResult)
            }
        });
    } catch (error) {
        console.error('统计查询失败:', error);
        res.json({ success: false, message: error.message });
    }
});

// 提交报单
app.post('/api/loan-application', (req, res) => {
    if (!db) return res.json({ success: false, message: '数据库未初始化' });
    
    try {
        const { name, phone, idCard, salesperson, carModel, carPrice, downPayment, loanTerm, notes } = req.body;
        
        // 验证必填项
        if (!name || !phone || !idCard || !salesperson || !carModel || !carPrice || !downPayment || !loanTerm) {
            return res.json({ success: false, message: '请填写所有必填项' });
        }
        
        // 验证手机号
        if (!/^1[3-9]\d{9}$/.test(phone)) {
            return res.json({ success: false, message: '请输入有效的手机号' });
        }
        
        // 验证身份证
        if (!/^\d{17}[\dXx]$/.test(idCard)) {
            return res.json({ success: false, message: '请输入有效的身份证号' });
        }
        
        const orderId = generateOrderId();
        const loanAmount = parseFloat(carPrice) - parseFloat(downPayment);
        const submitTime = new Date().toISOString();
        
        const stmt = db.prepare(`
            INSERT INTO loan_applications 
            (order_id, name, phone, id_card, salesperson, car_model, car_price, down_payment, loan_amount, loan_term, notes, submit_time, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'pending')
        `);
        
        stmt.run([orderId, name, phone, idCard, salesperson, carModel, parseFloat(carPrice), parseFloat(downPayment), loanAmount, parseInt(loanTerm), notes || '', submitTime]);
        stmt.free();
        
        saveDatabase();
        
        console.log(`✅ 新报单: ${orderId} - ${name}`);
        
        res.json({
            success: true,
            message: '报单提交成功',
            orderId: orderId
        });
        
    } catch (error) {
        console.error('报单提交失败:', error);
        res.json({ success: false, message: error.message });
    }
});

// 获取业务员报单列表
app.get('/api/my-orders', (req, res) => {
    if (!db) return res.json({ success: false, message: '数据库未初始化' });
    
    try {
        const { salesperson } = req.query;
        
        if (!salesperson) {
            return res.json({ success: false, message: '请提供业务员姓名' });
        }
        
        const result = db.exec(`SELECT * FROM loan_applications WHERE salesperson = '${salesperson}' ORDER BY submit_time DESC`);
        
        if (result.length === 0) {
            return res.json({ success: true, orders: [] });
        }
        
        const columns = result[0].columns;
        const orders = result[0].values.map(row => {
            const order = {};
            columns.forEach((col, i) => order[col] = row[i]);
            return order;
        });
        
        res.json({
            success: true,
            orders: orders
        });
        
    } catch (error) {
        console.error('查询失败:', error);
        res.json({ success: false, message: error.message });
    }
});

// 获取所有报单（管理员）
app.get('/api/all-orders', (req, res) => {
    if (!db) return res.json({ success: false, message: '数据库未初始化' });
    
    try {
        const result = db.exec("SELECT * FROM loan_applications ORDER BY submit_time DESC");
        
        if (result.length === 0) {
            return res.json({ success: true, orders: [] });
        }
        
        const columns = result[0].columns;
        const orders = result[0].values.map(row => {
            const order = {};
            columns.forEach((col, i) => order[col] = row[i]);
            return order;
        });
        
        res.json({
            success: true,
            orders: orders
        });
        
    } catch (error) {
        console.error('查询失败:', error);
        res.json({ success: false, message: error.message });
    }
});

// 审批报单
app.post('/api/approve-order', (req, res) => {
    if (!db) return res.json({ success: false, message: '数据库未初始化' });
    
    try {
        const { orderId, status, riskLevel, remarks, approver } = req.body;
        
        if (!orderId || !status) {
            return res.json({ success: false, message: '缺少必要参数' });
        }
        
        const approvalTime = new Date().toISOString();
        
        db.run(`
            UPDATE loan_applications 
            SET status = '${status}', 
                risk_level = '${riskLevel || ''}', 
                remarks = '${remarks || ''}', 
                approval_time = '${approvalTime}',
                approver = '${approver || '管理员'}',
                updated_at = '${approvalTime}'
            WHERE order_id = '${orderId}'
        `);
        
        // 记录审批日志
        const logStmt = db.prepare(`
            INSERT INTO approval_logs (order_id, action, operator, remarks, created_at)
            VALUES (?, ?, ?, ?, ?)
        `);
        logStmt.run([orderId, status, approver || '管理员', remarks || '', approvalTime]);
        logStmt.free();
        
        saveDatabase();
        
        console.log(`✅ 审批完成: ${orderId} - ${status}`);
        
        res.json({
            success: true,
            message: '审批成功'
        });
        
    } catch (error) {
        console.error('审批失败:', error);
        res.json({ success: false, message: error.message });
    }
});

// 获取报单详情
app.get('/api/order/:orderId', (req, res) => {
    if (!db) return res.json({ success: false, message: '数据库未初始化' });
    
    try {
        const { orderId } = req.params;
        
        const result = db.exec(`SELECT * FROM loan_applications WHERE order_id = '${orderId}'`);
        
        if (result.length === 0 || result[0].values.length === 0) {
            return res.json({ success: false, message: '报单不存在' });
        }
        
        const columns = result[0].columns;
        const row = result[0].values[0];
        const order = {};
        columns.forEach((col, i) => order[col] = row[i]);
        
        res.json({
            success: true,
            order: order
        });
        
    } catch (error) {
        console.error('查询失败:', error);
        res.json({ success: false, message: error.message });
    }
});

// 获取业务员列表
app.get('/api/salespersons', (req, res) => {
    if (!db) return res.json({ success: false, message: '数据库未初始化' });
    
    try {
        const result = db.exec("SELECT * FROM salespersons WHERE status = 'active' ORDER BY created_at DESC");
        
        if (result.length === 0) {
            return res.json({ success: true, salespersons: [] });
        }
        
        const columns = result[0].columns;
        const salespersons = result[0].values.map(row => {
            const sp = {};
            columns.forEach((col, i) => sp[col] = row[i]);
            return sp;
        });
        
        res.json({
            success: true,
            salespersons: salespersons
        });
        
    } catch (error) {
        console.error('查询失败:', error);
        res.json({ success: false, message: error.message });
    }
});

// 健康检查
app.get('/api/health', (req, res) => {
    res.json({ 
        success: true, 
        status: 'ok',
        database: db ? 'connected' : 'disconnected'
    });
});

// 启动服务器
async function startServer() {
    await initDatabase();
    
    app.listen(PORT, () => {
        console.log('=====================================');
        console.log('  MASLAS 汽车分期系统 API 服务器');
        console.log('=====================================');
        console.log(`📍 地址: http://localhost:${PORT}`);
        console.log(`📱 报单表单: http://localhost:${PORT}/loan-form.html`);
        console.log(`📋 我的报单: http://localhost:${PORT}/my-orders.html`);
        console.log(`📊 管理后台: http://localhost:${PORT}/admin.html`);
        console.log('=====================================');
    });
}

startServer();
