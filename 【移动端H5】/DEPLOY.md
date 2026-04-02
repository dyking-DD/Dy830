# 汽车分期管理平台 - 手机端 部署指南

## 方案概述

使用 Cloudflare Pages 免费托管前端，用户的内网机器通过内网穿透暴露给外网访问。

## 步骤一：前端部署到 Cloudflare Pages

### 1.1 准备代码
将【移动端H5】文件夹内容上传到 GitHub 仓库。

### 1.2 连接 Cloudflare Pages
1. 访问 https://pages.cloudflare.com
2. 用 GitHub 登录
3. 点击 "Create a project" → 选择你的仓库
4. 构建设置：
   - Build command: （留空）
   - Output directory: /（或根据实际）
5. 点击 "Save and deploy"

### 1.3 自定义域名（可选）
在 Pages Settings 里添加你自己的域名。

## 步骤二：内网穿透（让手机可以访问本地后端）

### 推荐方案：Cloudflare Tunnel（完全免费）

1. 在有公网IP的机器上（或用有公网IP的云服务器）：
```bash
# 安装 cloudflared
curl -L https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64 -o cloudflared
chmod +x cloudflared
sudo mv cloudflared /usr/local/bin/

# 创建隧道（免费账号即可）
cloudflared tunnel create car-loan-backend

# 获取隧道token，记录下来
cloudflared tunnel run --token <TOKEN>

# 隧道会暴露 localhost:8899 到外网
```

2. 或者用更简单的方案：ngrok
```bash
# 注册 https://ngrok.com
# 安装后：
ngrok http 8899
# 会给你一个 https://xxxx.ngrok.io 的公网地址
```

### 步骤三：修改前端API地址

部署后需要把前端的API地址改成公网地址。

方法：在 js/api.js 里把 API_BASE 改成你的公网地址：
```javascript
const API_BASE = 'https://your-ngrok-url.ngrok.io';  // 改成你的
```

或者用环境变量（如果 Cloudflare Pages 支持）。

## 手机端使用方法

1. 手机浏览器打开部署好的网址
2. 输入手机号登录（测试账号：13800138001 / 123456）
3. 查询订单进度、查看合同、查看资料

## 成本估算

- Cloudflare Pages: 免费（无限流量）
- 域名: 可选（约50元/年）
- 内网穿透: 免费（ngrok免费版有限制但够用）
- 总成本: 0元起

## 注意事项

1. ngrok免费版每次重启会变地址，需要重新配置
2. Cloudflare Tunnel 更稳定但需要有一台有公网IP的机器
3. 正式环境建议购买云服务器（阿里云/腾讯云约30元/月）
