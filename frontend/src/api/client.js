import axios from "axios";

/**
 * Single axios instance so every page shares the base URL, the auth header
 * and the 401 handling. Talks only to FastAPI — never directly to models.
 */
const apiClient = axios.create({
  baseURL: "/api",
  headers: { "Content-Type": "application/json" },
});

apiClient.interceptors.request.use((config) => {
  const token = localStorage.getItem("access_token");
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }

  // Let the browser set the multipart boundary itself.
  if (config.data instanceof FormData) {
    delete config.headers["Content-Type"];
  }

  return config;
});

apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    const status = error.response?.status;

    // An expired or revoked token must not leave the user staring at a
    // dashboard full of failed requests. Clear it and bounce to login.
    // `/auth/login` itself is excluded — a wrong password is a 401 too, and
    // that one belongs to the form, not the session.
    const isLoginAttempt = error.config?.url?.includes("/auth/login");

    if (status === 401 && !isLoginAttempt) {
      localStorage.removeItem("access_token");
      window.dispatchEvent(new Event("deepshield:unauthorized"));
    }

    return Promise.reject(error);
  }
);

/** Normalises an axios error into a displayable string. */
export function apiError(error, fallback = "Something went wrong.") {
  const detail = error?.response?.data?.detail;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail) && detail[0]?.msg) return detail[0].msg;
  if (error?.message === "Network Error") {
    return "Cannot reach the API. Is the backend running on port 8000?";
  }
  return fallback;
}

export default apiClient;
