import { StatusBar } from 'react-native'
import React, { useEffect } from 'react'
import Router from './src/navigations/Router'
import { AuthProvider } from './src/contexts/AuthContext'
import { configureGoogleSignIn } from './AppBackend/googleLogin'
import { GOOGLE_WEB_CLIENT_ID } from './AppBackend/config'

const App = () => {
  useEffect(() => {
    // Initialize Google Sign-In when app starts
    if (GOOGLE_WEB_CLIENT_ID && !GOOGLE_WEB_CLIENT_ID.includes('YOUR_GOOGLE_WEB_CLIENT_ID')) {
      configureGoogleSignIn(GOOGLE_WEB_CLIENT_ID);
    } else {
      console.warn('Google Sign-In not configured. Set GOOGLE_WEB_CLIENT_ID in AppBackend/config.js');
    }
  }, []);

  return (
    <AuthProvider>
      <StatusBar backgroundColor='#F5F5F5' barStyle='dark-content' />
      <Router />
    </AuthProvider>
  )
}

export default App