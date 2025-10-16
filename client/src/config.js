// API Configuration
const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:5000';

// Helper function for authenticated API calls
export async function authenticatedFetch(url, options = {}) {
  const token = localStorage.getItem('authToken');

  if (!token) {
    throw new Error('Not authenticated');
  }

  const headers = {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${token}`,
    ...options.headers
  };

  return fetch(url, { ...options, headers });
}

export default API_URL;
