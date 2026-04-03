# 权限控制模块 - 修改总结

## 修改时间
2026-04-02

## 修改目标
在现有统一系统基础上，增加权限认证，实现前台（客户）和后台（管理员）分离。

## 修改文件清单

### 1. database.py
**修改内容：**
- 新增 `system_users` 表（系统用户表，后台管理员）
- 新增 `customer_accounts` 表（客户账户表，前台客户）
- 新增索引：`idx_customer_accounts_customer`、`idx_system_users_username`
- 新增测试用户数据：
  - 后台管理员：admin/admin123, finance01/finance123, collections01/collect123
  - 前台客户：13800138001/123456 (张三), 13800138002/123456 (李四)

**关键代码：**
```python
# 系统用户表（后台管理员）
CREATE TABLE system_users (
    user_id TEXT PRIMARY KEY,
    username TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    name TEXT NOT NULL,
    role TEXT NOT NULL,  -- admin/boss/finance/collections/operation
    department TEXT,
    status TEXT DEFAULT '正常',
    created_at TEXT
)

# 客户账户表（前台客户）
CREATE TABLE customer_accounts (
    account_id TEXT PRIMARY KEY,
    customer_id TEXT NOT NULL,  -- 关联客户
    phone TEXT UNIQUE NOT NULL,  -- 手机号即账号
    password_hash TEXT NOT NULL,
    status TEXT DEFAULT '正常',
    created_at TEXT
)
```

### 2. auth.py（新增文件）
**功能：**
- `hash_password()`: 密码哈希（SHA256）
- `verify_password()`: 密码验证
- `generate_token()`: 生成认证token（base64编码）
- `verify_token_full()`: 完整验证token
- `get_user_from_db()`: 从数据库获取用户信息

**Token格式：**
```
base64(user_id|role|expiry|signature)
```

### 3. models.py
**修改内容：**
- 新增 `UserRole` 枚举类
- 新增认证相关模型：
  - `LoginRequest`: 管理员登录请求
  - `CustomerLoginRequest`: 客户登录请求
  - `LoginResponse`: 登录响应
  - `UserInfoResponse`: 用户信息响应
  - `AdminUserCreate`: 创建管理员用户
  - `CustomerAccountCreate`: 创建客户账户

### 4. main.py
**修改内容：**
- 新增导入：`from auth import hash_password, verify_password, generate_token, verify_token_full, get_user_from_db`
- 新增辅助函数：
  - `verify_admin_token()`: 验证管理员token
  - `verify_customer_token()`: 验证客户token
- 新增认证路由：
  - `POST /api/v1/auth/login`: 管理员登录
  - `POST /api/v1/auth/customer/login`: 客户登录
  - `GET /api/v1/auth/me`: 获取当前用户信息
- 新增前台客户路由（7个）：
  - `GET /api/v1/customer/orders`: 客户查看自己的订单列表
  - `GET /api/v1/customer/orders/{order_id}`: 客户查看自己的订单详情
  - `GET /api/v1/customer/advances`: 客户查看自己的垫资记录
  - `GET /api/v1/customer/repayments`: 客户查看自己的还款计划
  - `GET /api/v1/customer/documents`: 客户查看自己的资料归档状态
  - `GET /api/v1/customer/dashboard`: 客户个人中心首页
- 新增管理员账户管理路由：
  - `POST /api/v1/admin/users`: 创建后台用户
  - `GET /api/v1/admin/users`: 获取后台用户列表
- 所有后台路由添加权限验证（46个路由）
- 修改端口：8888 → 8899

### 5. start.sh
**修改内容：**
- 更新端口说明：8888 → 8899
- 新增认证信息提示

### 6. README.md
**修改内容：**
- 更新功能模块说明
- 新增权限控制章节
- 新增认证信息章节
- 更新API端点说明
- 更新数据库表结构说明
- 更新测试数据说明
- 新增权限说明章节
- 更新版本号：v1.0.0 → v2.0.0

## 核心功能

### 认证流程
1. **管理员登录**：`POST /api/v1/auth/login` → 返回token
2. **客户登录**：`POST /api/v1/auth/customer/login` → 返回token
3. **访问受保护路由**：在Header中添加 `Authorization: Bearer <token>`

### 权限隔离
- **后台管理员**：可查看和操作所有数据
- **前台客户**：只能查看自己的数据（数据隔离）

### Token验证
- Token格式：base64编码的 `user_id|role|expiry|signature`
- 过期时间：24小时
- 验证内容：用户ID、角色、过期时间、签名

## 测试账号

### 后台管理员
| 用户名 | 密码 | 角色 | 部门 |
|--------|------|------|------|
| admin | admin123 | admin | - |
| finance01 | finance123 | finance | 财务部 |
| collections01 | collect123 | collections | 贷后部 |

### 前台客户
| 手机号 | 密码 | 客户姓名 |
|--------|------|----------|
| 13800138001 | 123456 | 张三 |
| 13800138002 | 123456 | 李四 |

## API路由统计
- 总路由数：59
- 前台客户路由：7
- 后台管理路由：46
- 认证路由：3
- 系统路由：3

## 启动方式

```bash
# 方式一：使用启动脚本
./start.sh

# 方式二：手动启动
pip install -r requirements.txt
python3 main.py
```

启动后访问：
- API文档：http://localhost:8899/docs
- ReDoc文档：http://localhost:8899/redoc

## 测试方法

运行测试脚本：
```bash
python3 test_api.py
```

## 注意事项

1. **首次启动**：会自动创建数据库和测试数据
2. **重置数据**：删除 `data/` 目录后重新启动
3. **端口冲突**：默认端口 8899，可在 `main.py` 中修改
4. **Token过期**：默认24小时，可在 `auth.py` 中修改
5. **密码安全**：使用SHA256简单哈希，生产环境建议使用werkzeug.security

## 版本信息
- 版本：v2.0.0
- 修改日期：2026-04-02
- 修改人：OpenClaw AI Assistant
