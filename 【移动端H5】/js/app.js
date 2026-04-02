/**
 * 主逻辑文件
 */

// 订单阶段配置
const ORDER_STAGES = [
    { key: '已接单', icon: '📥', desc: '您的订单已被接收，工作人员将尽快与您联系' },
    { key: '垫资预审', icon: '💰', desc: '正在进行垫资预审，评估您的垫资需求' },
    { key: '垫资审批中', icon: '⏳', desc: '垫资审批进行中，请耐心等待' },
    { key: '垫资通过', icon: '✅', desc: '恭喜！垫资申请已通过审批' },
    { key: '垫资已出账', icon: '💸', desc: '垫资款项已出账，请查收' },
    { key: '银行审批中', icon: '🏦', desc: '银行正在审核您的贷款申请，预计1-3个工作日' },
    { key: '审批通过', icon: '🎉', desc: '恭喜！您的贷款申请已通过审批' },
    { key: '放款通知', icon: '📢', desc: '贷款即将发放，请保持电话畅通' },
    { key: '待提车', icon: '🚗', desc: '贷款已放款，请联系车行提车' },
    { key: '已提车', icon: '🎊', desc: '恭喜提车！请按时还款' },
    { key: 'GPS安装中', icon: '🛰️', desc: 'GPS设备正在安装中' },
    { key: 'GPS已在线', icon: '✅', desc: 'GPS设备已安装完成并上线' },
    { key: '资料归档中', icon: '📋', desc: '您的资料正在归档整理中' },
    { key: '归档完成', icon: '✅', desc: '所有资料已归档完成' },
    { key: '正常还款中', icon: '💳', desc: '请按时还款，保持良好信用' },
    { key: '已结清', icon: '🏆', desc: '恭喜！您已结清所有贷款' },
    { key: '已完结', icon: '🎊', desc: '订单已完成，感谢您的信任！' }
];

// 还款状态配置
const REPAYMENT_STATUS = {
    'pending': { text: '待还款', class: 'badge-warning' },
    'normal': { text: '正常', class: 'badge-success' },
    'overdue': { text: '逾期', class: 'badge-danger' },
    'paid': { text: '已还清', class: 'badge-default' }
};

// 资料类型配置
const DOCUMENT_TYPES = {
    'id_card_front': { name: '身份证正面', required: true },
    'id_card_back': { name: '身份证反面', required: true },
    'driver_license': { name: '驾驶证', required: true },
    'bank_card': { name: '银行卡', required: true },
    'income_proof': { name: '收入证明', required: true },
    'work_proof': { name: '工作证明', required: false },
    'residence_proof': { name: '居住证明', required: false },
    'car_purchase_agreement': { name: '购车合同', required: true },
    'insurance': { name: '保险单', required: true },
    'invoice': { name: '购车发票', required: true }
};

// ==================== 首页/进度查询 ====================

/**
 * 查询订单
 */
async function searchOrder() {
    const orderId = document.getElementById('orderInput').value.trim();
    
    if (!orderId) {
        showToast('请输入订单号');
        return;
    }
    
    showLoading();
    
    try {
        // 方式1: 通过订单号查询
        let res = await getOrderByOrderId(orderId);
        
        // 如果失败，尝试从订单列表中查找
        if (res.code !== 200 || !res.data) {
            res = await getMyOrders();
            if (res.code === 200 && res.data) {
                const order = res.data.find(o => o.order_id === orderId || o.order_no === orderId);
                if (order) {
                    res.data = order;
                    res.code = 200;
                }
            }
        }
        
        hideLoading();
        
        if (res.code === 200 && res.data) {
            renderOrderResult(res.data);
        } else {
            renderEmptyState('未找到该订单，请检查订单号');
        }
    } catch (error) {
        hideLoading();
        showToast('查询失败，请检查网络连接');
        renderEmptyState('查询失败，请稍后重试');
    }
}

/**
 * 渲染订单结果
 */
function renderOrderResult(order) {
    const resultSection = document.getElementById('resultSection');
    if (!resultSection) return;
    
    // 确定当前阶段索引
    const currentStage = order.stage || order.status || '已接单';
    const stageIndex = ORDER_STAGES.findIndex(s => s.key === currentStage);
    
    // 客户信息
    const customerName = order.customer_name || localStorage.getItem('customer_name') || '客户';
    const customerPhone = order.customer_phone || localStorage.getItem('phone') || '';
    
    // 车辆信息
    const carBrand = order.car_brand || order.brand || '';
    const carModel = order.car_model || order.model || '';
    
    // 贷款信息
    const loanAmount = order.loan_amount || order.amount || 0;
    const loanTerm = order.loan_term || order.term || 0;
    const monthlyPayment = order.monthly_payment || order.monthly || 0;
    
    // 渲染HTML
    resultSection.innerHTML = `
        <!-- 客户信息卡片 -->
        <div class="card">
            <div class="card-body">
                <div class="customer-info">
                    <div class="customer-avatar">${customerName.charAt(0)}</div>
                    <div>
                        <div class="customer-name">${customerName}</div>
                        <div class="customer-phone">${formatPhone(customerPhone)}</div>
                    </div>
                </div>
                
                <div class="car-info">
                    <div class="car-brand">${carBrand || '待确认车型'}</div>
                    <div class="car-model">${carModel || ''}</div>
                </div>
                
                <div class="loan-summary">
                    <div class="loan-item">
                        <div class="loan-value">${loanAmount ? (loanAmount / 10000).toFixed(0) + '万' : '-'}</div>
                        <div class="loan-label">贷款金额</div>
                    </div>
                    <div class="loan-item">
                        <div class="loan-value">${loanTerm ? loanTerm + '期' : '-'}</div>
                        <div class="loan-label">贷款期数</div>
                    </div>
                    <div class="loan-item">
                        <div class="loan-value">${monthlyPayment ? monthlyPayment.toLocaleString() : '-'}</div>
                        <div class="loan-label">月供金额</div>
                    </div>
                </div>
            </div>
        </div>
        
        <!-- 进度时间轴 -->
        <div class="card">
            <div class="card-header">办理进度</div>
            <div class="card-body">
                <div class="timeline">
                    ${renderTimeline(stageIndex, order)}
                </div>
                
                <!-- 当前阶段高亮卡片 -->
                ${stageIndex >= 0 ? `
                <div class="current-stage-card">
                    <div class="current-stage-title">
                        <span>${ORDER_STAGES[stageIndex].icon}</span>
                        <span>当前阶段：${currentStage}</span>
                    </div>
                    <div class="current-stage-time">更新时间：${formatDateTime(order.stage_time || order.update_time || new Date())}</div>
                    <div class="current-stage-desc">${ORDER_STAGES[stageIndex].desc}</div>
                </div>
                ` : ''}
            </div>
        </div>
    `;
    
    resultSection.style.display = 'block';
}

/**
 * 渲染时间轴
 */
function renderTimeline(currentIndex, order) {
    let html = '';
    
    ORDER_STAGES.forEach((stage, index) => {
        let status = 'pending';
        if (index < currentIndex) {
            status = 'completed';
        } else if (index === currentIndex) {
            status = 'current';
        }
        
        html += `
            <div class="timeline-item ${status}">
                <div class="timeline-dot ${status}">
                    ${status === 'completed' ? '✓' : (status === 'current' ? '●' : '')}
                </div>
                <div class="timeline-content">
                    <div class="timeline-title">${stage.key}</div>
                    ${status !== 'pending' ? `<div class="timeline-time">${formatDateTime(order.stage_times?.[stage.key] || '')}</div>` : ''}
                </div>
            </div>
        `;
    });
    
    return html;
}

/**
 * 渲染空状态
 */
function renderEmptyState(message) {
    const resultSection = document.getElementById('resultSection');
    if (!resultSection) return;
    
    resultSection.innerHTML = `
        <div class="empty-state">
            <div class="empty-icon">🔍</div>
            <div class="empty-text">${message}</div>
        </div>
    `;
    resultSection.style.display = 'block';
}

// ==================== 合同页面 ====================

/**
 * 加载还款计划
 */
async function loadRepayments() {
    showLoading();
    
    try {
        const res = await getMyRepayments();
        hideLoading();
        
        if (res.code === 200 && res.data) {
            renderRepayments(res.data);
        } else {
            // 使用模拟数据
            renderRepayments(getMockRepayments());
        }
    } catch (error) {
        hideLoading();
        showToast('加载失败');
        // 使用模拟数据
        renderRepayments(getMockRepayments());
    }
}

/**
 * 获取模拟还款数据
 */
function getMockRepayments() {
    return {
        loan_amount: 280000,
        down_payment: 80000,
        monthly_payment: 8520,
        total_terms: 36,
        paid_terms: 8,
        repayments: [
            { term: 1, due_date: '2025-01-15', amount: 8520, status: 'paid', paid_date: '2025-01-14' },
            { term: 2, due_date: '2025-02-15', amount: 8520, status: 'paid', paid_date: '2025-02-15' },
            { term: 3, due_date: '2025-03-15', amount: 8520, status: 'paid', paid_date: '2025-03-14' },
            { term: 4, due_date: '2025-04-15', amount: 8520, status: 'paid', paid_date: '2025-04-15' },
            { term: 5, due_date: '2025-05-15', amount: 8520, status: 'paid', paid_date: '2025-05-14' },
            { term: 6, due_date: '2025-06-15', amount: 8520, status: 'paid', paid_date: '2025-06-15' },
            { term: 7, due_date: '2025-07-15', amount: 8520, status: 'paid', paid_date: '2025-07-14' },
            { term: 8, due_date: '2025-08-15', amount: 8520, status: 'paid', paid_date: '2025-08-15' },
            { term: 9, due_date: '2025-09-15', amount: 8520, status: 'normal' },
            { term: 10, due_date: '2025-10-15', amount: 8520, status: 'pending' }
        ]
    };
}

/**
 * 渲染还款计划
 */
function renderRepayments(data) {
    // 渲染贷款总览
    const overviewCard = document.getElementById('loanOverview');
    if (overviewCard) {
        overviewCard.innerHTML = `
            <div class="loan-amount">
                <span class="amount-large">${(data.loan_amount / 10000).toFixed(0)}</span>
                <span class="amount-unit">万元</span>
            </div>
            <div class="loan-detail">
                <div class="loan-detail-item">
                    <div class="loan-detail-value">${(data.down_payment / 10000).toFixed(0)}万</div>
                    <div class="loan-detail-label">首付</div>
                </div>
                <div class="loan-detail-item">
                    <div class="loan-detail-value">${data.monthly_payment.toLocaleString()}</div>
                    <div class="loan-detail-label">月供</div>
                </div>
                <div class="loan-detail-item">
                    <div class="loan-detail-value">${data.total_terms}期</div>
                    <div class="loan-detail-label">分期</div>
                </div>
            </div>
        `;
    }
    
    // 渲染还款列表
    const repaymentList = document.getElementById('repaymentList');
    if (repaymentList && data.repayments) {
        repaymentList.innerHTML = data.repayments.map(item => {
            const statusConfig = REPAYMENT_STATUS[item.status] || REPAYMENT_STATUS['pending'];
            return `
                <tr>
                    <td>第${item.term}期</td>
                    <td>${formatDate(item.due_date)}</td>
                    <td>${item.amount.toLocaleString()}</td>
                    <td><span class="badge ${statusConfig.class}">${statusConfig.text}</span></td>
                </tr>
            `;
        }).join('');
    }
    
    // 渲染进度
    const progressBar = document.getElementById('progressBar');
    const progressText = document.getElementById('progressText');
    if (progressBar && progressText) {
        const progress = (data.paid_terms / data.total_terms * 100).toFixed(1);
        progressBar.style.width = progress + '%';
        progressText.textContent = `已还 ${data.paid_terms} 期，剩余 ${data.total_terms - data.paid_terms} 期`;
    }
}

// ==================== 资料页面 ====================

/**
 * 加载资料列表
 */
async function loadDocuments() {
    showLoading();
    
    try {
        const res = await getMyDocuments();
        hideLoading();
        
        if (res.code === 200 && res.data) {
            renderDocuments(res.data);
        } else {
            // 使用模拟数据
            renderDocuments(getMockDocuments());
        }
    } catch (error) {
        hideLoading();
        showToast('加载失败');
        // 使用模拟数据
        renderDocuments(getMockDocuments());
    }
}

/**
 * 获取模拟资料数据
 */
function getMockDocuments() {
    return {
        total: 10,
        uploaded: 7,
        documents: [
            { type: 'id_card_front', name: '身份证正面', uploaded: true, upload_time: '2025-03-28 10:30' },
            { type: 'id_card_back', name: '身份证反面', uploaded: true, upload_time: '2025-03-28 10:31' },
            { type: 'driver_license', name: '驾驶证', uploaded: true, upload_time: '2025-03-28 10:32' },
            { type: 'bank_card', name: '银行卡', uploaded: true, upload_time: '2025-03-28 10:35' },
            { type: 'income_proof', name: '收入证明', uploaded: true, upload_time: '2025-03-28 14:20' },
            { type: 'work_proof', name: '工作证明', uploaded: false },
            { type: 'residence_proof', name: '居住证明', uploaded: false },
            { type: 'car_purchase_agreement', name: '购车合同', uploaded: true, upload_time: '2025-03-29 09:00' },
            { type: 'insurance', name: '保险单', uploaded: true, upload_time: '2025-03-30 15:30' },
            { type: 'invoice', name: '购车发票', uploaded: false }
        ]
    };
}

/**
 * 渲染资料列表
 */
function renderDocuments(data) {
    // 渲染进度圆环
    const progressRing = document.getElementById('progressRing');
    const progressValue = document.getElementById('progressValue');
    
    if (progressRing && progressValue) {
        const percentage = (data.uploaded / data.total * 100).toFixed(0);
        const circumference = 2 * Math.PI * 50; // r=50
        const offset = circumference - (percentage / 100) * circumference;
        
        progressRing.style.strokeDashoffset = offset;
        progressValue.textContent = percentage + '%';
    }
    
    // 渲染资料列表
    const docList = document.getElementById('docList');
    if (docList && data.documents) {
        // 按必填/选填分组
        const requiredDocs = data.documents.filter(d => DOCUMENT_TYPES[d.type]?.required);
        const optionalDocs = data.documents.filter(d => !DOCUMENT_TYPES[d.type]?.required);
        
        let html = '';
        
        // 必填项
        if (requiredDocs.length > 0) {
            html += '<div class="section-title">必填资料</div>';
            html += '<div class="card"><div class="card-body" style="padding:0;">';
            requiredDocs.forEach(doc => {
                html += renderDocItem(doc);
            });
            html += '</div></div>';
        }
        
        // 选填项
        if (optionalDocs.length > 0) {
            html += '<div class="section-title">选填资料</div>';
            html += '<div class="card"><div class="card-body" style="padding:0;">';
            optionalDocs.forEach(doc => {
                html += renderDocItem(doc);
            });
            html += '</div></div>';
        }
        
        docList.innerHTML = html;
    }
}

/**
 * 渲染单个资料项
 */
function renderDocItem(doc) {
    return `
        <div class="doc-item" onclick="handleDocClick('${doc.type}', ${doc.uploaded})">
            <div class="doc-name">
                ${doc.name}
                ${DOCUMENT_TYPES[doc.type]?.required ? '<span class="doc-required">*</span>' : ''}
            </div>
            <div class="doc-status ${doc.uploaded ? 'uploaded' : 'pending'}">
                ${doc.uploaded ? '✓ 已上传' : '待上传'}
            </div>
        </div>
    `;
}

/**
 * 处理资料点击
 */
function handleDocClick(docType, uploaded) {
    if (uploaded) {
        showToast('该资料已上传');
    } else {
        // 触发文件选择
        const input = document.createElement('input');
        input.type = 'file';
        input.accept = 'image/*,.pdf';
        input.onchange = async (e) => {
            const file = e.target.files[0];
            if (file) {
                showLoading();
                const res = await uploadDocument(docType, file);
                hideLoading();
                
                if (res.code === 200) {
                    showToast('上传成功');
                    loadDocuments(); // 刷新列表
                } else {
                    showToast(res.message || '上传失败');
                }
            }
        };
        input.click();
    }
}

// ==================== 个人中心 ====================

/**
 * 加载顾问信息
 */
async function loadAdvisor() {
    try {
        const res = await getMyAdvisor();
        
        if (res.code === 200 && res.data) {
            renderAdvisor(res.data);
        } else {
            // 使用模拟数据
            renderAdvisor(getMockAdvisor());
        }
    } catch (error) {
        // 使用模拟数据
        renderAdvisor(getMockAdvisor());
    }
}

/**
 * 获取模拟顾问数据
 */
function getMockAdvisor() {
    return {
        name: '李顾问',
        phone: '13912345678',
        wechat: 'advisor_licq',
        avatar: '李'
    };
}

/**
 * 渲染顾问信息
 */
function renderAdvisor(data) {
    const advisorCard = document.getElementById('advisorCard');
    if (advisorCard) {
        advisorCard.innerHTML = `
            <div class="advisor-avatar">${data.avatar || data.name.charAt(0)}</div>
            <div class="advisor-info">
                <div class="advisor-name">${data.name}</div>
                <div class="advisor-phone">${formatPhone(data.phone)}</div>
            </div>
            <div class="advisor-actions">
                <a href="tel:${data.phone}" class="btn btn-primary btn-sm">📞 拨打</a>
            </div>
        `;
    }
}

// ==================== API配置 ====================

/**
 * 显示API配置弹窗
 */
function showApiConfig() {
    const currentApi = getApiBase();
    const newApi = prompt('请输入API地址：', currentApi);
    
    if (newApi !== null && newApi.trim() !== '') {
        setApiBase(newApi.trim());
        showToast('API地址已更新');
    }
}
