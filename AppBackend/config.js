/**
 * Backend API Configuration
 * 
 * This file contains the configuration for connecting to the Django REST Framework backend.
 * Update the BASE_URL to match your backend server address.
 */

// Base URL for the Django backend API
// For local development: http://localhost:8000/api/v1
// For production: https://your-domain.com/api/v1
// For Android emulator: http://10.0.2.2:8000/api/v1
// For iOS simulator: http://localhost:8000/api/v1
// For physical device: http://YOUR_COMPUTER_IP:8000/api/v1

// Google OAuth 2.0 Web Client ID
// Get this from Google Cloud Console: https://console.cloud.google.com/
// Create OAuth 2.0 credentials > Web application
// IMPORTANT: Replace with your actual Google Client ID
// If this is not set, Google Sign-In will fail with a configuration error.
export const GOOGLE_WEB_CLIENT_ID = '882762364908-7msv9fqac3qne0dhvlvng7vtb3a2lf8j.apps.googleusercontent.com';

export const API_CONFIG = {
  BASE_URL: __DEV__
    ? 'http://10.0.2.2:8000/api/v1'  // Development
    : 'https://your-production-domain.com/api/v1',  // Production

  // Timeout for API requests (in milliseconds)
  TIMEOUT: 30000,

  // Endpoints
  ENDPOINTS: {
    // Authentication
    AUTH: {
      LOGIN: '/auth/jwt/create/',
      REFRESH: '/auth/jwt/refresh/',
      VERIFY: '/auth/jwt/verify/',
      REGISTER: '/auth/register/',
      GOOGLE_LOGIN: '/auth/google/',
    },

    // Products
    PRODUCTS: {
      LIST: '/products/',
      DETAIL: (id) => `/products/${id}/`,
      SEARCH: '/products/search/',
      SEARCH_SUGGESTIONS: '/products/search_suggestions/',
      AI_SEARCH: '/products/ai_search/',
      HYBRID_SEARCH: '/products/hybrid_search/',
      TRENDING: '/products/trending/',
      PLATFORMS: '/products/platforms/',
      FILTER_OPTIONS: '/products/filter_options/',
      CATEGORY_MAPPINGS: '/products/category_mappings/',
      TRACK_VIEW: (id) => `/products/${id}/track_view/`,
    },

    // Categories
    CATEGORIES: {
      LIST: '/categories/',
      DETAIL: (id) => `/categories/${id}/`,
    },

    // Wishlist
    WISHLIST: {
      LIST: '/wishlist/',
      ADD: '/wishlist/add_product/',
      REMOVE: '/wishlist/remove_product/',
    },

    // User
    USER: {
      PROFILE: '/users/profile/',
    },
  },
};

/**
 * PostgreSQL Database Configuration
 * 
 * The backend uses PostgreSQL. Configuration is stored in backend/buyvaulthub/settings.py
 * 
 * Default configuration (from settings.py):
 * - Database Name: buyvaulthub_db (configurable via DATABASE_NAME env var)
 * - User: postgres (configurable via DATABASE_USER env var)
 * - Password: (configurable via DATABASE_PASSWORD env var)
 * - Host: localhost (configurable via DATABASE_HOST env var)
 * - Port: 5432 (configurable via DATABASE_PORT env var)
 * 
 * To configure PostgreSQL:
 * 1. Install PostgreSQL on your system
 * 2. Create a database: createdb buyvaulthub_db
 * 3. Set environment variables in backend/.env or export them:
 *    - DATABASE_NAME=buyvaulthub_db
 *    - DATABASE_USER=postgres
 *    - DATABASE_PASSWORD=your_password
 *    - DATABASE_HOST=localhost
 *    - DATABASE_PORT=5432
 * 4. Run migrations: cd backend && python manage.py migrate
 * 5. Import data from backups if needed
 */
