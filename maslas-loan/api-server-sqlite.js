const express = require('express');
const sqlite3 = require('sqlite3').verbose();
const path = require('path');
const cors = require('cors');

const app = express();
app.use(cors());
app.use(express.json({ limit: '50mb' }));

// 数据库
const db = new sqlite3.Database(path.join(__dirname, 'loan.db'));

// 创建表
db.serialize(() => {
    // 报单表
    db.run(`CREATE TABLE IF NOT EXISTS loan_applications (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        order_id TEXT UNIQUE,
        customer_name TEXT,
        customer_phone TEXT,
        id_card TEXT,
        staff_id TEXT,
        salesperson TEXT,
        dealer_name TEXT,
        car_brand TEXT,
        car_model TEXT,
        car_color TEXT,
        car_price REAL,
        bank TEXT,
        down_ratio REAL,
        down_payment REAL,
        loan_amount REAL,
        loan_term INTEGER,
        total_rate REAL,
        total_interest REAL,
        monthly_payment REAL,
        has_gps TEXT,
        has_mortgage TEXT,
        funding_date TEXT,
        reg_cert_photos TEXT,
        person_car_photos TEXT,
        notes TEXT,
        status TEXT DEFAULT 'pending',
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )`);
    
    // 员工表
    db.run(`CREATE TABLE IF NOT EXISTS employees (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        employee_id TEXT UNIQUE,
        name TEXT,
        phone TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )`);
    
    // 初始化员工
    const initEmployees = ['DQYD001', 'DQYD002', 'DQYD003'];
    initEmployees.forEach(id => {
        db.run(`INSERT OR IGNORE INTO employees (employee_id) VALUES (?)`, [id]);
    });
});

// 生成订单ID
function generateOrderId() {
    const now = new Date();
    const date = now.toISOString().slice(0, 10).replace(/-/g, '');
    const time = now.getTime().toString().slice(-6);
    return `DQ${date}${time}`;
}

// ===== API 路由 =====

// 提交报单
app.post('/api/loan-application', (req, res) => {
    const data = req.body;
    const orderId = generateOrderId();
    
    const sql = `INSERT INTO loan_applications (
        order_id, customer_name, customer_phone, id_card, staff_id, salesperson, dealer_name,
        car_brand, car_model, car_color, car_price, bank, down_ratio, down_payment,
        loan_amount, loan_term, total_rate, total_interest, monthly_payment,
        has_gps, has_mortgage, funding_date, reg_cert_photos, person_car_photos, notes
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`;
    
    const params = [
        orderId,
        data.customer_name || data.name || null,
        data.customer_phone || data.phone || null,
        data.id_card || data.idCard || null,
        data.staff_id || data.staffId || null,
        data.salesperson || null,
        data.dealer_name || data.dealerName || null,
        data.car_brand || data.carBrand || null,
        data.car_model || data.carModel || null,
        data.car_color || data.carColor || null,
        data.car_price || data.carPrice || null,
        data.bank || null,
        data.down_ratio || data.downRatio || null,
        data.down_payment || data.downPayment || null,
        data.loan_amount || data.loanAmount || null,
        data.loan_term || data.loanTerm || null,
        data.total_rate || data.totalRate || null,
        data.total_interest || data.totalInterest || null,
        data.monthly_payment || data.monthlyPayment || null,
        data.has_gps || data.hasGPS || null,
        data.has_mortgage || data.hasMortgage || null,
        data.funding_date || data.fundingDate || null,
        data.reg_cert_photos || data.regCertPhotos ? JSON.stringify(data.reg_cert_photos || data.regCertPhotos) : null,
        data.person_car_photos || data.personCarPhotos ? JSON.stringify(data.person_car_photos || data.personCarPhotos) : null,
        data.notes || null
    ];
    
    db.run(sql, params, function(err) {
        if (err) {
            console.error(err);
            return res.json({ success: false, error: err.message });
        }
        res.json({ success: true, orderId });
    });
});

// 我的订单（员工端）
app.get('/api/my-orders', (req, res) => {
    const staffId = req.query.staffId || 'DQYD003';
    db.all(`SELECT * FROM loan_applications WHERE staff_id = ? ORDER BY created_at DESC`, [staffId], (err, rows) => {
        if (err) return res.json({ success: false, error: err.message });
        res.json({ success: true, orders: rows });
    });
});

// 所有订单（管理端）
app.get('/api/all-orders', (req, res) => {
    db.all(`SELECT * FROM loan_applications ORDER BY created_at DESC`, [], (err, rows) => {
        if (err) return res.json({ success: false, error: err.message });
        res.json({ success: true, orders: rows });
    });
});

// 单个订单详情
app.get('/api/order/:orderId', (req, res) => {
    db.get(`SELECT * FROM loan_applications WHERE order_id = ?`, [req.params.orderId], (err, row) => {
        if (err) return res.json({ success: false, error: err.message });
        res.json({ success: true, order: row });
    });
});

// 统计数据
app.get('/api/statistics', (req, res) => {
    const today = new Date().toISOString().slice(0, 10);
    
    db.get(`SELECT 
        COUNT(CASE WHEN date(created_at) = ? THEN 1 END) as today,
        COUNT(CASE WHEN status = 'pending' THEN 1 END) as pending,
        COUNT(CASE WHEN status = 'approved' THEN 1 END) as approved,
        COUNT(CASE WHEN status = 'rejected' THEN 1 END) as rejected,
        COUNT(CASE WHEN status = 'funded' THEN 1 END) as funded,
        COUNT(*) as total
    FROM loan_applications`, [today], (err, row) => {
        if (err) return res.json({ success: false, error: err.message });
        res.json({ success: true, statistics: row });
    });
});

// 审核订单
app.post('/api/approve-order', (req, res) => {
    const { orderId, action } = req.body;
    const status = action === 'approve' ? 'approved' : 'rejected';
    
    db.run(`UPDATE loan_applications SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE order_id = ?`, 
        [status, orderId], 
        function(err) {
            if (err) return res.json({ success: false, error: err.message });
            res.json({ success: true });
        }
    );
});

// 删除订单
app.delete('/api/order/:orderId', (req, res) => {
    db.run(`DELETE FROM loan_applications WHERE order_id = ?`, [req.params.orderId], function(err) {
        if (err) return res.json({ success: false, error: err.message });
        res.json({ success: true });
    });
});

// ===== 补充资料 =====
app.put('/api/order/:orderId/supplement', (req, res) => {
    const { orderId } = req.params;
    const { fundingDate, regCertPhotos, personCarPhotos } = req.body;
    
    const sql = `UPDATE loan_applications SET 
        funding_date = ?, 
        reg_cert_photos = ?, 
        person_car_photos = ?, 
        status = 'funded',
        updated_at = CURRENT_TIMESTAMP 
        WHERE order_id = ?`;
    
    const params = [
        fundingDate || null,
        regCertPhotos && regCertPhotos.length > 0 ? JSON.stringify(regCertPhotos) : null,
        personCarPhotos && personCarPhotos.length > 0 ? JSON.stringify(personCarPhotos) : null,
        orderId
    ];
    
    db.run(sql, params, function(err) {
        if (err) {
            console.error(err);
            return res.json({ success: false, error: err.message });
        }
        if (this.changes === 0) {
            return res.json({ success: false, error: '订单不存在' });
        }
        res.json({ success: true, message: '资料已保存' });
    });
});

// ===== 员工管理 =====

// 获取员工列表
app.get('/api/employees', (req, res) => {
    db.all(`SELECT * FROM employees ORDER BY created_at DESC`, [], (err, rows) => {
        if (err) return res.json({ success: false, error: err.message });
        res.json({ success: true, employees: rows });
    });
});

// 添加员工
app.post('/api/employees', (req, res) => {
    const { name, phone, position } = req.body;
    
    // 自动生成员工编号
    db.all(`SELECT employee_id FROM employees ORDER BY id DESC LIMIT 1`, [], (err, rows) => {
        let num = 4;
        if (!err && rows.length && rows[0].employee_id) {
            const last = parseInt(rows[0].employee_id.replace('DQYD', ''));
            if (!isNaN(last)) num = last + 1;
        }
        const newId = 'DQYD' + String(num).padStart(3, '0');
        db.run(`INSERT INTO employees (employee_id, name, phone, position) VALUES (?, ?, ?, ?)`, 
            [newId, name || '（未填）', phone || '', position || '客户经理'], 
            function(err2) {
                if (err2) return res.json({ success: false, error: err2.message });
                res.json({ success: true, employee_id: newId, name: name || '（未填）', phone, position: position || '客户经理' });
            }
        );
    });
});

// 删除员工
app.delete('/api/employees/:employeeId', (req, res) => {
    db.run(`DELETE FROM employees WHERE employee_id = ?`, [req.params.employeeId], function(err) {
        if (err) return res.json({ success: false, error: err.message });
        res.json({ success: true });
    });
});

// 启动服务器
const PORT = 3000;
app.listen(PORT, () => {
    console.log(`API Server running on port ${PORT}`);
});

// DEBUG endpoint
app.post('/api/debug', (req, res) => {
    console.log('DEBUG req.body:', typeof req.body, req.body);
    console.log('DEBUG raw body:', req.rawBody ? req.rawBody.substring(0, 200) : 'none');
    res.json({ received: req.body, type: typeof req.body });
});
