# AppBackend Integration

This folder contains the backend API integration for the React Native BuyVaultHub app.

## Overview

The AppBackend folder provides a complete API client layer that connects the React Native app to the Django REST Framework backend. It includes:

- **config.js**: API configuration and endpoint definitions
- **apiClient.js**: Low-level HTTP client with JWT token management
- **api.js**: High-level API service methods

## Features

- ✅ JWT Authentication with automatic token refresh
- ✅ Request/response interceptors
- ✅ Error handling
- ✅ Token persistence using AsyncStorage
- ✅ Support for all backend endpoints

## Setup

### 1. Install Dependencies

The required dependency `@react-native-async-storage/async-storage` has been installed.

### 2. Configure Backend URL

Edit `AppBackend/config.js` and update the `BASE_URL`:

```javascript
export const API_CONFIG = {
  BASE_URL: __DEV__ 
    ? 'http://localhost:8000/api/v1'  // Development
    : 'https://your-production-domain.com/api/v1',  // Production
  // ...
};
```

**Important Notes:**
- **Android Emulator**: Use `http://10.0.2.2:8000/api/v1`
- **iOS Simulator**: Use `http://localhost:8000/api/v1`
- **Physical Device**: Use `http://YOUR_COMPUTER_IP:8000/api/v1`

### 3. Start Backend Server

Make sure your Django backend is running:

```bash
cd backend
python manage.py runserver
```

## API Endpoints

### Authentication
- `POST /auth/jwt/create/` - Login
- `POST /auth/jwt/refresh/` - Refresh token
- `POST /auth/jwt/verify/` - Verify token
- `POST /auth/register/` - Register new user
- `POST /auth/google/` - Google login

### Products
- `GET /products/` - List products (with filters)
- `GET /products/{id}/` - Get product details
- `GET /products/search/` - Search products
- `GET /products/trending/` - Get trending products
- `GET /products/platforms/` - Get platforms
- `GET /products/filter_options/` - Get filter options
- `POST /products/{id}/track_view/` - Track product view

### Categories
- `GET /categories/` - List categories
- `GET /categories/{id}/` - Get category details

### Wishlist
- `GET /wishlist/` - Get user wishlist
- `POST /wishlist/add_product/` - Add to wishlist
- `POST /wishlist/remove_product/` - Remove from wishlist

### User
- `GET /users/profile/` - Get user profile
- `PUT /users/profile/` - Update user profile

## Usage Examples

### Authentication

```javascript
import { authAPI } from '../AppBackend/api';

// Login
const response = await authAPI.login('username', 'password');
// Tokens are automatically stored

// Register
const response = await authAPI.register({
  username: 'user123',
  email: 'user@example.com',
  password: 'password123',
});

// Logout
await authAPI.logout();
```

### Products

```javascript
import { productsAPI } from '../AppBackend/api';

// Get all products
const products = await productsAPI.getProducts();

// Get products with filters
const products = await productsAPI.getProducts({
  main_category: 'Electronics',
  min_price: 1000,
  max_price: 50000,
  ordering: '-created_at',
});

// Get product by ID
const product = await productsAPI.getProduct(123);

// Search products
const results = await productsAPI.searchProducts('laptop', 20);

// Get trending products
const trending = await productsAPI.getTrending();
```

### Wishlist

```javascript
import { wishlistAPI } from '../AppBackend/api';

// Get wishlist
const wishlist = await wishlistAPI.getWishlist();

// Add to wishlist
await wishlistAPI.addToWishlist(productId);

// Remove from wishlist
await wishlistAPI.removeFromWishlist(productId);

// Check if in wishlist
const isInWishlist = await wishlistAPI.isInWishlist(productId);
```

## Error Handling

All API methods throw errors that should be caught:

```javascript
try {
  const products = await productsAPI.getProducts();
} catch (error) {
  console.error('API Error:', error.message);
  // Handle error (show alert, etc.)
}
```

## Token Management

The API client automatically:
- Stores access and refresh tokens in AsyncStorage
- Adds Authorization header to requests
- Refreshes tokens when they expire (401 response)
- Clears tokens on refresh failure

## Database Configuration

The backend uses PostgreSQL. See `AppBackend/config.js` for database configuration details.

To set up PostgreSQL:
1. Install PostgreSQL
2. Create database: `createdb buyvaulthub_db`
3. Set environment variables in `backend/.env`:
   ```
   DATABASE_NAME=buyvaulthub_db
   DATABASE_USER=postgres
   DATABASE_PASSWORD=your_password
   DATABASE_HOST=localhost
   DATABASE_PORT=5432
   ```
4. Run migrations: `cd backend && python manage.py migrate`

## Troubleshooting

### Connection Issues

1. **Check backend is running**: `curl http://localhost:8000/api/v1/products/`
2. **Check CORS settings**: Ensure backend allows your app's origin
3. **Check network**: For physical devices, ensure device and computer are on same network

### Authentication Issues

1. **Check tokens**: Tokens are stored in AsyncStorage with keys `access_token` and `refresh_token`
2. **Clear tokens**: Call `authAPI.logout()` to clear stored tokens
3. **Check backend logs**: Look for authentication errors in Django logs

### API Errors

1. **Check response format**: Backend should return JSON
2. **Check status codes**: 401 = unauthorized, 404 = not found, 500 = server error
3. **Check network tab**: Use React Native Debugger to inspect requests

## Files

The following React Native files use the backend:

- `src/contexts/AuthContext.jsx` - Authentication context
- `src/screens/LoginScreen.jsx` - Login screen
- `src/screens/SignupScreen.jsx` - Signup screen
- `src/screens/ProductsScreen.jsx` - Products listing
- `src/screens/ProductDetailScreen.jsx` - Product details
- `src/screens/WishlistScreen.jsx` - Wishlist
- `src/screens/SearchScreen.jsx` - Search
- `src/components/TopRatedSection.jsx` - Top rated products
- `src/components/WhatsNewsection.jsx` - New products

## Next Steps

1. Test all screens with real backend data
2. Handle edge cases (empty responses, network errors)
3. Add loading states and error messages
4. Implement offline caching if needed
5. Add analytics/tracking if needed
