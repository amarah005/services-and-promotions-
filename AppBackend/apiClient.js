/**
 * API Client for React Native 
 * 
 * This module provides a centralized API client with:
 * - JWT token management
 * - Automatic token refresh
 * - Request/response interceptors
 * - Error handling
 */

import AsyncStorage from '@react-native-async-storage/async-storage';
import { API_CONFIG } from './config';

const BASE_URL = API_CONFIG.BASE_URL;
const TIMEOUT = API_CONFIG.TIMEOUT;

// Token storage keys
const ACCESS_TOKEN_KEY = 'access_token';
const REFRESH_TOKEN_KEY = 'refresh_token';

class ApiClient {
  constructor() {
    this.baseURL = BASE_URL;
    this.timeout = TIMEOUT;
    this.isRefreshing = false;
    this.failedQueue = [];
  }

  /**
   * Get stored access token
   */
  async getAccessToken() {
    try {
      return await AsyncStorage.getItem(ACCESS_TOKEN_KEY);
    } catch (error) {
      console.error('Error getting access token:', error);
      return null;
    }
  }

  /**
   * Get stored refresh token
   */
  async getRefreshToken() {
    try {
      return await AsyncStorage.getItem(REFRESH_TOKEN_KEY);
    } catch (error) {
      console.error('Error getting refresh token:', error);
      return null;
    }
  }

  /**
   * Store tokens
   */
  async setTokens(access, refresh) {
    try {
      await AsyncStorage.setItem(ACCESS_TOKEN_KEY, access);
      if (refresh) {
        await AsyncStorage.setItem(REFRESH_TOKEN_KEY, refresh);
      }
    } catch (error) {
      console.error('Error storing tokens:', error);
    }
  }

  /**
   * Clear tokens (logout)
   */
  async clearTokens() {
    try {
      await AsyncStorage.removeItem(ACCESS_TOKEN_KEY);
      await AsyncStorage.removeItem(REFRESH_TOKEN_KEY);
    } catch (error) {
      console.error('Error clearing tokens:', error);
    }
  }

  /**
   * Refresh access token using refresh token
   */
  async refreshAccessToken() {
    if (this.isRefreshing) {
      // Wait for ongoing refresh
      return new Promise((resolve, reject) => {
        this.failedQueue.push({ resolve, reject });
      });
    }

    this.isRefreshing = true;

    try {
      const refreshToken = await this.getRefreshToken();
      if (!refreshToken) {
        throw new Error('No refresh token available');
      }

      const response = await fetch(`${this.baseURL}${API_CONFIG.ENDPOINTS.AUTH.REFRESH}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ refresh: refreshToken }),
      });

      if (!response.ok) {
        throw new Error('Token refresh failed');
      }

      const data = await response.json();
      await this.setTokens(data.access, data.refresh || refreshToken);

      // Process queued requests
      this.failedQueue.forEach(({ resolve }) => resolve(data.access));
      this.failedQueue = [];

      return data.access;
    } catch (error) {
      // Process queued requests with error
      this.failedQueue.forEach(({ reject }) => reject(error));
      this.failedQueue = [];

      // Clear tokens on refresh failure
      await this.clearTokens();
      throw error;
    } finally {
      this.isRefreshing = false;
    }
  }

  /**
   * Make API request with automatic token management
   */
  async request(endpoint, options = {}) {
    const url = endpoint.startsWith('http') ? endpoint : `${this.baseURL}${endpoint}`;

    const defaultHeaders = {
      'Content-Type': 'application/json',
      'Accept': 'application/json',
    };

    // Add authorization header if token exists
    const accessToken = await this.getAccessToken();
    if (accessToken) {
      defaultHeaders['Authorization'] = `Bearer ${accessToken}`;
    }

    const config = {
      ...options,
      headers: {
        ...defaultHeaders,
        ...options.headers,
      },
    };

    try {
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), this.timeout);

      const response = await fetch(url, {
        ...config,
        signal: controller.signal,
      });

      clearTimeout(timeoutId);

      // Handle 401 Unauthorized - try to refresh token
      if (response.status === 401 && accessToken) {
        try {
          const newAccessToken = await this.refreshAccessToken();
          // Retry request with new token
          config.headers['Authorization'] = `Bearer ${newAccessToken}`;
          const retryResponse = await fetch(url, {
            ...config,
            signal: controller.signal,
          });
          return this.handleResponse(retryResponse);
        } catch (refreshError) {
          // Refresh failed, clear tokens and throw error
          await this.clearTokens();
          throw new Error('Authentication failed. Please login again.');
        }
      }

      return this.handleResponse(response);
    } catch (error) {
      if (error.name === 'AbortError') {
        throw new Error('Request timeout. Please check your connection.');
      }
      throw error;
    }
  }

  /**
   * Handle API response
   */
  async handleResponse(response) {
    const contentType = response.headers.get('content-type');

    if (!response.ok) {
      let errorMessage = `Request failed with status ${response.status}`;

      if (contentType && contentType.includes('application/json')) {
        try {
          const errorData = await response.json();
          errorMessage = errorData.error || errorData.detail || errorMessage;
        } catch (e) {
          // Ignore JSON parse errors
        }
      }

      const error = new Error(errorMessage);
      error.status = response.status;
      throw error;
    }

    // Handle empty responses
    if (response.status === 204) {
      return null;
    }

    // Parse JSON response
    if (contentType && contentType.includes('application/json')) {
      return await response.json();
    }

    // Return text response
    return await response.text();
  }

  // Convenience methods
  async get(endpoint, params = {}) {
    const queryString = new URLSearchParams(params).toString();
    const url = queryString ? `${endpoint}?${queryString}` : endpoint;
    return this.request(url, { method: 'GET' });
  }

  async post(endpoint, data = {}) {
    return this.request(endpoint, {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async put(endpoint, data = {}) {
    return this.request(endpoint, {
      method: 'PUT',
      body: JSON.stringify(data),
    });
  }

  async patch(endpoint, data = {}) {
    return this.request(endpoint, {
      method: 'PATCH',
      body: JSON.stringify(data),
    });
  }

  async delete(endpoint) {
    return this.request(endpoint, { method: 'DELETE' });
  }
}

// Export singleton instance
export default new ApiClient();
