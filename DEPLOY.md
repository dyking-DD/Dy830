# MASLAS 飞书小程序 - 部署指南

## 🚀 快速启动

### 步骤1：安装依赖
```bash
cd ~/Desktop/2-多节点智能体汽车分期协作系统_软著/feishu-app
npm install
```

### 步骤2：配置MySQL数据库

#### 2.1 创建数据库
```bash
mysql -u root -p < ../database_init.sql
```

#### 2.2 修改数据库配置
编辑 `api-server-full.js`，修改数据库配置：
```javascript
const dbConfig = {
    host: 'localhost',
    user: 'root',
    password: 'your_password',  // 修改为你的MySQL密码
    database: 'maslas_loan_system'
};
```

### 步骤3：启动服务器
```bash
node ../api-server-full.js
```

### 步骤4：访问应用

打开浏览器访问：

- **报单表单**: http://localhost:3000/feishu-app/loan-form.html
- **我的报单**: http://localhost:3000/feishu-app/my-orders.html
- **控制面板**: http://localhost:3000/dashboard.html

---

## 📱 业务员使用指南

### 提交报单

1. 打开报单表单链接
2. 填写以下信息：
   - 客户姓名
   - 联系电话（11位手机号）
   - 身份证号（18位）
   - 业务员姓名（你的名字）
   - 车型（下拉选择）
   - 车价（万元）
   - 首付（万元）
   - 贷款期数（12-60期）
   - 备注说明（可选）
3. 点击"提交报单"
4. 等待审核

### 查看报单

1. 打开"我的报单"链接
2. 查看所有报单列表
3. 查看审批状态
4. 页面每30秒自动刷新

---

## 📊 管理员使用指南

### 查看所有报单

1. 打开控制面板
2. 查看实时统计数据
3. 查看所有报单列表
4. 按业务员、日期、状态筛选

### 审批报单

1. 在控制面板点击报单详情
2. 查看客户信息
3. 进行风险评估
4. 选择审批结果（通过/拒绝）
5. 添加审批备注

---

## 🔧 API接口文档

### 1. 提交报单
**URL**: `POST /api/loan-application`

**请求体**:
```json
{
  "orderId": "ORD1234567890",
  "name": "张三",
  "phone": "13800138000",
  "idCard": "610123199001011234",
  "salesperson": "张业务员",
  "carModel": "奥迪A4",
  "carPrice": "25",
  "downPayment": "5",
  "loanAmount": "20",
  "loanTerm": "36",
  "notes": "备注说明",
  "submitTime": "2026-04-01T04:30:00.000Z",
  "status": "pending"
}
```

**响应**:
```json
{
  "success": true,
  "message": "报单提交成功",
  "orderId": "ORD1234567890"
}
```

---

### 2. 获取业务员报单列表
**URL**: `GET /api/my-orders?salesperson=张业务员`

**响应**:
```json
{
  "success": true,
  "orders": [
    {
      "id": 1,
      "order_id": "ORD1234567890",
      "name": "张三",
      "phone": "13800138000",
      "status": "pending",
      "submit_time": "2026-04-01T04:30:00.000Z"
    }
  ]
}
```

---

### 3. 获取所有报单（管理员）
**URL**: `GET /api/all-orders`

**响应**:
```json
{
  "success": true,
  "orders": [...]
}
```

---

### 4. 获取统计数据
**URL**: `GET /api/statistics`

**响应**:
```json
{
  "success": true,
  "statistics": {
    "today": 15,
    "pending": 8,
    "approved": 12,
    "rejected": 3,
    "total": 38
  }
}
```

---

### 5. 审批报单
**URL**: `POST /api/approve-order`

**请求体**:
```json
{
  "orderId": "ORD1234567890",
  "status": "approved",
  "riskLevel": "low",
  "remarks": "审批通过"
}
```

**响应**:
```json
{
  "success": true,
  "message": "审批成功"
}
```

---

### 6. 获取报单详情
**URL**: `GET /api/order/ORD1234567890`

**响应**:
```json
{
  "success": true,
  "order": {
    "id": 1,
    "order_id": "ORD1234567890",
    "name": "张三",
    "phone": "13800138000",
    ...
  }
}
```

---

## 🔒 安全建议

1. **修改默认密码**: 修改MySQL的root密码
2. **使用HTTPS**: 配置SSL证书
3. **限制访问**: 配置防火墙，只允许必要端口
4. **定期备份**: 定期备份数据库
5. **日志监控**: 监控服务器日志

---

## 🐛 常见问题

### 问题1：数据库连接失败
**解决方案**:
1. 检查MySQL是否启动
2. 检查数据库配置是否正确
3. 检查用户权限

### 问题2：提交报单失败
**解决方案**:
1. 检查表单验证
2. 检查必填项是否填写
3. 查看浏览器控制台错误

### 问题3：无法看到报单列表
**解决方案**:
1. 检查业务员姓名是否正确
2. 刷新页面
3. 检查数据库连接

---

## 📈 性能优化

1. **使用连接池**: 已配置数据库连接池
2. **添加索引**: 已在关键字段添加索引
3. **使用缓存**: 可添加Redis缓存
4. **负载均衡**: 可配置Nginx负载均衡

---

## 📞 技术支持

如有问题，请联系：
- 技术支持：小哈哈
- 文档：查看 README.md

---

**创建时间**: 2026-04-01 04:40 AM
**版本**: V1.0.0
**状态**: ✅ 开发完成