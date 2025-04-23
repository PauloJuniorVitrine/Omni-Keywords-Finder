import axios from 'axios';
import { toast } from 'react-toastify';

const apiClient = axios.create({
  baseURL: '/api',
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json'
  }
});

// Adiciona cabeçalho X-Request-ID para rastreamento
apiClient.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token');
    if (token) {
      config.headers['Authorization'] = `Bearer ${token}`;
    }

    config.headers['X-Request-ID'] = crypto.randomUUID();

    // Remove Content-Type se for FormData (upload)
    if (config.data instanceof FormData) {
      delete config.headers['Content-Type'];
    }

    return config;
  },
  (error) => Promise.reject(error)
);

// Interceptor de resposta para erros globais e renovação de token
apiClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;
    const status = error.response?.status;
    const message = error.response?.data?.message || 'Erro inesperado na API';

    // Se não for erro de auth ou se já tentou renovar, mostra erro
    if (status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;
      try {
        const refreshToken = localStorage.getItem('refreshToken');
        const { data } = await axios.post('/api/auth/refresh-token', { refreshToken });

        localStorage.setItem('token', data.token);
        originalRequest.headers['Authorization'] = `Bearer ${data.token}`;
        return apiClient(originalRequest);
      } catch (refreshError) {
        localStorage.removeItem('token');
        localStorage.removeItem('refreshToken');
        window.location.href = '/login';
        return Promise.reject(refreshError);
      }
    }

    toast.error(message);
    return Promise.reject(error);
  }
);

export default apiClient;
