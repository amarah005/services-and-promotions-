/**
 * API Service Layer
 * 
 * This module provides high-level API methods for the React Native app.
 * All methods use the ApiClient for making requests.
 */

import apiClient from './apiClient';
import { API_CONFIG } from './config';

// ============================================================================
// Authentication API
// ============================================================================

export const authAPI = {
  /**
   * Login with username and password
   * Returns: { access, refresh, user }
   */
  async login(username, password) {
    try {
      const response = await apiClient.post(API_CONFIG.ENDPOINTS.AUTH.LOGIN, {
        username,
        password,
      });

      // Store tokens
      if (response.access && response.refresh) {
        await apiClient.setTokens(response.access, response.refresh);
      }

      return response;
    } catch (error) {
      throw new Error(error.message || 'Login failed');
    }
  },

  /**
   * Register new user
   * Returns: { access, refresh, user } or { token, user_id, username, email, ... }
   */
  async register(userData) {
    try {
      const response = await apiClient.post(API_CONFIG.ENDPOINTS.AUTH.REGISTER, {
        username: userData.username,
        email: userData.email,
        password: userData.password,
        first_name: userData.first_name || '',
        last_name: userData.last_name || '',
      });

      // Handle both JWT and token-based responses
      if (response.access && response.refresh) {
        await apiClient.setTokens(response.access, response.refresh);
      } else if (response.token) {
        // Legacy token-based auth
        await apiClient.setTokens(response.token, null);
      }

      return response;
    } catch (error) {
      throw new Error(error.message || 'Registration failed');
    }
  },

  /**
   * Google login
   */
  async googleLogin(idToken) {
    try {
      const response = await apiClient.post(API_CONFIG.ENDPOINTS.AUTH.GOOGLE_LOGIN, {
        id_token: idToken,
      });

      if (response.access && response.refresh) {
        await apiClient.setTokens(response.access, response.refresh);
      }

      return response;
    } catch (error) {
      throw new Error(error.message || 'Google login failed');
    }
  },

  /**
   * Logout (clear tokens)
   */
  async logout() {
    await apiClient.clearTokens();
  },

  /**
   * Verify token
   */
  async verifyToken(token) {
    try {
      return await apiClient.post(API_CONFIG.ENDPOINTS.AUTH.VERIFY, { token });
    } catch (error) {
      throw new Error(error.message || 'Token verification failed');
    }
  },
};

// ============================================================================
// Products API
// ============================================================================

export const productsAPI = {
  /**
   * Get all products with optional filters
   */
  async getProducts(params = {}) {
    try {
      return await apiClient.get(API_CONFIG.ENDPOINTS.PRODUCTS.LIST, params);
    } catch (error) {
      throw new Error(error.message || 'Failed to fetch products');
    }
  },

  /**
   * Get product by ID
   */
  async getProduct(id) {
    try {
      return await apiClient.get(API_CONFIG.ENDPOINTS.PRODUCTS.DETAIL(id));
    } catch (error) {
      throw new Error(error.message || 'Failed to fetch product');
    }
  },

  /**
   * Search products
   */
  async searchProducts(query, limit = 20) {
    try {
      return await apiClient.get(API_CONFIG.ENDPOINTS.PRODUCTS.SEARCH, {
        q: query,
        limit,
      });
    } catch (error) {
      throw new Error(error.message || 'Search failed');
    }
  },

  /**
   * Get search suggestions
   */
  async getSearchSuggestions(query, limit = 10) {
    try {
      return await apiClient.get(API_CONFIG.ENDPOINTS.PRODUCTS.SEARCH_SUGGESTIONS, {
        q: query,
        limit,
      });
    } catch (error) {
      throw new Error(error.message || 'Failed to get suggestions');
    }
  },

  /**
   * AI-powered semantic search
   */
  async aiSearch(query, limit = 20) {
    try {
      return await apiClient.get(API_CONFIG.ENDPOINTS.PRODUCTS.AI_SEARCH, {
        q: query,
        limit,
      });
    } catch (error) {
      throw new Error(error.message || 'AI search failed');
    }
  },

  /**
   * Hybrid search (AI + Full-text)
   */
  async hybridSearch(query, limit = 20) {
    try {
      return await apiClient.get(API_CONFIG.ENDPOINTS.PRODUCTS.HYBRID_SEARCH, {
        q: query,
        limit,
      });
    } catch (error) {
      throw new Error(error.message || 'Hybrid search failed');
    }
  },

  /**
   * Get trending products
   */
  async getTrending() {
    try {
      return await apiClient.get(API_CONFIG.ENDPOINTS.PRODUCTS.TRENDING);
    } catch (error) {
      throw new Error(error.message || 'Failed to fetch trending products');
    }
  },

  /**
   * Get platforms
   */
  async getPlatforms(category = '', subcategory = '') {
    try {
      const params = {};
      if (category) params.category = category;
      if (subcategory) params.subcategory = subcategory;
      return await apiClient.get(API_CONFIG.ENDPOINTS.PRODUCTS.PLATFORMS, params);
    } catch (error) {
      throw new Error(error.message || 'Failed to fetch platforms');
    }
  },

  /**
   * Get filter options
   */
  async getFilterOptions(mainCategory = '', subcategory = '') {
    try {
      const params = {};
      if (mainCategory) params.main_category = mainCategory;
      if (subcategory) params.subcategory = subcategory;
      return await apiClient.get(API_CONFIG.ENDPOINTS.PRODUCTS.FILTER_OPTIONS, params);
    } catch (error) {
      throw new Error(error.message || 'Failed to fetch filter options');
    }
  },

  /**
   * Get category mappings
   */
  async getCategoryMappings() {
    try {
      return await apiClient.get(API_CONFIG.ENDPOINTS.PRODUCTS.CATEGORY_MAPPINGS);
    } catch (error) {
      throw new Error(error.message || 'Failed to fetch category mappings');
    }
  },

  /**
   * Track product view
   */
  async trackView(productId) {
    try {
      return await apiClient.post(API_CONFIG.ENDPOINTS.PRODUCTS.TRACK_VIEW(productId));
    } catch (error) {
      // Don't throw error for view tracking failures
      console.error('Failed to track view:', error);
    }
  },
};

// ============================================================================
// Categories API
// ============================================================================

export const categoriesAPI = {
  /**
   * Get all categories
   */
  async getCategories() {
    try {
      let allCategories = [];
      let nextUrl = API_CONFIG.ENDPOINTS.CATEGORIES.LIST;

      while (nextUrl) {
        // Handle full URL or relative path
        const endpoint = nextUrl.replace(API_CONFIG.BASE_URL, '');
        const response = await apiClient.get(endpoint);

        // Handle different response structures
        const data = response.results || response;

        if (Array.isArray(data)) {
          allCategories = allCategories.concat(data);
        }

        // Check for next page
        if (response.next) {
          nextUrl = response.next;
        } else {
          nextUrl = null;
        }
      }

      return allCategories;
    } catch (error) {
      throw new Error(error.message || 'Failed to fetch categories');
    }
  },

  /**
   * Get category by ID
   */
  async getCategory(id) {
    try {
      return await apiClient.get(API_CONFIG.ENDPOINTS.CATEGORIES.DETAIL(id));
    } catch (error) {
      throw new Error(error.message || 'Failed to fetch category');
    }
  },
};

// ============================================================================
// Wishlist API
// ============================================================================

export const wishlistAPI = {
  /**
   * Get user's wishlist
   */
  async getWishlist() {
    try {
      return await apiClient.get(API_CONFIG.ENDPOINTS.WISHLIST.LIST);
    } catch (error) {
      throw new Error(error.message || 'Failed to fetch wishlist');
    }
  },

  /**
   * Add product to wishlist
   */
  async addToWishlist(productId) {
    try {
      return await apiClient.post(API_CONFIG.ENDPOINTS.WISHLIST.ADD, {
        product_id: productId,
      });
    } catch (error) {
      throw new Error(error.message || 'Failed to add to wishlist');
    }
  },

  /**
   * Remove product from wishlist
   */
  async removeFromWishlist(productId) {
    try {
      return await apiClient.post(API_CONFIG.ENDPOINTS.WISHLIST.REMOVE, {
        product_id: productId,
      });
    } catch (error) {
      throw new Error(error.message || 'Failed to remove from wishlist');
    }
  },

  /**
   * Check if product is in wishlist
   */
  async isInWishlist(productId) {
    try {
      const wishlist = await this.getWishlist();
      return wishlist.some(item => item.product?.id === productId);
    } catch (error) {
      return false;
    }
  },
};

// ============================================================================
// User API
// ============================================================================

export const userAPI = {
  /**
   * Get user profile
   */
  async getProfile() {
    try {
      return await apiClient.get(API_CONFIG.ENDPOINTS.USER.PROFILE);
    } catch (error) {
      throw new Error(error.message || 'Failed to fetch profile');
    }
  },

  /**
   * Update user profile
   */
  async updateProfile(data) {
    try {
      return await apiClient.put(API_CONFIG.ENDPOINTS.USER.PROFILE, data);
    } catch (error) {
      throw new Error(error.message || 'Failed to update profile');
    }
  },
};
