import { StyleSheet, Text, View, Image, TextInput, TouchableOpacity, Alert, ActivityIndicator, ScrollView, Platform } from 'react-native'
import React, { useState, useEffect } from 'react'
import { useNavigation, useRoute } from '@react-navigation/native'
import LinearGradient from 'react-native-linear-gradient'
import BouncyCheckbox from "react-native-bouncy-checkbox";
import { useAuth } from '../contexts/AuthContext';
import { SafeAreaView } from 'react-native-safe-area-context';
import Ionicons from 'react-native-vector-icons/Ionicons';
import Feather from 'react-native-vector-icons/Feather';
import { completeGoogleLogin } from '../../AppBackend/googleLogin';
import { GOOGLE_WEB_CLIENT_ID } from '../../AppBackend/config';

const LoginScreen = () => {
    const navigation = useNavigation();
    const route = useRoute();
    const { login, setAuthData } = useAuth();
    const [rememberMe, setRememberMe] = useState(false);
    const [username, setUsername] = useState(route.params?.username || '');
    const [password, setPassword] = useState('');
    const [showPassword, setShowPassword] = useState(false);
    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState('');

    // Show success message if coming from signup
    useEffect(() => {
        if (route.params?.message) {
            Alert.alert('Success', route.params.message);
        }
    }, [route.params?.message]);

    const handleLogin = async () => {
        if (!username.trim() || !password.trim()) {
            setError('Please enter both username and password');
            return;
        }

        try {
            setIsLoading(true);
            setError('');
            await login(username, password);
            navigation.navigate('HomeScreen');
        } catch (err) {
            const errorMessage = err.message || 'Login failed. Please check your credentials and try again.';
            setError(errorMessage);
            Alert.alert('Login Failed', errorMessage);
        } finally {
            setIsLoading(false);
        }
    };

    const handleGoogleLogin = async () => {
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
            const errorMessage = err.message || 'Google login failed. Please try again.';
            setError(errorMessage);
            Alert.alert('Google Login Failed', errorMessage);
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
                        <Text style={styles.mobileSubtitle}>Your secure digital asset portal</Text>
                    </View>

                    {/* Login Card */}
                    <View style={styles.card}>
                        {/* Welcome Section */}
                        <View style={styles.welcomeSection}>
                            <View style={styles.iconContainer}>
                                <Feather name="lock" size={20} color="#ffffff" />
                            </View>
                            <Text style={styles.welcomeTitle}>Welcome Back</Text>
                            <Text style={styles.welcomeSubtitle}>Sign in to your account</Text>
                        </View>

                        {/* Login Form */}
                        {error ? (
                            <View style={styles.errorContainer}>
                                <Text style={styles.errorText}>{error}</Text>
                            </View>
                        ) : null}

                        {/* Username Field */}
                        <View style={styles.inputGroup}>
                            <View style={styles.inputWrapper}>
                                <Feather name="mail" size={20} color="#9ca3af" style={styles.inputIcon} />
                                <TextInput
                                    style={styles.input}
                                    placeholder="Enter your username or email"
                                    placeholderTextColor="#6b7280"
                                    value={username}
                                    onChangeText={(text) => {
                                        setUsername(text);
                                        setError('');
                                    }}
                                    autoCapitalize="none"
                                />
                            </View>
                        </View>

                        {/* Password Field */}
                        <View style={styles.inputGroup}>
                            <View style={styles.inputWrapper}>
                                <Feather name="lock" size={20} color="#9ca3af" style={styles.inputIcon} />
                                <TextInput
                                    style={styles.input}
                                    placeholder="Enter your password"
                                    placeholderTextColor="#6b7280"
                                    value={password}
                                    onChangeText={(text) => {
                                        setPassword(text);
                                        setError('');
                                    }}
                                    secureTextEntry={!showPassword}
                                />
                                <TouchableOpacity
                                    onPress={() => setShowPassword(!showPassword)}
                                    style={styles.eyeIcon}
                                >
                                    <Feather
                                        name={showPassword ? "eye-off" : "eye"}
                                        size={20}
                                        color="#9ca3af"
                                    />
                                </TouchableOpacity>
                            </View>
                        </View>

                        {/* Remember Me & Forgot Password */}
                        <View style={styles.rememberForgotRow}>
                            <View style={styles.rememberMeContainer}>
                                <BouncyCheckbox
                                    size={16}
                                    isChecked={rememberMe}
                                    onPress={() => setRememberMe(!rememberMe)}
                                    fillColor="#2563eb"
                                    iconStyle={{ borderRadius: 4 }}
                                    innerIconStyle={{ borderRadius: 4, borderWidth: 2 }}
                                    text="Remember me"
                                    textStyle={{
                                        textDecorationLine: "none",
                                        fontSize: 14,
                                        color: '#374151',
                                        marginLeft: 8,
                                    }}
                                />
                            </View>
                            <TouchableOpacity>
                                <Text style={styles.forgetpassword}>Forgot your password?</Text>
                            </TouchableOpacity>
                        </View>

                        {/* Login Button */}
                        <TouchableOpacity
                            style={[styles.loginBtn, isLoading && styles.loginBtnDisabled]}
                            onPress={handleLogin}
                            disabled={isLoading}
                        >
                            {isLoading ? (
                                <View style={styles.loadingContainer}>
                                    <ActivityIndicator size="small" color="#ffffff" />
                                    <Text style={styles.loginBtnText}>Signing in...</Text>
                                </View>
                            ) : (
                                <Text style={styles.loginBtnText}>Sign In</Text>
                            )}
                        </TouchableOpacity>

                        {/* Divider */}
                        <View style={styles.divider}>
                            <View style={styles.dividerLine} />
                            <Text style={styles.dividerText}>OR</Text>
                            <View style={styles.dividerLine} />
                        </View>

                        {/* Google Login Button */}
                        <TouchableOpacity
                            style={styles.googleBtn}
                            onPress={handleGoogleLogin}
                            disabled={isLoading}
                        >
                            <Image
                                source={{ uri: "https://img.icons8.com/color/48/google-logo.png" }}
                                style={styles.googleIcon}
                            />
                            <Text style={styles.googleBtnText}>Continue with Google</Text>
                        </TouchableOpacity>

                        {/* Sign Up Link */}
                        <View style={styles.signupContainer}>
                            <Text style={styles.normalText}>Don't have an account? </Text>
                            <TouchableOpacity onPress={() => navigation.navigate('SignUpScreen')}>
                                <Text style={styles.signupText}>Sign up</Text>
                            </TouchableOpacity>
                        </View>

                        {/* Footer */}
                        <View style={styles.footer}>
                            <Text style={styles.footerText}>
                                By continuing, you agree to Buy Vault Hub's{' '}
                                <Text style={styles.footerLink}>Terms of Service</Text>
                                {' '}and{' '}
                                <Text style={styles.footerLink}>Privacy Policy</Text>
                            </Text>
                        </View>
                    </View>
                </ScrollView>
            </LinearGradient>
        </SafeAreaView>
    )
}

export default LoginScreen

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
        justifyContent: 'flex-start',
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
        marginBottom: 5,
    },
    backButtonText: {
        fontSize: 12,
        color: '#4b5563',
        marginLeft: 4,
    },
    mobileHeader: {
        alignItems: 'center',
        marginBottom: 16,
    },
    mobileLogoContainer: {
        width: 80,
        height: 80,
        backgroundColor: 'rgba(255, 255, 255, 0.72)',
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
        marginTop: 10,
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
        padding: 12,
        borderRadius: 8,
        marginBottom: 12,
    },
    errorText: {
        color: '#991b1b',
        fontSize: 12,
    },
    inputGroup: {
        marginBottom: 12,
    },
    inputWrapper: {
        flexDirection: 'row',
        alignItems: 'center',
        backgroundColor: 'rgba(249, 250, 251, 0.5)',
        borderWidth: 1,
        borderColor: '#e5e7eb',
        borderRadius: 8,
        paddingHorizontal: 16,
        height: 42,
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
    rememberForgotRow: {
        flexDirection: 'row',
        justifyContent: 'space-between',
        alignItems: 'center',
        marginBottom: 12,
    },
    rememberMeContainer: {
        flexDirection: 'row',
        alignItems: 'center',
        flex: 1,
    },
    forgetpassword: {
        fontSize: 14,
        color: '#2563eb',
        fontWeight: '500',
        textAlign: 'right',
    },
    loginBtn: {
        backgroundColor: '#2563eb',
        paddingVertical: 10,
        borderRadius: 8,
        alignItems: 'center',
        marginTop: 8,
        marginBottom: 12,
        elevation: 4,
        shadowColor: '#000',
        shadowOffset: { width: 0, height: 2 },
        shadowOpacity: 0.1,
        shadowRadius: 4,
    },
    loginBtnDisabled: {
        opacity: 0.5,
    },
    loadingContainer: {
        flexDirection: 'row',
        alignItems: 'center',
    },
    loginBtnText: {
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
        width: 20,
        height: 20,
        marginRight: 8,
    },
    googleBtnText: {
        fontSize: 14,
        fontWeight: '500',
        color: '#1f2937',
    },
    signupContainer: {
        flexDirection: 'row',
        justifyContent: 'center',
        alignItems: 'center',
        marginTop: 12,
    },
    normalText: {
        fontSize: 12,
        color: '#4b5563',
    },
    signupText: {
        fontSize: 12,
        color: '#2563eb',
        fontWeight: '600',
    },
    footer: {
        marginTop: 24,
        alignItems: 'center',
    },
    footerText: {
        fontSize: 12,
        color: '#6b7280',
        textAlign: 'center',
        lineHeight: 18,
    },
    footerLink: {
        color: '#2563eb',
        fontWeight: '600',
    },
})
