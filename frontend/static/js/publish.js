/* /static/js/publish.js */
document.addEventListener('DOMContentLoaded', () => {
    const form = document.getElementById('publish-form');
    
    if (form) {
        form.addEventListener('submit', async (e) => {
            e.preventDefault();
            
            const formData = new FormData(form);
            const data = Object.fromEntries(formData.entries());
            data.category = form.dataset.category;
            if (data.tags) data.tags = [data.tags]; else data.tags = [];
            
            // [修改] 前端虽设置，后端会再次校验并强制扣除20
            data.reward_points = 20;
            if (data.file_pages) data.file_pages = parseInt(data.file_pages);

            try {
                await window.api.post('/orders/create', data);
                alert("订单已发出！扣除 20 积分。");
                window.location.href = '/'; 
            } catch (error) {
                console.error('Publish failed', error);
                // 错误已由 api.js 弹窗
            }
        });
    }
});