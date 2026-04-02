/**
 * 登录状态管理
 */

/**
 * 检查是否已登录
 * @returns {boolean}
 */
function checkAuth() {
    const token = localStorage.getItem('customer_token');
    if (!token) {
        // 未登录，跳转到登录页
        const currentPage = window.location.pathname.split('/').pop();
        if (currentPage !== 'index.html' && currentPage !== '') {
            window.location.href = 'index.html';
        }
        return false;
    }
    return true;
}

/**
 * 获取用户信息
 * @returns {Object}
 */
function getUserInfo() {
    return {
        name: localStorage.getItem('customer_name') || '客户',
        phone: localStorage.getItem('phone') || '',
        customerId: localStorage.getItem('customer_id') || ''
    };
}

/**
 * 获取用户名首字（用于头像显示）
 * @returns {string}
 */
function getUserInitial() {
    const name = localStorage.getItem('customer_name') || '客';
    return name.charAt(0);
}

/**
 * 检查登录状态并显示用户信息
 */
function initPageAuth() {
    if (!checkAuth()) {
        return false;
    }
    
    // 更新页面上的用户头像
    const avatarElements = document.querySelectorAll('.navbar-avatar, .user-avatar');
    const initial = getUserInitial();
    
    avatarElements.forEach(el => {
        if (el.textContent === '' || el.textContent === '客') {
            el.textContent = initial;
        }
    });
    
    // 更新用户名和手机号
    const userInfo = getUserInfo();
    const nameElements = document.querySelectorAll('.user-name');
    const phoneElements = document.querySelectorAll('.user-phone');
    
    nameElements.forEach(el => {
        el.textContent = userInfo.name;
    });
    
    phoneElements.forEach(el => {
        el.textContent = formatPhone(userInfo.phone);
    });
    
    return true;
}

/**
 * 判断是否在登录页
 * @returns {boolean}
 */
function isLoginPage() {
    const currentPage = window.location.pathname.split('/').pop();
    return currentPage === 'index.html' || currentPage === '';
}
