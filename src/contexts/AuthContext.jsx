import React, { createContext, useContext, useState, useEffect } from 'react';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { authAPI, userAPI } from '../../AppBackend/api';

const AuthContext = createContext();

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isAuthenticated, setIsAuthenticated] = useState(false);

  // Check if user is logged in on app start
  useEffect(() => {
    checkAuthStatus();
  }, []);

  const checkAuthStatus = async () => {
    try {
      const access = await AsyncStorage.getItem('access_token');

      if (!access) {
        setUser(null);
        setIsAuthenticated(false);
        setIsLoading(false);
        return;
      }

      // Validate token by fetching user profile
      try {
        const userData = await userAPI.getProfile();
        setUser(userData);
        setIsAuthenticated(true);
      } catch (error) {
        // Token invalid, clear it
        await authAPI.logout();
        setUser(null);
        setIsAuthenticated(false);
      }
    } catch (error) {
      console.error('Error checking auth status:', error);
      await authAPI.logout();
      setUser(null);
      setIsAuthenticated(false);
    } finally {
      setIsLoading(false);
    }
  };

  const login = async (username, password) => {
    try {
      setIsLoading(true);

      // Call backend API
      const response = await authAPI.login(username, password);

      // Extract user data from response
      let userData;
      if (response.user) {
        userData = response.user;
      } else if (response.user_id) {
        // Legacy token-based response
        userData = {
          id: response.user_id,
          username: response.username,
          email: response.email,
          first_name: response.first_name || '',
          last_name: response.last_name || '',
        };
      } else {
        // Fetch user profile
        userData = await userAPI.getProfile();
      }

      setUser(userData);
      setIsAuthenticated(true);
      return { access: response.access || response.token, user: userData };
    } catch (error) {
      throw error;
    } finally {
      setIsLoading(false);
    }
  };

  const logout = async () => {
    try {
      await authAPI.logout();
    } catch (error) {
      console.error('Error during logout:', error);
    }
    setUser(null);
    setIsAuthenticated(false);
  };

  const setAuthData = async (access, refresh, userData) => {
    if (access) {
      await AsyncStorage.setItem('access_token', access);
    }
    if (refresh) {
      await AsyncStorage.setItem('refresh_token', refresh);
    }
    if (userData) {
      setUser(userData);
      setIsAuthenticated(true);
    }
  };

  const value = {
    user,
    isAuthenticated,
    isLoading,
    login,
    logout,
    checkAuthStatus,
    setAuthData,
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
};

