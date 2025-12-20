/* 认证逻辑 */

document.addEventListener('DOMContentLoaded', () => {
    const loginForm = document.getElementById('login-form');
    const registerForm = document.getElementById('register-form');

    // 登录逻辑
    if (loginForm) {
        loginForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const student_id = document.getElementById('student_id').value;
            const password = document.getElementById('password').value;
            const btn = loginForm.querySelector('button');

            // 1. 设置按钮加载状态
            const originalText = btn.innerHTML;
            btn.disabled = true;
            btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> 登录中...';

            try {
                // POST /api/auth/login
                const res = await api.post('/auth/login', { student_id, password });
                
                // 2. 检查返回数据
                if (res && res.token) {
                    localStorage.setItem('token', res.token);
                    localStorage.setItem('user', JSON.stringify(res.user));
                    window.location.href = '/';
                } else {
                    // 如果 api.js 没有抛错但也没返回 token (罕见情况)
                    alert("登录失败：服务器未返回凭证");
                    btn.disabled = false;
                    btn.innerHTML = originalText;
                }
            } catch (error) {
                // 错误已被 api.js 的 alert 弹出，这里只需恢复按钮
                console.error('Login flow error', error);
                btn.disabled = false;
                btn.innerHTML = originalText;
            }
        });
    }

    // 注册逻辑
    if (registerForm) {
        registerForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const student_id = document.getElementById('student_id').value;
            const name = document.getElementById('name').value;
            const password = document.getElementById('password').value;
            const confirm_password = document.getElementById('confirm_password').value;
            const btn = registerForm.querySelector('button');

            if (password !== confirm_password) {
                alert("两次输入的密码不一致");
                return;
            }

            // 按钮加载状态
            const originalText = btn.innerHTML;
            btn.disabled = true;
            btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> 注册中...';

            try {
                await api.post('/auth/register', { student_id, name, password });
                alert('注册成功，请登录');
                window.location.href = '/login';
            } catch (error) {
                btn.disabled = false;
                btn.innerHTML = originalText;
            }
        });
    }
});