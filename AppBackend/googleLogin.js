/**
 * Google Login for React Native
 * 
 * This module provides Google Sign-In functionality for React Native
 * using @react-native-google-signin/google-signin
 */

import { GoogleSignin, statusCodes } from '@react-native-google-signin/google-signin';
import { authAPI } from './api';

/**
 * Configure Google Sign-In
 * Call this once when the app starts (e.g., in App.tsx or index.js)
 * 
 * @param {string} webClientId - Google OAuth 2.0 Web Client ID (from Google Cloud Console)
 */
export const configureGoogleSignIn = (webClientId) => {
  GoogleSignin.configure({
    webClientId: webClientId, // From Google Cloud Console
    offlineAccess: true, // If you want to access Google API on behalf of the user FROM YOUR SERVER
    forceCodeForRefreshToken: true, // [Android] related to `serverAuthCode`, read the docs link below *.
    iosClientId: '', // [iOS] optional, if you want to specify the client ID of type iOS (otherwise, it is taken from GoogleService-Info.plist)
  });
};

/**
 * Sign in with Google
 * Returns the ID token that can be sent to the backend
 * 
 * @returns {Promise<{idToken: string, user: object}>}
 */
export const signInWithGoogle = async () => {
  try {
    // Check if Google Play Services are available (Android)
    await GoogleSignin.hasPlayServices({ showPlayServicesUpdateDialog: true });
    
    // Get user info
    const userInfo = await GoogleSignin.signIn();
    
    // Get ID token
    const tokens = await GoogleSignin.getTokens();
    
    if (!tokens.idToken) {
      throw new Error('Google Sign-In did not return an ID token');
    }

    return {
      idToken: tokens.idToken,
      user: userInfo.user,
    };
  } catch (error) {
    if (error.code === statusCodes.SIGN_IN_CANCELLED) {
      throw new Error('User cancelled the login flow');
    } else if (error.code === statusCodes.IN_PROGRESS) {
      throw new Error('Sign in is in progress already');
    } else if (error.code === statusCodes.PLAY_SERVICES_NOT_AVAILABLE) {
      throw new Error('Play Services not available or outdated');
    } else {
      throw new Error(error.message || 'Google Sign-In failed');
    }
  }
};

/**
 * Sign out from Google
 */
export const signOutFromGoogle = async () => {
  try {
    await GoogleSignin.signOut();
  } catch (error) {
    console.error('Google Sign-Out error:', error);
  }
};

/**
 * Complete Google login flow
 * 1. Sign in with Google
 * 2. Send ID token to backend
 * 3. Store tokens from backend
 * 
 * @param {string} webClientId - Google OAuth 2.0 Web Client ID
 * @returns {Promise<{access: string, refresh: string, user: object}>}
 */
export const completeGoogleLogin = async (webClientId) => {
  try {
    // Configure if not already configured
    const currentConfig = await GoogleSignin.getCurrentUser();
    if (!currentConfig) {
      configureGoogleSignIn(webClientId);
    }

    // Sign in with Google
    const { idToken } = await signInWithGoogle();

    // Send ID token to backend
    const response = await authAPI.googleLogin(idToken);

    return {
      access: response.access,
      refresh: response.refresh,
      user: response.user,
    };
  } catch (error) {
    throw new Error(error.message || 'Google login failed');
  }
};

/**
 * Check if user is signed in with Google
 */
export const isSignedIn = async () => {
  return await GoogleSignin.isSignedIn();
};

/**
 * Get current Google user
 */
export const getCurrentGoogleUser = async () => {
  try {
    return await GoogleSignin.getCurrentUser();
  } catch (error) {
    return null;
  }
};
