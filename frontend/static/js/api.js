/* /static/js/api.js */

class API {
    constructor(baseURL = '/api') {
        this.baseURL = baseURL;
    }

    getToken() {
        return localStorage.getItem('token');
    }

    async request(endpoint, method = 'GET', data = null) {
        const headers = {
            'Content-Type': 'application/json'
        };

        const token = this.getToken();
        if (token) {
            headers['Authorization'] = `Bearer ${token}`;
        }

        const config = {
            method,
            headers,
        };

        if (data) {
            config.body = JSON.stringify(data);
        }

        try {
            const response = await fetch(`${this.baseURL}${endpoint}`, config);
            
            // --- 核心修复开始 ---
            if (response.status === 401) {
                // 如果是登录接口报 401，说明是账号密码错误，抛出错误让 UI 层处理
                // 而不是执行全局的“Token过期跳转”逻辑
                if (endpoint.includes('/auth/login')) {
                    throw new Error("账号或密码错误");
                }

                console.warn('Authentication failed, redirecting to login.');
                localStorage.clear();
                window.location.href = '/login';
                return; // 终止执行
            }
            // --- 核心修复结束 ---

            const result = await response.json();

            if (!response.ok) {
                throw new Error(result.message || '请求失败');
            }

            return result;
        } catch (error) {
            console.error('API Error:', error);
            // 统一弹窗提示错误（除非是静默检查）
            if (!endpoint.includes('check')) { 
                alert(error.message); 
            }
            throw error; // 继续抛出，让调用方也能感知错误
        }
    }

    get(endpoint) {
        return this.request(endpoint, 'GET');
    }

    post(endpoint, data) {
        return this.request(endpoint, 'POST', data);
    }
}

window.api = new API();