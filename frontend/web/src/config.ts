export const API_BASE = (() => {
  if (typeof window === "undefined") return "http://127.0.0.1:8000";
  return process.env.REACT_APP_API_URL || import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";
})();
