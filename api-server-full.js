const express = require('express');
const mysql = require('mysql2/promise');
const cors = require('cors');
const bodyParser = require('body-parser');

const app = express();
const PORT = 3000;

// 中间件
app.use(cors());
app.use(bodyParser.json());
app.use(bodyParser.urlencoded({ extended: true }));

// 数据库配置
const dbConfig = {
    host: 'localhost',
    user: 'root',
    password: '', // 根据实际情况修改
    database: 'maslas_loan_system',
    waitForConnections: true,
    connectionLimit: 10,
    queueLimit: 0
};

// 创建连接池
const pool = mysql.createPool(dbConfig);

// 测试数据库连接
async function testConnection() {
    try {
        const connection = await pool.getConnection();
        console.log('✅ 数据库连接成功');
        connection.release();
    } catch (error) {
        console.error('❌ 数据库连接失败:', error.message);
    }
}

// API路由

// 1. 提交报单
app.post('/api/loan-application', async (req, res) => {
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
        notes,
        submitTime,
        status
    } = req.body;

    try {
        const connection = await pool.getConnection();

        // 检查订单号是否已存在
        const [existing] = await connection.query(
            'SELECT id FROM loan_applications WHERE order_id = ?',
            [orderId]
        );

        if (existing.length > 0) {
            connection.release();
            return res.json({
                success: false,
                message: '订单号已存在'
            });
        }

        // 插入报单数据
        const sql = `
            INSERT INTO loan_applications (
                order_id, name, phone, id_card, salesperson,
                car_model, car_price, down_payment, loan_amount, loan_term,
                notes, submit_time, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        `;

        const values = [
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
            submitTime,
            status || 'pending'
        ];

        await connection.query(sql, values);
        connection.release();

        console.log(`✅ 报单提交成功: ${orderId} - ${name}`);

        res.json({
            success: true,
            message: '报单提交成功',
            orderId: orderId
        });

    } catch (error) {
        console.error('❌ 提交报单失败:', error);
        res.json({
            success: false,
            message: '提交失败: ' + error.message
        });
    }
});

// 2. 获取业务员的报单列表
app.get('/api/my-orders', async (req, res) => {
    const { salesperson } = req.query;

    try {
        const connection = await pool.getConnection();

        const sql = salesperson
            ? 'SELECT * FROM loan_applications WHERE salesperson = ? ORDER BY submit_time DESC'
            : 'SELECT * FROM loan_applications ORDER BY submit_time DESC';

        const [orders] = await connection.query(sql, salesperson ? [salesperson] : []);
        connection.release();

        res.json({
            success: true,
            orders: orders
        });

    } catch (error) {
        console.error('❌ 获取报单列表失败:', error);
        res.json({
            success: false,
            message: '获取失败: ' + error.message,
            orders: []
        });
    }
});

// 3. 获取所有报单（管理员）
app.get('/api/all-orders', async (req, res) => {
    try {
        const connection = await pool.getConnection();

        const [orders] = await connection.query(
            'SELECT * FROM loan_applications ORDER BY submit_time DESC'
        );

        connection.release();

        res.json({
            success: true,
            orders: orders
        });

    } catch (error) {
        console.error('❌ 获取所有报单失败:', error);
        res.json({
            success: false,
            message: '获取失败: ' + error.message,
            orders: []
        });
    }
});

// 4. 获取统计数据
app.get('/api/statistics', async (req, res) => {
    try {
        const connection = await pool.getConnection();

        // 今日报单数
        const [todayCount] = await connection.query(
            'SELECT COUNT(*) as count FROM loan_applications WHERE DATE(submit_time) = CURDATE()'
        );

        // 待审批数
        const [pendingCount] = await connection.query(
            'SELECT COUNT(*) as count FROM loan_applications WHERE status = ?',
            ['pending']
        );

        // 已通过数
        const [approvedCount] = await connection.query(
            'SELECT COUNT(*) as count FROM loan_applications WHERE status = ?',
            ['approved']
        );

        // 已拒绝数
        const [rejectedCount] = await connection.query(
            'SELECT COUNT(*) as count FROM loan_applications WHERE status = ?',
            ['rejected']
        );

        connection.release();

        res.json({
            success: true,
            statistics: {
                today: todayCount[0].count,
                pending: pendingCount[0].count,
                approved: approvedCount[0].count,
                rejected: rejectedCount[0].count,
                total: todayCount[0].count + pendingCount[0].count + approvedCount[0].count + rejectedCount[0].count
            }
        });

    } catch (error) {
        console.error('❌ 获取统计失败:', error);
        res.json({
            success: false,
            message: '获取失败: ' + error.message
        });
    }
});

// 5. 审批报单
app.post('/api/approve-order', async (req, res) => {
    const { orderId, status, riskLevel, remarks } = req.body;

    try {
        const connection = await pool.getConnection();

        const sql = `
            UPDATE loan_applications
            SET status = ?, risk_level = ?, remarks = ?, approval_time = NOW()
            WHERE order_id = ?
        `;

        await connection.query(sql, [status, riskLevel, remarks, orderId]);
        connection.release();

        console.log(`✅ 报单审批: ${orderId} - ${status}`);

        res.json({
            success: true,
            message: '审批成功'
        });

    } catch (error) {
        console.error('❌ 审批失败:', error);
        res.json({
            success: false,
            message: '审批失败: ' + error.message
        });
    }
});

// 6. 获取单个报单详情
app.get('/api/order/:orderId', async (req, res) => {
    const { orderId } = req.params;

    try {
        const connection = await pool.getConnection();

        const [orders] = await connection.query(
            'SELECT * FROM loan_applications WHERE order_id = ?',
            [orderId]
        );

        connection.release();

        if (orders.length === 0) {
            res.json({
                success: false,
                message: '报单不存在'
            });
        } else {
            res.json({
                success: true,
                order: orders[0]
            });
        }

    } catch (error) {
        console.error('❌ 获取报单详情失败:', error);
        res.json({
            success: false,
            message: '获取失败: ' + error.message
        });
    }
});

// 静态文件服务
app.use(express.static(__dirname));

// 启动服务器
app.listen(PORT, async () => {
    console.log('='.repeat(50));
    console.log('🚀 MASLAS API服务器启动成功');
    console.log('='.repeat(50));
    console.log(`📡 服务器地址: http://localhost:${PORT}`);
    console.log(`📱 报单表单: http://localhost:${PORT}/feishu-app/loan-form.html`);
    console.log(`📋 我的报单: http://localhost:${PORT}/feishu-app/my-orders.html`);
    console.log(`📊 控制面板: http://localhost:${PORT}/dashboard.html`);
    console.log(`📈 API文档: http://localhost:${PORT}/api`);
    console.log('='.repeat(50));

    // 测试数据库连接
    await testConnection();
});

module.exports = app;