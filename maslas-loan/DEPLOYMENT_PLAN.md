# 飞书小程序部署和测试计划

## 📋 部署前准备

### 1. 检查系统依赖
- [ ] Node.js (v16+)
- [ ] MySQL (v8.0+)
- [ ] Nginx (可选，用于生产环境)

### 2. 安装项目依赖
```bash
cd ~/.openclaw/workspace/feishu-app
npm install
```

### 3. 配置数据库
- [ ] 创建数据库 `maslas_loan_system`
- [ ] 导入数据库初始化脚本
- [ ] 配置数据库连接信息

---

## 🚀 部署步骤

### 步骤1：数据库初始化

#### 1.1 创建数据库
```sql
CREATE DATABASE maslas_loan_system
CHARACTER SET utf8mb4
COLLATE utf8mb4_unicode_ci;

USE maslas_loan_system;
```

#### 1.2 创建表结构
```sql
-- 报单表
CREATE TABLE loan_applications (
  id INT AUTO_INCREMENT PRIMARY KEY,
  order_id VARCHAR(50) UNIQUE NOT NULL,
  name VARCHAR(100) NOT NULL,
  phone VARCHAR(20) NOT NULL,
  id_card VARCHAR(20) NOT NULL,
  salesperson VARCHAR(100) NOT NULL,
  car_model VARCHAR(100) NOT NULL,
  car_price DECIMAL(10,2) NOT NULL,
  down_payment DECIMAL(10,2) NOT NULL,
  loan_amount DECIMAL(10,2) NOT NULL,
  loan_term INT NOT NULL,
  notes TEXT,
  submit_time DATETIME DEFAULT CURRENT_TIMESTAMP,
  status ENUM('pending', 'approved', 'rejected') DEFAULT 'pending',
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  INDEX idx_salesperson (salesperson),
  INDEX idx_status (status),
  INDEX idx_submit_time (submit_time)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

#### 1.3 修改数据库配置
需要创建或编辑 `api-server-full.js`：
```javascript
const dbConfig = {
    host: 'localhost',
    user: 'root',
    password: 'your_password',  // 修改为实际密码
    database: 'maslas_loan_system'
};
```

### 步骤2：创建后端API服务器

#### 2.1 创建 api-server-full.js
如果不存在，需要创建完整的服务器文件。

#### 2.2 启动服务器
```bash
cd ~/.openclaw/workspace/feishu-app
node api-server-full.js
```

### 步骤3：访问测试

#### 3.1 本地测试
- 报单表单：http://localhost:3000/feishu-app/loan-form.html
- 我的报单：http://localhost:3000/feishu-app/my-orders.html

#### 3.2 测试功能清单
- [ ] 提交报单功能
- [ ] 表单验证（手机号、身份证号）
- [ ] 自动计算贷款金额
- [ ] 查看报单列表
- [ ] 报单状态更新
- [ ] 30秒自动刷新

---

## 🧪 测试计划

### 测试1：报单提交
1. 打开报单表单
2. 填写测试数据
3. 点击提交
4. 验证数据库记录

### 测试2：报单查询
1. 打开我的报单页面
2. 验证报单列表显示
3. 验证状态标识
4. 验证自动刷新

### 测试3：API接口
1. 测试 POST /api/loan-application
2. 测试 GET /api/my-orders
3. 测试 GET /api/all-orders
4. 测试 GET /api/statistics
5. 测试 POST /api/approve-order

### 测试4：数据验证
1. 测试必填项验证
2. 测试手机号格式验证
3. 测试身份证号格式验证
4. 测试数值范围验证

---

## 📊 预期结果

### 成功标准
- ✅ 所有功能正常工作
- ✅ 数据正确存储到数据库
- ✅ API接口响应正常
- ✅ 页面渲染正确
- ✅ 表单验证有效

### 性能指标
- 页面加载时间 < 2秒
- API响应时间 < 500ms
- 数据库查询时间 < 100ms

---

## 🐛 故障排除

### 问题1：数据库连接失败
**解决方案**：
1. 检查MySQL是否运行
2. 检查用户名密码
3. 检查数据库权限

### 问题2：API调用失败
**解决方案**：
1. 检查服务器是否启动
2. 检查端口是否被占用
3. 查看服务器日志

### 问题3：页面无法访问
**解决方案**：
1. 检查文件路径
2. 检查服务器配置
3. 检查防火墙设置

---

## ✅ 完成检查清单

### 部署前
- [ ] 系统依赖安装完成
- [ ] 项目依赖安装完成
- [ ] 数据库配置完成
- [ ] 后端API创建完成

### 部署中
- [ ] 数据库初始化完成
- [ ] 服务器启动成功
- [ ] 页面可以访问
- [ ] API接口正常

### 部署后
- [ ] 功能测试通过
- [ ] 性能测试通过
- [ ] 文档更新完成
- [ ] 备份完成

---

**创建时间**: 2026-04-01 11:00
**状态**: 待执行
**执行者**: 小哈哈