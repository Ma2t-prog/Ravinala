import axios, { type AxiosError } from "axios";

const TOKEN_KEY = "access_token";

const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL ?? "",
  timeout: 90000,
  headers: {
    "Content-Type": "application/json",
  },
});

// Attach JWT token to every request
api.interceptors.request.use((config) => {
  const token = localStorage.getItem(TOKEN_KEY);
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

api.interceptors.response.use(
  (response) => response,
  (error: AxiosError) => {
    const status = error.response?.status;
    const url = error.config?.url ?? "unknown endpoint";

    if (status === 401) {
      localStorage.removeItem(TOKEN_KEY);
      console.error(`[API] Unauthorized: ${url}`);
    } else if (status === 404) {
      console.error(`[API] Not found: ${url}`);
    } else if (status === 422) {
      console.error(`[API] Validation error on ${url}:`, error.response?.data);
    } else if (status === 500) {
      console.error(`[API] Server error on ${url}:`, error.response?.data);
    } else if (error.code === "ECONNABORTED") {
      console.error(`[API] Request timed out: ${url}`);
    } else if (!error.response) {
      console.error(
        `[API] Network error — backend may be unreachable (${url})`,
      );
    } else {
      console.error(
        `[API] Unexpected error ${status} on ${url}:`,
        error.response?.data,
      );
    }

    return Promise.reject(error);
  },
);

export default api;
