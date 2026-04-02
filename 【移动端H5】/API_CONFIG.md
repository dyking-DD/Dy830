# API 地址配置说明

## 开发环境（本地）
```javascript
const API_BASE = 'http://localhost:8899';
```

## 测试环境（ngrok内网穿透）
```javascript
const API_BASE = 'https://xxxx.ngrok.io';  // 替换为你的ngrok地址
```

## 生产环境（云服务器）
```javascript
const API_BASE = 'https://api.yourdomain.com';
```

## 修改方法

打开 `js/api.js`，找到第一行：
```javascript
const API_BASE = localStorage.getItem('api_base') || 'http://localhost:8899';
```

将后面的地址改成你的实际地址即可。
