import { StyleSheet, Text, TextInput, View, TouchableOpacity, Image, StatusBar, Dimensions, Modal } from 'react-native'
import React, { useState } from 'react'
import { useNavigation } from '@react-navigation/native'
import LinearGradient from 'react-native-linear-gradient'
import Ionicons from 'react-native-vector-icons/Ionicons'
import Feather from 'react-native-vector-icons/Feather'
import DrawerOverlay from './DrawerOverlay';
import { useAuth } from '../contexts/AuthContext';

// const { width, height } = Dimensions.get('window');

const Header = () => {
  const navigation = useNavigation();
  const { isAuthenticated, user, logout } = useAuth();
  const [sidebarVisible, setSidebarVisible] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [userMenuVisible, setUserMenuVisible] = useState(false);

  const handleSearch = () => {
    if (searchQuery.trim()) {
      navigation.navigate('Search', { query: searchQuery });
    } else {
      navigation.navigate('Search');
    }
  };

  const handleLogout = async () => {
    await logout();
    setUserMenuVisible(false);
    navigation.navigate('HomeScreen');
  };

  const displayName = user && (user.first_name || user.last_name)
    ? `${user.first_name || ''} ${user.last_name || ''}`.trim()
    : (user?.username || 'User');

  return (
    <>
      <DrawerOverlay
        isOpen={sidebarVisible}
        onClose={() => setSidebarVisible(false)}
      />

      {/* Actual header layout */}
      <LinearGradient
        colors={['#F5F5F5', '#F0F0F0', '#FFFFFF']}
        style={styles.container}
      >
        {/* Top Row */}
        <View style={styles.topRow}>
          <TouchableOpacity onPress={() => setSidebarVisible(true)}>
            <Feather name="menu" size={24} color="#333333" style={{ marginRight: 10 }} />
          </TouchableOpacity>

          <TouchableOpacity
            onPress={() => navigation.navigate('HomeScreen')}
            style={styles.logoContainer}
          >
            <Image
              source={require("../assets/logo_icon.jpg")}
              style={styles.logo}
              resizeMode="cover"
            />
          </TouchableOpacity>

          <View style={styles.navButtons}>
            <TouchableOpacity onPress={() => navigation.navigate('Products')}>
              <Text style={styles.navText}>Products</Text>
            </TouchableOpacity>
          </View>

          <View style={styles.iconRow}>
            {isAuthenticated ? (
              <>
                <TouchableOpacity onPress={() => navigation.navigate('Wishlist')} style={{ marginRight: 12 }}>
                  <Ionicons name="heart-outline" size={22} color="#333333" />
                </TouchableOpacity>
                <TouchableOpacity onPress={() => setUserMenuVisible(true)}>
                  <Feather name="user" size={22} color="#333333" />
                </TouchableOpacity>
              </>
            ) : (
              <TouchableOpacity
                onPress={() => navigation.navigate('LoginScreen')}
                style={styles.signInButton}
              >
                <Text style={styles.signInText}>Sign In</Text>
              </TouchableOpacity>
            )}
          </View>
        </View>

        {/* Search Bar */}
        <TouchableOpacity
          style={styles.textinputcontainer}
          onPress={handleSearch}
          activeOpacity={0.8}
        >
          <View style={styles.row}>
            <Ionicons name="search" size={22} color="#1f1f1f" />
            <TextInput
              placeholder='Search products'
              placeholderTextColor="#848484"
              style={styles.textinput}
              value={searchQuery}
              onChangeText={setSearchQuery}
              onSubmitEditing={handleSearch}
              returnKeyType="search"
              editable={true}
            />
          </View>
          <TouchableOpacity onPress={handleSearch}>
            <Ionicons name="search" size={22} color="#1f1f1f" />
          </TouchableOpacity>
        </TouchableOpacity>
      </LinearGradient>

      {/* User Menu Modal */}
      <Modal
        visible={userMenuVisible}
        transparent={true}
        animationType="fade"
        onRequestClose={() => setUserMenuVisible(false)}
      >
        <TouchableOpacity
          style={styles.menuOverlay}
          activeOpacity={1}
          onPress={() => setUserMenuVisible(false)}
        >
          <View style={styles.userMenu}>
            <View style={styles.userMenuHeader}>
              <Text style={styles.userMenuName}>
                {user?.first_name || user?.username || 'User'}
              </Text>
              <Text style={styles.userMenuEmail}>{user?.email || ''}</Text>
            </View>
            <TouchableOpacity
              style={styles.userMenuItem}
              onPress={() => {
                setUserMenuVisible(false);
                navigation.navigate('Profile');
              }}
            >
              <Feather name="settings" size={16} color="#374151" />
              <Text style={styles.userMenuItemText}>Profile Settings</Text>
            </TouchableOpacity>
            <TouchableOpacity
              style={styles.userMenuItem}
              onPress={handleLogout}
            >
              <Feather name="log-out" size={16} color="#374151" />
              <Text style={styles.userMenuItemText}>Sign Out</Text>
            </TouchableOpacity>
          </View>
        </TouchableOpacity>
      </Modal>
    </>
  )
}

export default Header

const styles = StyleSheet.create({
  container: {
    padding: 20,
    paddingTop: StatusBar.currentHeight - 5,
    flexDirection: 'column',
    justifyContent: 'center'
  },
  topRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginTop: -20,
  },
  logoContainer: {
    width: 60,
    height: 60,
    backgroundColor: 'rgba(255, 255, 255, 0.9)',
    borderRadius: 14,
    overflow: 'hidden',
    elevation: 6,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.1,
    shadowRadius: 8,
  },
  logo: {
    width: '100%',
    height: '100%',
    // borderRadius: 30,
  },
  navButtons: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  navText: {
    color: '#333333',
    fontSize: 14,
    marginHorizontal: 8,
    fontWeight: '500'
  },
  iconRow: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  textinputcontainer: {
    flexDirection: 'row',
    alignItems: 'center',
    borderWidth: 1,
    borderColor: '#CCCCCC',
    borderRadius: 8,
    backgroundColor: '#FFFFFF',
    width: '100%',
    justifyContent: 'space-between',
    paddingHorizontal: 10,
    paddingVertical: 4,
    marginTop: 15,
    elevation: 5,
  },
  row: {
    flexDirection: 'row',
    alignItems: 'center',
    flex: 1,
    marginRight: -18,
  },
  textinput: {
    padding: 8,
    flex: 1,
  },
  signInButton: {
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 6,
  },
  signInText: {
    color: '#2563eb',
    fontSize: 14,
    fontWeight: '600',
  },
  menuOverlay: {
    flex: 1,
    backgroundColor: 'rgba(0, 0, 0, 0.5)',
    justifyContent: 'flex-start',
    alignItems: 'flex-end',
    paddingTop: 60,
    paddingRight: 16,
  },
  userMenu: {
    backgroundColor: '#ffffff',
    borderRadius: 8,
    width: 200,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 4 },
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.2,
    shadowRadius: 8,
    elevation: 8,
    borderWidth: 1,
    borderColor: '#e5e7eb',
  },
  userMenuHeader: {
    padding: 16,
    borderBottomWidth: 1,
    borderBottomColor: '#f3f4f6',
  },
  userMenuName: {
    fontSize: 14,
    fontWeight: '600',
    color: '#1f2937',
    marginBottom: 4,
  },
  userMenuEmail: {
    fontSize: 12,
    color: '#6b7280',
  },
  userMenuItem: {
    flexDirection: 'row',
    alignItems: 'center',
    padding: 16,
    borderBottomWidth: 1,
    borderBottomColor: '#f3f4f6',
  },
  userMenuItemText: {
    fontSize: 14,
    color: '#374151',
    marginLeft: 12,
  },
})
