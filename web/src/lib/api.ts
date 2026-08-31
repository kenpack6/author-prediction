import axios, { type AxiosInstance } from 'axios'

export const api: AxiosInstance = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || '/api',
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Global response interceptor for consistent error handling
api.interceptors.response.use(
  (response) => response,
  (error) => {
    // Handle errors globally if needed
    return Promise.reject(error)
  },
)

export default api
