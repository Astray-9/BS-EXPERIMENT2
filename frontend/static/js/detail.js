/* /static/js/detail.js */

let currentOrderId = null;
let currentUser = null;
let currentOrderData = null;
let statusPollingInterval = null; 

// 全局入口
window.initDetailLogic = async function(orderId) {
    currentOrderId = orderId;
    currentUser = JSON.parse(localStorage.getItem('user') || '{}');
    
    // 1. 立即加载一次数据
    await loadOrderData();

    // 2. 启动轮询
    if (statusPollingInterval) clearInterval(statusPollingInterval);
    
    statusPollingInterval = setInterval(async () => {
        try {
            const res = await api.get(`/orders/${currentOrderId}`);
            const newOrder = res.data;

            // 只有当状态发生改变时才刷新UI，避免页面闪烁
            // 注意：如果后端在轮询中返回了新消息，这里也可以扩展逻辑去刷新聊天，
            // 但为了简化，目前只针对状态改变和完成弹窗
            if (currentOrderData && newOrder.status !== currentOrderData.status) {
                console.log('订单状态更新:', newOrder.status);
                currentOrderData = newOrder;
                updateUI(currentOrderData);

                if (currentOrderData.status === 3) {
                     document.getElementById('ratingModal').style.display = 'flex';
                     clearInterval(statusPollingInterval); 
                }
            }
            // 每次轮询更新数据缓存，以便聊天窗口打开时能看到最新消息
            currentOrderData = newOrder;
            
            // 如果聊天窗口是打开的，尝试刷新消息（简单的追加逻辑需更复杂处理，这里仅更新数据源）
            // 若要实时聊天，建议在 openChat 时单独轮询消息接口。
        } catch(e) { console.error("轮询状态失败", e); }
    }, 3000);
    
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

    // 3. 底部按钮逻辑
    const actions = document.getElementById('panel-actions');
    const footer = document.querySelector('.panel-footer');
    
    // 判定是否为发布者
    const isOwner = String(order.requester_id) === String(currentUser.user_id);
    
    footer.className = 'panel-footer'; 
    footer.style.display = 'grid'; 

    if (order.status === 0) {
        // 待接单状态
        if (isOwner) {
            // [我是发布者]
            actions.innerHTML = `
                <button class="btn btn-secondary-outline" onclick="toggleChat()"><i class="fas fa-comment-dots" style="margin-right:8px;"></i>联系</button>
                <button class="btn btn-danger" onclick="cancelOrder('${order.order_id}')">取消订单</button>
            `;
        } else {
            // [我是路人]
            footer.classList.add('single-btn');
            actions.innerHTML = `<button class="btn btn-submit btn-block" onclick="takeOrder('${order.order_id}')" style="background:#3182CE;color:#fff;">立即接单</button>`;
        }
    } else if (order.status === 1 || order.status === 2) {
        // 配送中 / 待收货状态
        let actionBtn = '';
        
        if (isOwner) {
             // [我是发布者]
             actionBtn = `<button class="btn btn-submit" style="background:#0F172A;color:#fff;" onclick="confirmFinish('${order.order_id}')">确认收货</button>`;
        } else if (String(order.runner_id) === String(currentUser.user_id)) {
             // [我是接单者]
             actionBtn = `<button class="btn btn-submit" style="background:#48BB78;color:#fff;" onclick="confirmDeliver('${order.order_id}')">确认送达</button>`;
        }
            
        actions.innerHTML = `
            <button class="btn btn-secondary-outline" onclick="toggleChat()"><i class="fas fa-comment-dots" style="margin-right:8px;"></i>联系对方</button>
            ${actionBtn}
        `;
    } else {
        // 已完成/已取消
        footer.style.display = 'none';
    }

    // 4. 额外信息提示
    const extraBox = document.getElementById('extra-info-box');
    let locationName = '指定地点';
    if (order.category === 'food') locationName = '食堂';
    else if (order.category === 'package') locationName = '驿站';
    else if (order.category === 'print') locationName = '可打印的教学楼';

    if (isOwner && order.status === 0) {
        extraBox.style.display = 'block';
        extraBox.innerHTML = '<i class="fas fa-info-circle"></i> 如需修改需求请先取消订单。';
    } else if (!isOwner && order.status === 1) {
        extraBox.style.display = 'block';
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

// [修改] 移除硬编码测试消息，改为渲染真实数据
async function loadChatHistory() {
    const chatBody = document.getElementById('chat-history');
    
    // 重置内容
    chatBody.innerHTML = '<div style="text-align:center;color:#ccc;font-size:12px;margin-bottom:10px;">- 历史消息 -</div>';
    
    // 渲染 currentOrderData 中的消息
    if (currentOrderData && currentOrderData.messages && currentOrderData.messages.length > 0) {
        currentOrderData.messages.forEach(msg => {
            // 简单判断发送者：如果发送者ID等于当前用户ID，显示在右侧(right)，否则在左侧(left)
            const isMe = String(msg.sender_id) === String(currentUser.user_id);
            const type = isMe ? 'right' : 'left';
            
            chatBody.innerHTML += `<div class="msg ${type}">${msg.content}</div>`;
        });
    } else {
        chatBody.innerHTML += '<div style="text-align:center;color:#eee;font-size:12px;">暂无更多消息</div>';
    }
    
    chatBody.scrollTop = chatBody.scrollHeight;
}

async function sendMessage() {
    const input = document.getElementById('chat-input');
    const text = input.value.trim();
    if (!text) return;
    
    // 1. 立即上屏（乐观UI）
    const chatBody = document.getElementById('chat-history');
    chatBody.innerHTML += `<div class="msg right">${text}</div>`;
    chatBody.scrollTop = chatBody.scrollHeight;
    
    // 2. 发送给后端
    try {
        await api.post(`/orders/${currentOrderId}/chat`, {
            content: text,
            type: 'text'
        });
        
        // 3. [修改] 移除自动回复的测试代码
        input.value = '';
        
        // 重新加载数据以确保同步（可选）
        // await loadOrderData(); 
    } catch(e) {
        showToast("发送失败");
        console.error(e);
    }
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

window.cleanupDetailLogic = function() {
    if (statusPollingInterval) {
        clearInterval(statusPollingInterval);
        statusPollingInterval = null;
        console.log('详情页轮询已停止');
    }
};