/* /static/js/detail.js */

let currentOrderId = null;
let currentUser = null;
let currentOrderData = null;

// 全局入口
window.initDetailLogic = async function(orderId) {
    currentOrderId = orderId;
    currentUser = JSON.parse(localStorage.getItem('user') || '{}');
    await loadOrderData();
    
    // 绑定评分点击
    document.querySelectorAll('.star-rating i').forEach(star => {
        star.onclick = function() {
            const val = this.dataset.val;
            document.querySelectorAll('.star-rating i').forEach(s => {
                s.classList.toggle('active', s.dataset.val <= val);
            });
        }
    });
};

async function loadOrderData() {
    try {
        const res = await api.get(`/orders/${currentOrderId}`);
        currentOrderData = res.data;
        updateUI(currentOrderData);
    } catch (e) {
        console.error(e);
        showToast('加载失败: ' + e.message);
    }
}

function updateUI(order) {
    // 1. 基础信息填充
    document.getElementById('panel-title').innerText = order.description || '无描述';
    
    // 安全截取订单号
    const orderIdStr = String(order.order_id);
    document.getElementById('panel-id').innerText = orderIdStr.length > 8 ? orderIdStr.substring(0, 8) : orderIdStr;
    
    document.getElementById('panel-price').innerText = '¥' + order.reward_points;
    document.getElementById('time-create').innerText = order.create_time;

    const statusMap = {0: '待接单', 1: '配送中', 2: '待收货', 3: '已完成', 4: '已取消'};
    const badge = document.getElementById('panel-status-badge');
    badge.innerText = statusMap[order.status];
    badge.style.background = order.status === 0 ? '#EDF2F7' : (order.status === 3 ? '#F0FFF4' : '#EBF8FF');
    badge.style.color = order.status === 0 ? '#718096' : (order.status === 3 ? '#48BB78' : '#3182CE');

    // 2. 时间轴更新
    const trackTaken = document.getElementById('track-taken');
    const trackDone = document.getElementById('track-done');
    
    if(trackTaken) trackTaken.className = 'timeline-item';
    if(trackDone) trackDone.className = 'timeline-item';

    if (order.status >= 1) {
        trackTaken.classList.add('active');
        trackTaken.children[0].style.background = '#3182CE'; 
        trackTaken.children[1].style.color = '#1A202C';
        document.getElementById('time-taken').innerText = order.take_time || '刚刚';
    }
    if (order.status >= 3) {
        trackDone.classList.add('active');
        trackDone.children[0].style.background = '#48BB78';
        trackDone.children[1].style.color = '#1A202C';
        document.getElementById('time-done').innerText = order.finish_time || '刚刚';
    }

    // 3. 底部按钮逻辑 (强力修复版)
    const actions = document.getElementById('panel-actions');
    const footer = document.querySelector('.panel-footer');
    
    // [修复] 强制转换为字符串比较，确保万无一失
    // 注意：如果是系统预设的假数据订单，user_id 可能不等于当前用户，所以显示接单是正常的。
    // 请务必自己发布一个新订单进行测试！
    const isOwner = String(order.user_id) === String(currentUser.user_id);
    
    console.log(`Order Owner: ${order.user_id}, Current User: ${currentUser.user_id}, isOwner: ${isOwner}`);

    footer.className = 'panel-footer'; // 重置类名

    if (order.status === 0) {
        if (isOwner) {
            // [发布者本人] -> 显示 [联系] [取消订单]
            actions.innerHTML = `
                <button class="btn btn-secondary-outline" onclick="toggleChat()"><i class="fas fa-comment-dots" style="margin-right:8px;"></i>联系</button>
                <button class="btn btn-danger" onclick="cancelOrder('${order.order_id}')">取消订单</button>
            `;
        } else {
            // [其他路人] -> 显示 [立即接单]
            footer.classList.add('single-btn');
            actions.innerHTML = `<button class="btn btn-submit btn-block" onclick="takeOrder('${order.order_id}')" style="background:#3182CE;color:#fff;">立即接单</button>`;
        }
    } else if (order.status === 1 || order.status === 2) {
        // 配送中/待收货 -> 显示 [联系] [操作]
        const actionBtn = isOwner 
            ? `<button class="btn btn-submit" style="background:#0F172A;color:#fff;" onclick="confirmFinish('${order.order_id}')">确认收货</button>`
            : `<button class="btn btn-submit" style="background:#48BB78;color:#fff;" onclick="confirmDeliver('${order.order_id}')">确认送达</button>`;
            
        actions.innerHTML = `
            <button class="btn btn-secondary-outline" onclick="toggleChat()"><i class="fas fa-comment-dots" style="margin-right:8px;"></i>联系对方</button>
            ${actionBtn}
        `;
    } else {
        // 已完成/已取消 -> 隐藏底部栏
        footer.style.display = 'none';
    }

    // 4. 额外信息提示 (根据订单类型动态文案)
    const extraBox = document.getElementById('extra-info-box');
    
    // [新增] 地点动态映射
    let locationName = '指定地点';
    if (order.category === 'food') locationName = '食堂';
    else if (order.category === 'package') locationName = '驿站';
    else if (order.category === 'print') locationName = '可打印的教学楼';

    if (isOwner && order.status === 0) {
        extraBox.style.display = 'block';
        extraBox.innerHTML = '<i class="fas fa-info-circle"></i> 如需修改需求请先取消订单。';
    } else if (!isOwner && order.status === 1) {
        extraBox.style.display = 'block';
        // [动态显示] 根据类型显示不同地点
        extraBox.innerHTML = `<i class="fas fa-running"></i> 请尽快前往<strong>${locationName}</strong>完成配送任务。`;
    } else {
        extraBox.style.display = 'none';
    }
}

// --- 操作逻辑 ---
async function takeOrder(oid) {
    showConfirmModal('确认接单？', '接单后请尽快完成配送', async () => {
        try {
            await api.post(`/orders/${oid}/take`, { taker_id: currentUser.user_id });
            showToast('接单成功！');
            loadOrderData();
            if(window.reloadOrderList) window.reloadOrderList();
        } catch(e) { showToast(e.message); }
    });
}

async function cancelOrder(oid) {
    showConfirmModal('取消订单？', '取消后将无法恢复，确定要取消吗？', async () => {
        try {
            await api.post(`/orders/${oid}/cancel`, { user_id: currentUser.user_id });
            showToast('订单已取消');
            closeDetail();
            if(window.reloadOrderList) window.reloadOrderList();
        } catch(e) { showToast(e.message); }
    });
}

async function confirmDeliver(oid) {
    showConfirmModal('确认送达？', '确认已将物品送达给发布者？', async () => {
        try {
            await api.post(`/orders/${oid}/deliver`);
            showToast('已通知发布者验收');
            loadOrderData();
        } catch(e) { showToast(e.message); }
    });
}

async function confirmFinish(oid) {
    showConfirmModal('确认收货？', '确认收到物品并完成订单？', async () => {
        try {
            await api.post(`/orders/${oid}/finish`);
            document.getElementById('ratingModal').style.display = 'flex';
            if(window.reloadOrderList) window.reloadOrderList();
        } catch(e) { showToast(e.message); }
    });
}

async function submitRating() {
    document.getElementById('ratingModal').style.display = 'none';
    showToast('评价成功！');
    closeDetail();
}

function toggleChat() {
    const win = document.getElementById('chat-window');
    if (!win.style.display || win.style.display === 'none') {
        win.style.display = 'flex'; 
        loadChatHistory();
    } else {
        win.style.display = 'none';
    }
}

async function loadChatHistory() {
    const chatBody = document.getElementById('chat-history');
    if (!chatBody.innerHTML) {
        chatBody.innerHTML = '<div style="text-align:center;color:#ccc;font-size:12px;margin-bottom:10px;">- 历史消息 -</div>';
        const msgs = [
            { type: 'left', text: '你好，请问具体的取餐窗口是哪里？' },
            { type: 'right', text: '在二楼最左边的麻辣烫窗口，单号是 1024' },
            { type: 'left', text: '好的，我现在过去，大约10分钟到寝室楼下。' }
        ];
        msgs.forEach(m => {
            chatBody.innerHTML += `<div class="msg ${m.type}">${m.text}</div>`;
        });
    }
    chatBody.scrollTop = chatBody.scrollHeight;
}

async function sendMessage() {
    const input = document.getElementById('chat-input');
    const text = input.value.trim();
    if (!text) return;
    
    const chatBody = document.getElementById('chat-history');
    chatBody.innerHTML += `<div class="msg right">${text}</div>`;
    input.value = '';
    chatBody.scrollTop = chatBody.scrollHeight;
    
    setTimeout(() => {
        chatBody.innerHTML += `<div class="msg left">收到，路上注意安全。</div>`;
        chatBody.scrollTop = chatBody.scrollHeight;
    }, 1000);
}

function showToast(msg) {
    let toast = document.getElementById('toast-msg');
    if (!toast) {
        toast = document.createElement('div');
        toast.id = 'toast-msg';
        toast.style.cssText = 'position:fixed;top:50%;left:50%;transform:translate(-50%,-50%);background:rgba(0,0,0,0.7);color:#fff;padding:10px 20px;border-radius:8px;z-index:99999;font-size:14px;';
        document.body.appendChild(toast);
    }
    toast.innerText = msg;
    setTimeout(() => toast.remove(), 2000);
}