/* /static/js/home.js */
document.addEventListener('DOMContentLoaded', () => {
    const orderList = document.getElementById('order-list');
    const emptyState = document.getElementById('empty-state');
    const loadingSpinner = document.getElementById('loading-spinner');
    
    // 获取当前分类参数
    const urlParams = new URLSearchParams(window.location.search);
    let currentCategory = urlParams.get('category') || 'all';
    
    // 高亮底部导航栏
    document.querySelectorAll('.bottom-nav-item').forEach(item => {
        item.classList.remove('active');
        if (item.dataset.category === currentCategory) {
            item.classList.add('active');
        }
    });
    
    // 高亮 PC 端侧边栏
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
            // [新增] 获取当前登录用户信息用于比对
            const currentUserStr = localStorage.getItem('user');
            const currentUser = currentUserStr ? JSON.parse(currentUserStr) : {};

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
                orderList.appendChild(createOrderCard(order, currentUser));
            });

        } catch (error) {
            loadingSpinner.style.display = 'none';
            console.error(error);
        }
    }

    function createOrderCard(order, currentUser) {
        const div = document.createElement('div');
        div.className = 'card fade-in';
        
        // 状态标签生成
        let statusHtml = '';
        if(order.status === 1) statusHtml = '<span class="tag tag-running" style="margin-left:auto;">配送中</span>';
        else if(order.status === 2) statusHtml = '<span class="tag tag-running" style="margin-left:auto;">待收货</span>';
        else if(order.status === 3) statusHtml = '<span class="tag" style="background:#CBD5E0;margin-left:auto;">已完成</span>';

        // [新增] “我发布的” 标签逻辑
        let myPostHtml = '';
        // 注意：API 返回的是 int, localStorage 可能是 string，转 string 比对最稳
        if (currentUser && String(order.requester_id) === String(currentUser.user_id)) {
            myPostHtml = '<span class="tag tag-mine" style="margin-right: 6px;">我发布的</span>';
        }

        div.onclick = () => openDetail(order.order_id);

        const iconMap = { 'food': 'fa-hamburger', 'package': 'fa-box-open', 'print': 'fa-print' };
        let title = order.description || '无描述';
        if (title.length > 25) title = title.substring(0, 25) + '...';

        div.innerHTML = `
            <div class="card-avatar" data-category="${order.category}">
                <i class="fas ${iconMap[order.category] || 'fa-running'}"></i>
            </div>
            <div class="card-body">
                <div class="card-title" style="display:flex; justify-content:space-between; align-items:center;">
                    <div style="display:flex; align-items:center; overflow:hidden;">
                        ${myPostHtml}
                        <span style="white-space:nowrap; overflow:hidden; text-overflow:ellipsis;">${title}</span>
                    </div>
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
        if (window.cleanupDetailLogic) {
            window.cleanupDetailLogic();
        }

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