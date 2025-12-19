import { StyleSheet, Text, TouchableOpacity, View, TextInput, Alert, ActivityIndicator, ScrollView, Image } from 'react-native'
import React, { useState } from 'react'
import { useNavigation } from '@react-navigation/native'
import { useAuth } from '../contexts/AuthContext'
import { SafeAreaView } from 'react-native-safe-area-context';
import LinearGradient from 'react-native-linear-gradient';
import BouncyCheckbox from "react-native-bouncy-checkbox";
import Feather from 'react-native-vector-icons/Feather';
import Ionicons from 'react-native-vector-icons/Ionicons';
import { authAPI } from '../../AppBackend/api';
import { completeGoogleLogin } from '../../AppBackend/googleLogin';
import { GOOGLE_WEB_CLIENT_ID } from '../../AppBackend/config';

const SignupScreen = () => {
  const navigation = useNavigation();
  const { login, setAuthData } = useAuth();
  const [formData, setFormData] = useState({
    username: '',
    email: '',
    password: '',
    confirmPassword: '',
  });
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');
  const [termsAccepted, setTermsAccepted] = useState(false);

  const handleChange = (field, value) => {
    setFormData(prev => ({ ...prev, [field]: value }));
    setError('');
  };

  const handleSignup = async () => {
    // Validation
    if (!formData.username.trim() || !formData.email.trim() || !formData.password.trim()) {
      setError('Please fill in all fields');
      return;
    }

    if (formData.password !== formData.confirmPassword) {
      setError('Passwords do not match');
      return;
    }

    if (formData.password.length < 6) {
      setError('Password must be at least 6 characters');
      return;
    }

    try {
      setIsLoading(true);
      setError('');

      // Register user via backend API
      const response = await authAPI.register({
        username: formData.username,
        email: formData.email,
        password: formData.password,
        first_name: '',
        last_name: '',
      });

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
        const { userAPI } = require('../../AppBackend/api');
        userData = await userAPI.getProfile();
      }

      // Show success message and redirect to login
      Alert.alert(
        'Account Created!',
        'Your account has been created successfully. Please sign in to continue.',
        [
          {
            text: 'Sign In',
            onPress: () => navigation.navigate('LoginScreen', {
              username: formData.username,
              message: 'Account created successfully! Please sign in.'
            })
          }
        ]
      );
    } catch (err) {
      const errorMessage = err.message || 'Signup failed. Please try again.';
      setError(errorMessage);
      Alert.alert('Signup Failed', errorMessage);
    } finally {
      setIsLoading(false);
    }
  };

  const handleGoogleSignup = async () => {
    try {
      setIsLoading(true);
      setError('');

      // Get Google Web Client ID from config
      if (!GOOGLE_WEB_CLIENT_ID || GOOGLE_WEB_CLIENT_ID.includes('YOUR_GOOGLE_WEB_CLIENT_ID')) {
        Alert.alert(
          'Configuration Required',
          'Google Client ID not configured. Please set GOOGLE_WEB_CLIENT_ID in AppBackend/config.js'
        );
        return;
      }

      const result = await completeGoogleLogin(GOOGLE_WEB_CLIENT_ID);

      // Login with the tokens from backend
      await setAuthData(result.access, result.refresh, result.user);

      navigation.navigate('HomeScreen');
    } catch (err) {
      const errorMessage = err.message || 'Google signup failed. Please try again.';
      setError(errorMessage);
      Alert.alert('Google Signup Failed', errorMessage);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <SafeAreaView style={styles.safeArea} edges={['top']}>
      <LinearGradient
        colors={['#e2e8f0', '#dbeafe', '#c7d2fe']}
        style={styles.container}
      >
        <ScrollView
          contentContainerStyle={styles.scrollContent}
          showsVerticalScrollIndicator={false}
        >
          {/* Back to Home Button */}
          <TouchableOpacity
            style={styles.backButton}
            onPress={() => navigation.navigate('HomeScreen')}
          >
            <Feather name="arrow-left" size={14} color="#4b5563" />
            <Text style={styles.backButtonText}>Back to Home</Text>
          </TouchableOpacity>

          {/* Mobile Header */}
          <View style={styles.mobileHeader}>
            <View style={styles.mobileLogoContainer}>
              <Image
                source={require("../assets/logo_icon.jpg")}
                style={styles.mobileLogo}
                resizeMode="cover"
              />
            </View>
            <Text style={styles.mobileTitle}>Buy Vault Hub</Text>
            <Text style={styles.mobileSubtitle}>Join our secure digital asset portal</Text>
          </View>

          {/* Signup Card */}
          <View style={styles.card}>
            <View style={styles.cardContent}>
              {/* Welcome Section */}
              <View style={styles.welcomeSection}>
                <View style={styles.iconContainer}>
                  <Feather name="user-plus" size={20} color="#ffffff" />
                </View>
                <Text style={styles.welcomeTitle}>Create Account</Text>
                <Text style={styles.welcomeSubtitle}>Join Buy Vault Hub and start shopping</Text>
              </View>

              {/* Signup Form */}
              {error ? (
                <View style={styles.errorContainer}>
                  <Text style={styles.errorText}>{error}</Text>
                </View>
              ) : null}

              {/* Username Field */}
              <View style={styles.inputGroup}>
                <View style={styles.inputWrapper}>
                  <Feather name="user" size={16} color="#9ca3af" style={styles.inputIcon} />
                  <TextInput
                    style={styles.input}
                    placeholder="Username"
                    placeholderTextColor="#6b7280"
                    value={formData.username}
                    onChangeText={(value) => handleChange('username', value)}
                    autoCapitalize="none"
                  />
                </View>
              </View>

              {/* Email Field */}
              <View style={styles.inputGroup}>
                <View style={styles.inputWrapper}>
                  <Feather name="mail" size={16} color="#9ca3af" style={styles.inputIcon} />
                  <TextInput
                    style={styles.input}
                    placeholder="Email"
                    placeholderTextColor="#6b7280"
                    value={formData.email}
                    onChangeText={(value) => handleChange('email', value)}
                    keyboardType="email-address"
                    autoCapitalize="none"
                  />
                </View>
              </View>

              {/* Password Field */}
              <View style={styles.inputGroup}>
                <View style={styles.inputWrapper}>
                  <Feather name="lock" size={16} color="#9ca3af" style={styles.inputIcon} />
                  <TextInput
                    style={styles.input}
                    placeholder="Password"
                    placeholderTextColor="#6b7280"
                    value={formData.password}
                    onChangeText={(value) => handleChange('password', value)}
                    secureTextEntry={!showPassword}
                  />
                  <TouchableOpacity
                    onPress={() => setShowPassword(!showPassword)}
                    style={styles.eyeIcon}
                  >
                    <Feather
                      name={showPassword ? "eye-off" : "eye"}
                      size={16}
                      color="#9ca3af"
                    />
                  </TouchableOpacity>
                </View>
              </View>

              {/* Confirm Password Field */}
              <View style={styles.inputGroup}>
                <View style={styles.inputWrapper}>
                  <Feather name="lock" size={16} color="#9ca3af" style={styles.inputIcon} />
                  <TextInput
                    style={styles.input}
                    placeholder="Confirm Password"
                    placeholderTextColor="#6b7280"
                    value={formData.confirmPassword}
                    onChangeText={(value) => handleChange('confirmPassword', value)}
                    secureTextEntry={!showConfirmPassword}
                  />
                  <TouchableOpacity
                    onPress={() => setShowConfirmPassword(!showConfirmPassword)}
                    style={styles.eyeIcon}
                  >
                    <Feather
                      name={showConfirmPassword ? "eye-off" : "eye"}
                      size={16}
                      color="#9ca3af"
                    />
                  </TouchableOpacity>
                </View>
              </View>

              {/* Terms Checkbox - Only checkbox, no text */}
              <View style={styles.termsContainer}>
                <BouncyCheckbox
                  size={16}
                  isChecked={termsAccepted}
                  onPress={() => setTermsAccepted(!termsAccepted)}
                  fillColor="#2563eb"
                  iconStyle={{ borderRadius: 4 }}
                  innerIconStyle={{ borderRadius: 4, borderWidth: 2 }}
                  text="I agree to the Terms of Service and Privacy Policy"
                  textStyle={{
                    textDecorationLine: "none",
                    fontSize: 12,
                    color: '#374151',
                    marginLeft: 8,
                    flex: 1,
                    flexWrap: 'wrap',
                  }}
                />
              </View>
            </View>

            {/* Bottom Section - Button at the very bottom */}
            <View style={styles.bottomSection}>
              {/* Signup Button - At the bottom */}
              <TouchableOpacity
                style={[styles.signupButton, (isLoading || !termsAccepted) && styles.signupButtonDisabled]}
                onPress={handleSignup}
                disabled={isLoading || !termsAccepted}
              >
                {isLoading ? (
                  <View style={styles.loadingContainer}>
                    <ActivityIndicator size="small" color="#ffffff" />
                    <Text style={styles.signupButtonText}>Creating...</Text>
                  </View>
                ) : (
                  <Text style={styles.signupButtonText}>Create Account</Text>
                )}
              </TouchableOpacity>

              {/* Divider */}
              <View style={styles.divider}>
                <View style={styles.dividerLine} />
                <Text style={styles.dividerText}>OR</Text>
                <View style={styles.dividerLine} />
              </View>

              {/* Google Signup Button */}
              <TouchableOpacity
                style={styles.googleBtn}
                onPress={handleGoogleSignup}
                disabled={isLoading}
              >
                <Image
                  source={{ uri: "https://img.icons8.com/color/48/google-logo.png" }}
                  style={styles.googleIcon}
                />
                <Text style={styles.googleBtnText}>Continue with Google</Text>
              </TouchableOpacity>

              {/* Sign In Link */}
              <View style={styles.loginContainer}>
                <Text style={styles.normalText}>Already have an account? </Text>
                <TouchableOpacity onPress={() => navigation.navigate('LoginScreen')}>
                  <Text style={styles.loginText}>Sign in</Text>
                </TouchableOpacity>
              </View>
            </View>
          </View>
        </ScrollView>
      </LinearGradient>
    </SafeAreaView>
  )
}

export default SignupScreen

const styles = StyleSheet.create({
  safeArea: {
    flex: 1,
    backgroundColor: '#f8fafc',
  },
  container: {
    flex: 1,
  },
  scrollContent: {
    flexGrow: 1,
    padding: 16,
    paddingTop: 8,
  },
  backButton: {
    flexDirection: 'row',
    alignItems: 'center',
    alignSelf: 'flex-start',
    backgroundColor: 'rgba(255, 255, 255, 0.5)',
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 20,
    borderWidth: 1,
    borderColor: 'rgba(229, 231, 235, 0.5)',
    marginBottom: 12,
  },
  backButtonText: {
    fontSize: 12,
    color: '#4b5563',
    marginLeft: 4,
  },
  mobileHeader: {
    alignItems: 'center',
    marginBottom: 24,
  },
  mobileLogoContainer: {
    width: 80,
    height: 80,
    backgroundColor: 'rgba(255, 255, 255, 0.9)',
    borderRadius: 16,
    marginBottom: 12,
    overflow: 'hidden',
    elevation: 8,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.1,
    shadowRadius: 8,
  },
  mobileLogo: {
    width: '100%',
    height: '100%',
  },
  mobileTitle: {
    fontSize: 24,
    fontWeight: 'bold',
    color: '#2563eb',
    marginBottom: 4,
  },
  mobileSubtitle: {
    fontSize: 14,
    color: '#4b5563',
  },
  card: {
    backgroundColor: 'rgba(255, 255, 255, 0.9)',
    borderRadius: 16,
    padding: 20,
    elevation: 8,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.1,
    shadowRadius: 8,
    borderWidth: 1,
    borderColor: 'rgba(255, 255, 255, 0.2)',
    minHeight: 200,
    justifyContent: 'space-between',
  },
  cardContent: {
    flex: 1,
  },
  bottomSection: {
    marginTop: 10,
    paddingTop: 10,
  },
  welcomeSection: {
    alignItems: 'center',
    marginBottom: 16,
  },
  iconContainer: {
    width: 40,
    height: 40,
    backgroundColor: '#2563eb',
    borderRadius: 12,
    justifyContent: 'center',
    alignItems: 'center',
    marginBottom: 8,
    elevation: 4,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
  },
  welcomeTitle: {
    fontSize: 18,
    fontWeight: 'bold',
    color: '#1f2937',
    marginBottom: 4,
  },
  welcomeSubtitle: {
    fontSize: 12,
    color: '#4b5563',
  },
  errorContainer: {
    backgroundColor: '#fef2f2',
    borderWidth: 1,
    borderColor: '#fecaca',
    padding: 8,
    borderRadius: 8,
    marginBottom: 12,
  },
  errorText: {
    color: '#991b1b',
    fontSize: 12,
  },
  inputGroup: {
    marginBottom: 8,
  },
  inputWrapper: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: 'rgba(249, 250, 251, 0.5)',
    borderWidth: 1,
    borderColor: '#e5e7eb',
    borderRadius: 8,
    paddingHorizontal: 12,
    height: 40,
  },
  inputIcon: {
    marginRight: 12,
  },
  input: {
    flex: 1,
    fontSize: 14,
    color: '#1f2937',
    padding: 0,
  },
  eyeIcon: {
    padding: 4,
  },
  termsContainer: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    marginBottom: 8,
    marginTop: 4,
  },
  signupButton: {
    backgroundColor: '#2563eb',
    paddingVertical: 12,
    borderRadius: 8,
    alignItems: 'center',
    marginTop: 0,
    marginBottom: 12,
    elevation: 4,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
  },
  signupButtonDisabled: {
    opacity: 0.5,
  },
  loadingContainer: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  signupButtonText: {
    color: '#ffffff',
    fontSize: 16,
    fontWeight: '600',
    marginLeft: 8,
  },
  divider: {
    flexDirection: 'row',
    alignItems: 'center',
    marginVertical: 12,
  },
  dividerLine: {
    flex: 1,
    height: 1,
    backgroundColor: '#e5e7eb',
  },
  dividerText: {
    marginHorizontal: 10,
    fontSize: 12,
    color: '#6b7280',
    backgroundColor: 'rgba(255, 255, 255, 0.9)',
  },
  googleBtn: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    borderWidth: 1,
    borderColor: '#e5e7eb',
    borderRadius: 8,
    paddingVertical: 10,
    marginBottom: 12,
  },
  googleIcon: {
    width: 16,
    height: 16,
    marginRight: 8,
  },
  googleBtnText: {
    fontSize: 14,
    fontWeight: '500',
    color: '#1f2937',
  },
  loginContainer: {
    flexDirection: 'row',
    justifyContent: 'center',
    alignItems: 'center',
    marginTop: 12,
  },
  normalText: {
    fontSize: 12,
    color: '#4b5563',
  },
  loginText: {
    fontSize: 12,
    color: '#2563eb',
    fontWeight: '600',
  },
})
