/**
 * API请求封装
 * 支持配置API地址，方便手机访问
 */

// API基础配置（可动态修改）
let API_BASE = localStorage.getItem('api_base') || 'http://localhost:8899';

// 设置API地址
function setApiBase(url) {
    API_BASE = url;
    localStorage.setItem('api_base', url);
    console.log('API地址已更新为:', url);
}

// 获取API地址
function getApiBase() {
    return API_BASE;
}

// 统一请求方法
async function request(path, method = 'GET', body = null, needAuth = true) {
    const headers = {
        'Content-Type': 'application/json'
    };
    
    // 添加认证token
    if (needAuth) {
        const token = localStorage.getItem('customer_token');
        if (token) {
            headers['Authorization'] = 'Bearer ' + token;
        }
    }
    
    const options = {
        method: method,
        headers: headers,
        mode: 'cors'
    };
    
    if (body && (method === 'POST' || method === 'PUT' || method === 'PATCH')) {
        options.body = JSON.stringify(body);
    }
    
    try {
        const response = await fetch(API_BASE + path, options);
        const data = await response.json();
        return data;
    } catch (error) {
        console.error('API请求失败:', error);
        throw error;
    }
}

// ==================== 认证相关API ====================

/**
 * 客户登录
 * @param {string} phone - 手机号
 * @param {string} password - 密码
 */
async function customerLogin(phone, password) {
    try {
        const res = await request('/api/v1/auth/customer/login', 'POST', { phone, password }, false);
        
        if (res.code === 200 && res.data) {
            // 保存登录信息
            localStorage.setItem('customer_token', res.data.token);
            localStorage.setItem('customer_name', res.data.customer_name || '');
            localStorage.setItem('customer_id', res.data.customer_id || '');
            localStorage.setItem('phone', phone);
            return { success: true, data: res.data };
        } else {
            return { success: false, message: res.message || '登录失败' };
        }
    } catch (error) {
        return { success: false, message: '网络错误，请检查API地址配置' };
    }
}

/**
 * 退出登录
 */
function logout() {
    localStorage.removeItem('customer_token');
    localStorage.removeItem('customer_name');
    localStorage.removeItem('customer_id');
    localStorage.removeItem('phone');
    window.location.href = 'index.html';
}

// ==================== 订单相关API ====================

/**
 * 获取我的订单列表
 */
async function getMyOrders() {
    try {
        const res = await request('/api/v1/customer/orders', 'GET');
        return res;
    } catch (error) {
        return { code: 500, message: '获取订单失败' };
    }
}

/**
 * 根据订单号查询订单详情
 * @param {string} orderId - 订单号
 */
async function getOrderByOrderId(orderId) {
    try {
        const res = await request(`/api/v1/customer/orders/${orderId}`, 'GET');
        return res;
    } catch (error) {
        return { code: 500, message: '查询订单失败' };
    }
}

// ==================== 还款相关API ====================

/**
 * 获取还款计划
 */
async function getMyRepayments() {
    try {
        const res = await request('/api/v1/customer/repayments', 'GET');
        return res;
    } catch (error) {
        return { code: 500, message: '获取还款计划失败' };
    }
}

// ==================== 资料相关API ====================

/**
 * 获取资料列表
 */
async function getMyDocuments() {
    try {
        const res = await request('/api/v1/customer/documents', 'GET');
        return res;
    } catch (error) {
        return { code: 500, message: '获取资料列表失败' };
    }
}

/**
 * 上传资料
 * @param {string} docType - 资料类型
 * @param {File} file - 文件
 */
async function uploadDocument(docType, file) {
    try {
        const formData = new FormData();
        formData.append('doc_type', docType);
        formData.append('file', file);
        
        const token = localStorage.getItem('customer_token');
        const response = await fetch(API_BASE + '/api/v1/customer/documents/upload', {
            method: 'POST',
            headers: {
                'Authorization': 'Bearer ' + token
            },
            body: formData
        });
        
        const data = await response.json();
        return data;
    } catch (error) {
        return { code: 500, message: '上传失败' };
    }
}

// ==================== 顾问相关API ====================

/**
 * 获取我的顾问信息
 */
async function getMyAdvisor() {
    try {
        const res = await request('/api/v1/customer/advisor', 'GET');
        return res;
    } catch (error) {
        return { code: 500, message: '获取顾问信息失败' };
    }
}

// ==================== 工具函数 ====================

/**
 * 显示Toast提示
 * @param {string} message - 提示消息
 * @param {number} duration - 显示时长(毫秒)
 */
function showToast(message, duration = 2000) {
    // 移除已存在的toast
    const existingToast = document.querySelector('.toast');
    if (existingToast) {
        existingToast.remove();
    }
    
    // 创建新toast
    const toast = document.createElement('div');
    toast.className = 'toast';
    toast.textContent = message;
    document.body.appendChild(toast);
    
    // 显示
    setTimeout(() => toast.classList.add('show'), 10);
    
    // 隐藏
    setTimeout(() => {
        toast.classList.remove('show');
        setTimeout(() => toast.remove(), 200);
    }, duration);
}

/**
 * 显示加载中
 */
function showLoading() {
    // 移除已存在的loading
    const existingLoading = document.querySelector('.loading-overlay');
    if (existingLoading) {
        existingLoading.remove();
    }
    
    const loading = document.createElement('div');
    loading.className = 'loading-overlay';
    loading.innerHTML = `
        <div class="loading-content">
            <div class="loading-spinner"></div>
            <div class="loading-text">加载中...</div>
        </div>
    `;
    loading.style.cssText = `
        position: fixed;
        top: 0;
        left: 0;
        right: 0;
        bottom: 0;
        background: rgba(255,255,255,0.9);
        display: flex;
        align-items: center;
        justify-content: center;
        z-index: 999;
    `;
    loading.querySelector('.loading-content').style.cssText = `
        text-align: center;
    `;
    
    document.body.appendChild(loading);
}

/**
 * 隐藏加载中
 */
function hideLoading() {
    const loading = document.querySelector('.loading-overlay');
    if (loading) {
        loading.remove();
    }
}

/**
 * 格式化金额
 * @param {number} amount - 金额
 * @param {boolean} showUnit - 是否显示单位
 */
function formatAmount(amount, showUnit = true) {
    if (!amount && amount !== 0) return '-';
    const formatted = amount.toLocaleString('zh-CN');
    return showUnit ? `¥${formatted}` : formatted;
}

/**
 * 格式化手机号（隐藏中间四位）
 * @param {string} phone - 手机号
 */
function formatPhone(phone) {
    if (!phone) return '-';
    return phone.replace(/(\d{3})\d{4}(\d{4})/, '$1****$2');
}

/**
 * 格式化日期
 * @param {string} dateStr - 日期字符串
 */
function formatDate(dateStr) {
    if (!dateStr) return '-';
    const date = new Date(dateStr);
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const day = String(date.getDate()).padStart(2, '0');
    return `${year}-${month}-${day}`;
}

/**
 * 格式化日期时间
 * @param {string} dateStr - 日期时间字符串
 */
function formatDateTime(dateStr) {
    if (!dateStr) return '-';
    const date = new Date(dateStr);
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const day = String(date.getDate()).padStart(2, '0');
    const hour = String(date.getHours()).padStart(2, '0');
    const minute = String(date.getMinutes()).padStart(2, '0');
    return `${year}-${month}-${day} ${hour}:${minute}`;
}
