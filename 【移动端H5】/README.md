# 汽车分期管理平台 - 移动端H5

## 📱 项目简介

移动端H5应用，为客户提供订单进度查询、还款计划查看、资料上传等功能。UI风格参考微信小程序/支付宝小程序，简洁美观。

## 🚀 快速开始

### 方式一：直接打开（开发模式）

1. 双击 `index.html` 打开登录页
2. 点击"配置API地址"按钮，输入后端API地址
3. 使用手机号+密码登录

### 方式二：本地服务器（推荐）

```bash
# 使用Python启动本地服务器
cd 【移动端H5】
python3 -m http.server 8080

# 访问 http://localhost:8080
```

### 方式三：手机访问

1. 确保手机和电脑在同一局域网
2. 启动本地服务器
3. 查看电脑IP地址（如 192.168.1.100）
4. 手机浏览器访问 `http://192.168.1.100:8080`
5. 在登录页配置API地址为 `http://192.168.1.100:8899`

## 📁 文件结构

```
【移动端H5】/
├── index.html          # 登录页
├── home.html           # 首页/进度查询
├── contract.html       # 我的合同/还款计划
├── documents.html      # 我的资料
├── profile.html        # 个人中心
├── css/
│   └── app.css         # 统一样式
└── js/
    ├── api.js          # API请求封装
    ├── auth.js         # 登录状态管理
    └── app.js          # 主逻辑
```

## 🔧 API配置

### 默认API地址
- 默认：`http://localhost:8899`
- 可在登录页或个人中心修改

### 后端API接口

| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/v1/auth/customer/login` | POST | 客户登录 |
| `/api/v1/customer/orders` | GET | 获取订单列表 |
| `/api/v1/customer/orders/:id` | GET | 查询订单详情 |
| `/api/v1/customer/repayments` | GET | 获取还款计划 |
| `/api/v1/customer/documents` | GET | 获取资料列表 |
| `/api/v1/customer/documents/upload` | POST | 上传资料 |
| `/api/v1/customer/advisor` | GET | 获取顾问信息 |

## 🎨 UI设计规范

### 颜色
- 主色：`#1A3A6B`（深蓝）
- 强调色：`#FF6B35`（橙色）
- 背景色：`#F5F5F5`（浅灰）
- 成功：`#52c41a`
- 危险：`#ff4d4f`
- 警告：`#faad14`

### 组件
- 卡片：白色背景 + 12px圆角 + 轻微阴影
- 按钮：圆角12px + 渐变背景
- 输入框：圆角12px + 聚焦时边框高亮
- 标签：圆角12px + 浅色背景

### 时间轴
- 已完成：蓝色实心圆 + 蓝色文字
- 当前：橙色脉冲动画 + 橙色文字
- 未完成：灰色空心圆 + 灰色文字

## 📝 功能说明

### 登录页 (index.html)
- 手机号+密码登录
- API地址配置入口
- 自动跳转已登录用户

### 首页 (home.html)
- 订单号搜索
- 客户信息展示
- 车辆信息展示
- 贷款信息概览
- 进度时间轴（重点）
- 当前阶段高亮卡片

### 合同页 (contract.html)
- 贷款总览卡片
- 还款计划列表
- 还款进度条

### 资料页 (documents.html)
- 上传进度圆环
- 必填/选填资料分组
- 点击上传资料

### 个人中心 (profile.html)
- 用户信息卡片
- 顾问联系方式
- 常见问题（可展开）
- API配置
- 退出登录

## 🔄 模拟数据

当API不可用时，系统会自动使用模拟数据，方便演示和测试。

模拟数据包括：
- 订单信息（奔驰GLC 300L）
- 还款计划（36期，已还8期）
- 资料列表（10项，已上传7项）
- 顾问信息（李顾问）

## 🌐 部署建议

### 静态托管
可部署到任意静态托管平台：
- Netlify
- Vercel
- GitHub Pages
- 腾讯云 COS
- 阿里云 OSS

### Nginx配置示例
```nginx
server {
    listen 80;
    server_name your-domain.com;
    
    location / {
        root /path/to/移动端H5;
        index index.html;
        try_files $uri $uri/ /index.html;
    }
}
```

## 📱 浏览器兼容

- iOS Safari 12+
- Android Chrome 60+
- 微信内置浏览器
- 支付宝内置浏览器

## 🛠 技术栈

- HTML5 + CSS3 + JavaScript (ES6+)
- 无框架依赖，纯原生实现
- LocalStorage 存储登录状态
- Fetch API 网络请求
- CSS Variables 主题配置
- CSS Animation 动画效果

## 📄 License

MIT
