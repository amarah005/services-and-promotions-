import { StyleSheet, Text, View } from 'react-native'
import React from 'react'
import { NavigationContainer } from '@react-navigation/native'
import { createNativeStackNavigator } from '@react-navigation/native-stack'
import HomeScreen from '../screens/HomeScreen'
import ProductsScreen from '../screens/ProductsScreen'
import ProductDetailScreen from '../screens/ProductDetailScreen'
import SearchScreen from '../screens/SearchScreen'
import WishlistScreen from '../screens/WishlistScreen'
import ProfileScreen from '../screens/ProfileScreen'
import LoginScreen from '../screens/LoginScreen'
import SignupScreen from '../screens/SignupScreen'
import CategoryDetailScreen from '../screens/CategoryDetailScreen'

const Stack = createNativeStackNavigator();

const Router = () => {
  return (
    <NavigationContainer>
        <Stack.Navigator 
          initialRouteName="HomeScreen"
          screenOptions={() => ({
            headerShown: false,
          })}
        >
            {/* Main screens - accessible without auth (matching web flow) */}
            <Stack.Screen name='HomeScreen' component={HomeScreen} />
            <Stack.Screen name='Products' component={ProductsScreen} />
            <Stack.Screen name='ProductDetail' component={ProductDetailScreen} />
            <Stack.Screen name='Search' component={SearchScreen} />
            <Stack.Screen name='CategoryDetail' component={CategoryDetailScreen} />
            
            {/* Auth screens */}
            <Stack.Screen name='LoginScreen' component={LoginScreen} />
            <Stack.Screen name='SignUpScreen' component={SignupScreen} />
            
            {/* Protected screens - will handle auth redirect internally */}
            <Stack.Screen name='Wishlist' component={WishlistScreen} />
            <Stack.Screen name='Profile' component={ProfileScreen} />
        </Stack.Navigator>
    </NavigationContainer>
  )
}

export default Router

const styles = StyleSheet.create({})