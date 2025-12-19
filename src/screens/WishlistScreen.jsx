import React, { useState, useEffect } from 'react';
import {
  StyleSheet,
  Text,
  View,
  FlatList,
  Image,
  TouchableOpacity,
  ActivityIndicator,
  Alert,
  Linking,
} from 'react-native';
import { useNavigation } from '@react-navigation/native';
import { useAuth } from '../contexts/AuthContext';
import { SafeAreaView } from 'react-native-safe-area-context';
import { wishlistAPI } from '../../AppBackend/api';

const WishlistScreen = () => {
  const navigation = useNavigation();
  const { isAuthenticated } = useAuth();
  const [wishlistItems, setWishlistItems] = useState([]);
  const [loading, setLoading] = useState(true);

  // Match web behavior: redirect to login if not authenticated
  useEffect(() => {
    if (!isAuthenticated) {
      navigation.navigate('LoginScreen');
      return;
    }
  }, [isAuthenticated, navigation]);

  useEffect(() => {
    // Only load wishlist if authenticated
    if (!isAuthenticated) {
      setLoading(false);
      return;
    }

    const loadWishlist = async () => {
      setLoading(true);
      try {
        const data = await wishlistAPI.getWishlist();
        setWishlistItems(Array.isArray(data.results || data) ? (data.results || data) : []);
      } catch (error) {
        console.error('Error loading wishlist:', error);
        setWishlistItems([]);
      } finally {
        setLoading(false);
      }
    };

    loadWishlist();
  }, [isAuthenticated]);

  const handleRemoveFromWishlist = async (item) => {
    Alert.alert(
      'Remove from Wishlist',
      `Remove "${item.product?.name || 'this product'}" from your wishlist?`,
      [
        { text: 'Cancel', style: 'cancel' },
        {
          text: 'Remove',
          style: 'destructive',
          onPress: async () => {
            try {
              await wishlistAPI.removeFromWishlist(item.product?.id || item.id);
              setWishlistItems((prev) => prev.filter((i) => i.id !== item.id));
              Alert.alert('Removed', 'Product removed from wishlist');
            } catch (error) {
              Alert.alert('Error', 'Failed to remove product from wishlist');
            }
          },
        },
      ]
    );
  };

  const handleProductPress = (product) => {
    navigation.navigate('ProductDetail', { productId: product.id });
  };

  const handleContactSeller = (product) => {
    const contactInfo = product.contact_info || product.contactInfo;
    const platformUrl = product.platform_url || product.platformUrl;
    
    if (contactInfo) {
      const phoneNumber = contactInfo.replace(/\s/g, '');
      Linking.openURL(`https://wa.me/${phoneNumber.replace('+', '')}`);
    } else if (platformUrl) {
      Linking.openURL(platformUrl);
    } else {
      Alert.alert('Contact Info', 'Contact information not available');
    }
  };

  const renderWishlistItem = ({ item }) => {
    const product = item.product || item;
    const price = product.price ? parseFloat(product.price).toFixed(0) : null;
    const originalPrice = product.original_price ? parseFloat(product.original_price).toFixed(0) : null;
    const imageUrl = product.main_image_url || product.image_url || 'https://via.placeholder.com/300';
    const contactInfo = product.contact_info || '';
    
    return (
      <View style={styles.productCard}>
        <TouchableOpacity
          onPress={() => handleProductPress(product)}
          style={styles.imageContainer}
        >
          <Image
            source={{ uri: imageUrl }}
            style={styles.productImage}
            resizeMode="cover"
          />
          <TouchableOpacity
            style={styles.removeButton}
            onPress={() => handleRemoveFromWishlist(item)}
          >
            <Text style={styles.removeButtonText}>✕</Text>
          </TouchableOpacity>
        </TouchableOpacity>

        <View style={styles.productInfo}>
          <TouchableOpacity onPress={() => handleProductPress(product)}>
            <Text style={styles.productName} numberOfLines={2}>
              {product.name}
            </Text>
          </TouchableOpacity>

          <View style={styles.categoryContainer}>
            <Text style={styles.categoryText}>{product.category_name || 'General'}</Text>
            <View style={styles.platformBadge}>
              <Text style={styles.badgeText}>{product.platform || 'Multiple'}</Text>
            </View>
          </View>

          <View style={styles.priceContainer}>
            <Text style={styles.price}>
              {price ? `Rs. ${parseInt(price).toLocaleString()}` : 'Contact Seller'}
            </Text>
            {originalPrice && price && parseFloat(originalPrice) > parseFloat(price) && (
              <Text style={styles.originalPrice}>Rs. {parseInt(originalPrice).toLocaleString()}</Text>
            )}
          </View>

          {contactInfo && (
            <TouchableOpacity
              style={styles.contactButton}
              onPress={() => handleContactSeller(product)}
            >
              <Text style={styles.contactButtonText}>📱 Contact Seller</Text>
            </TouchableOpacity>
          )}
        </View>
      </View>
    );
  };

  // Don't render if not authenticated (will redirect)
  if (!isAuthenticated) {
    return null;
  }

  if (loading) {
    return (
      <SafeAreaView style={styles.safeArea} edges={['top', 'bottom']}>
        <View style={styles.loadingContainer}>
          <ActivityIndicator size="large" color="#2563eb" />
          <Text style={styles.loadingText}>Loading your wishlist...</Text>
        </View>
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView style={styles.safeArea} edges={['top', 'bottom']}>
      <View style={styles.container}>
      {/* Header */}
      <View style={styles.header}>
        <TouchableOpacity onPress={() => navigation.goBack()}>
          <Text style={styles.backButton}>← Back</Text>
        </TouchableOpacity>
        <View style={styles.headerTitleContainer}>
          <Text style={styles.headerIcon}>❤️</Text>
          <Text style={styles.headerTitle}>My Wishlist</Text>
        </View>
        <Text style={styles.itemCount}>{wishlistItems.length}</Text>
      </View>

      {/* Wishlist Content */}
      {wishlistItems.length === 0 ? (
        <View style={styles.emptyContainer}>
          <Text style={styles.emptyIcon}>💗</Text>
          <Text style={styles.emptyTitle}>Your wishlist is empty</Text>
          <Text style={styles.emptyText}>
            Start adding products you love to your wishlist!
          </Text>
          <TouchableOpacity
            style={styles.browseButton}
            onPress={() => navigation.navigate('Products')}
          >
            <Text style={styles.browseButtonText}>Browse Products</Text>
          </TouchableOpacity>
        </View>
      ) : (
        <FlatList
          data={wishlistItems}
          renderItem={renderWishlistItem}
          keyExtractor={(item) => item.id.toString()}
          numColumns={2}
          contentContainerStyle={styles.wishlistList}
          columnWrapperStyle={styles.row}
          showsVerticalScrollIndicator={false}
        />
      )}
      </View>
    </SafeAreaView>
  );
};

export default WishlistScreen;

const styles = StyleSheet.create({
  safeArea: {
    flex: 1,
    backgroundColor: '#f9fafb',
  },
  container: {
    flex: 1,
    backgroundColor: '#f9fafb',
  },
  loadingContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: '#f9fafb',
  },
  loadingText: {
    marginTop: 10,
    fontSize: 16,
    color: '#666',
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingHorizontal: 16,
    paddingVertical: 12,
    backgroundColor: '#fff',
    borderBottomWidth: 1,
    borderBottomColor: '#e0e0e0',
  },
  backButton: {
    fontSize: 16,
    color: '#2563eb',
    fontWeight: '600',
  },
  headerTitleContainer: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  headerIcon: {
    fontSize: 20,
    marginRight: 8,
  },
  headerTitle: {
    fontSize: 20,
    fontWeight: 'bold',
    color: '#333',
  },
  itemCount: {
    fontSize: 14,
    color: '#666',
    fontWeight: '600',
  },
  wishlistList: {
    padding: 8,
  },
  row: {
    justifyContent: 'space-between',
    paddingHorizontal: 4,
  },
  productCard: {
    flex: 1,
    backgroundColor: '#fff',
    borderRadius: 12,
    margin: 4,
    overflow: 'hidden',
    elevation: 2,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
  },
  imageContainer: {
    position: 'relative',
  },
  productImage: {
    width: '100%',
    height: 200,
    backgroundColor: '#f0f0f0',
  },
  removeButton: {
    position: 'absolute',
    top: 8,
    right: 8,
    width: 28,
    height: 28,
    borderRadius: 14,
    backgroundColor: '#fff',
    justifyContent: 'center',
    alignItems: 'center',
    elevation: 3,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.2,
    shadowRadius: 4,
  },
  removeButtonText: {
    fontSize: 16,
    color: '#e74c3c',
    fontWeight: 'bold',
  },
  productInfo: {
    padding: 12,
  },
  productName: {
    fontSize: 14,
    fontWeight: '600',
    color: '#333',
    marginBottom: 8,
    minHeight: 36,
  },
  categoryContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 8,
  },
  categoryText: {
    fontSize: 12,
    color: '#666',
    marginRight: 8,
  },
  platformBadge: {
    backgroundColor: '#e3f2fd',
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 12,
  },
  badgeText: {
    fontSize: 10,
    color: '#0984e3',
    fontWeight: '600',
  },
  priceContainer: {
    marginBottom: 12,
  },
  price: {
    fontSize: 18,
    fontWeight: 'bold',
    color: '#2563eb',
    marginBottom: 4,
  },
  originalPrice: {
    fontSize: 12,
    color: '#999',
    textDecorationLine: 'line-through',
  },
  contactButton: {
    backgroundColor: '#27ae60',
    paddingVertical: 10,
    borderRadius: 8,
    alignItems: 'center',
  },
  contactButtonText: {
    color: '#fff',
    fontSize: 14,
    fontWeight: 'bold',
  },
  emptyContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    paddingHorizontal: 40,
  },
  emptyIcon: {
    fontSize: 64,
    marginBottom: 16,
  },
  emptyTitle: {
    fontSize: 20,
    fontWeight: 'bold',
    color: '#333',
    marginBottom: 8,
    textAlign: 'center',
  },
  emptyText: {
    fontSize: 14,
    color: '#666',
    textAlign: 'center',
    marginBottom: 24,
  },
  browseButton: {
    backgroundColor: '#2563eb',
    paddingHorizontal: 24,
    paddingVertical: 12,
    borderRadius: 8,
  },
  browseButtonText: {
    color: '#fff',
    fontSize: 16,
    fontWeight: 'bold',
  },
});

