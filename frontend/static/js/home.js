/* /static/js/home.js */
document.addEventListener('DOMContentLoaded', () => {
    const orderList = document.getElementById('order-list');
    const emptyState = document.getElementById('empty-state');
    const loadingSpinner = document.getElementById('loading-spinner');
    
    // 获取当前分类参数
    const urlParams = new URLSearchParams(window.location.search);
    let currentCategory = urlParams.get('category') || 'all';
    
    // [修复] 高亮底部导航栏 (适配新的 bottom-nav-item 类名)
    document.querySelectorAll('.bottom-nav-item').forEach(item => {
        item.classList.remove('active');
        if (item.dataset.category === currentCategory) {
            item.classList.add('active');
        }
    });
    
    // 同时也高亮 PC 端的侧边栏
    document.querySelectorAll('.nav-item').forEach(item => {
        item.classList.remove('active');
        if (item.dataset.category === currentCategory) {
            item.classList.add('active');
        }
    });

    loadOrders(currentCategory);
    
    // 暴露刷新方法
    window.reloadOrderList = () => loadOrders(currentCategory);

    async function loadOrders(category) {
        if(!loadingSpinner || !orderList) return;
        loadingSpinner.style.display = 'block';
        orderList.innerHTML = '';
        if(emptyState) emptyState.style.display = 'none';

        try {
            // [核心修复] 请求 active 状态，显示所有未结束的订单 (0,1,2)
            // 这样用户接单后，订单依然显示在列表中（状态变为配送中）
            let endpoint = '/orders/list?status=active';
            
            if (category && category !== 'all') {
                endpoint += `&category=${category}`;
            }

            const res = await window.api.get(endpoint);
            const orders = res.data || [];
            loadingSpinner.style.display = 'none';

            if (orders.length === 0) {
                if(emptyState) emptyState.style.display = 'block';
                return;
            }

            orders.forEach(order => {
                orderList.appendChild(createOrderCard(order));
            });

        } catch (error) {
            loadingSpinner.style.display = 'none';
            console.error(error);
        }
    }

    function createOrderCard(order) {
        const div = document.createElement('div');
        div.className = 'card fade-in';
        
        // 状态标签生成
        let statusHtml = '';
        if(order.status === 1) statusHtml = '<span class="tag tag-running" style="margin-left:auto;">配送中</span>';
        else if(order.status === 2) statusHtml = '<span class="tag tag-running" style="margin-left:auto;">待收货</span>';
        else if(order.status === 3) statusHtml = '<span class="tag" style="background:#CBD5E0;margin-left:auto;">已完成</span>';

        div.onclick = () => openDetail(order.order_id);

        const iconMap = { 'food': 'fa-hamburger', 'package': 'fa-box-open', 'print': 'fa-print' };
        let title = order.description || '无描述';
        if (title.length > 25) title = title.substring(0, 25) + '...';

        div.innerHTML = `
            <div class="card-avatar" data-category="${order.category}">
                <i class="fas ${iconMap[order.category] || 'fa-running'}"></i>
            </div>
            <div class="card-body">
                <div class="card-title" style="display:flex; justify-content:space-between;">
                    <span>${title}</span>
                    ${statusHtml}
                </div>
                <div class="card-meta"><span>200m</span><span>•</span><span>刚刚</span></div>
            </div>
            <div class="card-price">¥${order.reward_points}</div>
        `;
        return div;
    }

    // --- 详情页逻辑 ---
    window.openDetail = async function(orderId) {
        document.getElementById('main-market-area').classList.add('blur-mode');
        const container = document.getElementById('detail-overlay-container');
        container.classList.add('active');
        
        try {
            const response = await fetch(`/orders/${orderId}?partial=true`);
            const html = await response.text();
            container.innerHTML = html;
            
            setTimeout(() => {
                const panel = container.querySelector('.right-slide-panel');
                if(panel) panel.classList.add('open');
            }, 10);

            const oldScript = document.getElementById('detail-script');
            if(oldScript) oldScript.remove();

            const script = document.createElement('script');
            script.id = 'detail-script';
            script.src = '/static/js/detail.js';
            script.onload = () => {
                if (window.initDetailLogic) window.initDetailLogic(orderId);
            };
            document.body.appendChild(script);

        } catch(e) { console.error(e); }
    }

    window.closeDetail = function() {
        document.getElementById('main-market-area').classList.remove('blur-mode');
        const container = document.getElementById('detail-overlay-container');
        const panel = container.querySelector('.right-slide-panel');
        if(panel) panel.classList.remove('open');
        setTimeout(() => {
            container.classList.remove('active');
            container.innerHTML = '';
        }, 300);
    }
});