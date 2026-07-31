export const getApiUrl = () => {
  // Use REACT_APP_API_URL from environment, fallback to localhost for local dev
  return import.meta.env.REACT_APP_API_URL || 'http://localhost:8000';
};

export const apiCall = async (endpoint, options = {}) => {
  const url = `${getApiUrl()}${endpoint}`;
  return fetch(url, options);
};
