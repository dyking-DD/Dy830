# 汽车分期管理平台 — 登录指南

---

## 🔐 三种登录入口

| 入口 | 对象 | 账号 | 密码 |
|------|------|------|------|
| 📱 **手机端** | 客户 | 13800138001 | 123456 |
| 💻 **PC管理后台** | 管理员/员工 | admin | admin123 |
| 💻 **PC管理后台** | 财务 | finance01 | finance123 |
| 💻 **PC管理后台** | 贷后 | collections01 | collect123 |

---

## 📱 手机端登录（客户用）

### 方式一：本地测试（同一WiFi下）

1. **启动后端**
   ```bash
   cd ~/Desktop/📦我的项目/4-汽车分期管理平台/【真实系统】汽车分期管理平台/
   bash start.sh
   # 后端运行在 http://localhost:8899
   ```

2. **查看电脑IP**（手机需要和电脑同一WiFi）
   ```bash
   # Mac电脑：
   ifconfig | grep "192.168"
   
   # Windows：
   ipconfig
   # 找类似 192.168.x.x 的地址
   ```

3. **修改手机端API地址**
   
   打开 `js/api.js`，找到第一行：
   ```javascript
   const API_BASE = localStorage.getItem('api_base') || 'http://localhost:8899';
   ```
   把 `localhost` 改成你电脑的IP，例如：
   ```javascript
   const API_BASE = localStorage.getItem('api_base') || 'http://192.168.1.100:8899';
   ```

4. **启动手机端页面**
   ```bash
   cd ~/Desktop/📦我的项目/4-汽车分期管理平台/【移动端H5】/
   python3 -m http.server 8080
   ```

5. **手机浏览器打开**
   ```
   http://192.168.1.100:8080
   ```

6. **登录**
   - 手机号：`13800138001`
   - 密码：`123456`

---

### 方式二：扫码访问（内网穿透）

1. 下载 ngrok：https://ngrok.com/download
2. 注册免费账号
3. 运行：
   ```bash
   ./ngrok http 8899
   ```
4. 复制显示的 https 地址（例如 `https://abc123.ngrok.io`）
5. 打开 `js/api.js`，把 API_BASE 改成这个地址
6. 手机浏览器打开 `http://你的.ngrok.io:8080`（另开一个端口）

---

## 💻 PC端登录（管理后台）

### 方式一：本地测试

1. **启动后端**（如果还没启动）
   ```bash
   cd ~/Desktop/📦我的项目/4-汽车分期管理平台/【真实系统】汽车分期管理平台/
   bash start.sh
   ```

2. **打开API文档**
   浏览器访问：**http://localhost:8899/docs**

3. **登录**
   找到 `POST /api/v1/auth/login`，点开，填入：
   ```json
   {
     "username": "admin",
     "password": "admin123"
   }
   ```
   点 Execute → 拿到 token

4. **Authorize**
   右上角 Authorize 按钮，填入 token，后台接口就全通了

5. **直接访问管理页面**
   API文档里可以测试所有接口：
   - `GET /api/v1/orders` — 订单列表
   - `POST /api/v1/advances` — 创建垫资
   - `GET /api/v1/gps/dashboard` — GPS驾驶舱
   - 等等……

### 方式二：浏览器直接打开HTML原型

不需要启动后端，直接双击打开：
```bash
open ~/Desktop/📦我的项目/4-汽车分期管理平台/【原型设计】/dashboard.html
```

---

## 👔 管理者登录哪个？

**登录 PC管理后台，用 admin 账号：**

| 角色 | 账号 | 密码 | 能看到什么 |
|------|------|------|-----------|
| 👑 超级管理员 | admin | admin123 | 所有数据，可管理所有模块 |
| 💰 财务 | finance01 | finance123 | 垫资、还款相关数据 |
| 📋 贷后管理 | collections01 | collect123 | GPS、归档、抵押数据 |

### admin 能做的事：
- 创建/审批/出账垫资单
- 查看所有订单
- 查看GPS告警
- 管理资料归档
- 管理用户账户
- 查看全局驾驶舱

---

## ⚠️ 注意事项

1. **手机端和PC端共用同一个后端**（localhost:8899 或 ngrok地址）
2. **客户看不到别人的数据**，只能看自己的订单
3. **管理员看不到客户敏感信息**（密码等）
4. **token有效期24小时**，过期需要重新登录
5. **测试数据已预置**，登录后就能看到数据

---

## 📞 登录遇到问题？

| 问题 | 解决方法 |
|------|---------|
| 手机打不开页面 | 确认手机和电脑同一WiFi，IP是否正确 |
| 登录提示401 | 检查后端是否启动，token是否过期 |
| 登录提示500 | 后端报错，看终端日志 |
| 看不到数据 | 用 admin/admin123 登录才有完整数据 |
