import React, { useState, useEffect } from 'react';
import {
  StyleSheet,
  Text,
  View,
  ScrollView,
  Image,
  TouchableOpacity,
  ActivityIndicator,
  Alert,
  Linking,
} from 'react-native';
import { useNavigation, useRoute } from '@react-navigation/native';
import { useAuth } from '../contexts/AuthContext';
import { SafeAreaView } from 'react-native-safe-area-context';
import { productsAPI, wishlistAPI } from '../../AppBackend/api';

const ProductDetailScreen = () => {
  const navigation = useNavigation();
  const route = useRoute();
  const { productId } = route.params || {};
  const { isAuthenticated } = useAuth();
  
  const [product, setProduct] = useState(null);
  const [loading, setLoading] = useState(true);
  const [inWishlist, setInWishlist] = useState(false);

  useEffect(() => {
    const fetchProduct = async () => {
      if (!productId) {
        setLoading(false);
        return;
      }

      setLoading(true);
      try {
        const productData = await productsAPI.getProduct(productId);
        setProduct(productData);
        
        // Track view
        productsAPI.trackView(productId);
        
        // Check if in wishlist
        if (isAuthenticated) {
          const inWishlist = await wishlistAPI.isInWishlist(productId);
          setInWishlist(inWishlist);
        }
      } catch (error) {
        console.error('Error fetching product:', error);
        setProduct(null);
      } finally {
        setLoading(false);
      }
    };

    fetchProduct();
  }, [productId, isAuthenticated]);

  const handleAddToWishlist = async () => {
    // Match web behavior: redirect to login if not authenticated
    if (!isAuthenticated) {
      navigation.navigate('LoginScreen');
      return;
    }
    
    try {
      if (inWishlist) {
        await wishlistAPI.removeFromWishlist(productId);
        setInWishlist(false);
        Alert.alert('Removed from Wishlist', 'Product removed from your wishlist');
      } else {
        await wishlistAPI.addToWishlist(productId);
        setInWishlist(true);
        Alert.alert('Added to Wishlist', 'Product added to your wishlist');
      }
    } catch (error) {
      Alert.alert('Error', error.message || 'Failed to update wishlist');
    }
  };

  const handleContactSeller = () => {
    const contactInfo = product?.contact_info || product?.contactInfo;
    if (contactInfo) {
      const phoneNumber = contactInfo.replace(/\s/g, '');
      Linking.openURL(`https://wa.me/${phoneNumber.replace('+', '')}`);
    } else {
      Alert.alert('Contact Info', 'Contact information not available');
    }
  };

  const handleViewOnPlatform = () => {
    const platformUrl = product?.platform_url || product?.platformUrl;
    if (platformUrl) {
      Linking.openURL(platformUrl);
    } else {
      Alert.alert('Platform URL', 'Platform URL not available');
    }
  };

  if (loading) {
    return (
      <SafeAreaView style={styles.safeArea} edges={['top', 'bottom']}>
        <View style={styles.loadingContainer}>
          <ActivityIndicator size="large" color="#2563eb" />
          <Text style={styles.loadingText}>Loading product details...</Text>
        </View>
      </SafeAreaView>
    );
  }

  if (!product) {
    return (
      <SafeAreaView style={styles.safeArea} edges={['top', 'bottom']}>
        <View style={styles.errorContainer}>
          <Text style={styles.errorText}>Product not found</Text>
          <TouchableOpacity
            style={styles.backButton}
            onPress={() => navigation.goBack()}
          >
            <Text style={styles.backButtonText}>Back to Products</Text>
          </TouchableOpacity>
        </View>
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView style={styles.safeArea} edges={['top', 'bottom']}>
      <View style={styles.container}>
      <ScrollView showsVerticalScrollIndicator={false}>
        {/* Product Image */}
        <View style={styles.imageContainer}>
          <Image
            source={{ uri: product.main_image_url || product.image_url || 'https://via.placeholder.com/400' }}
            style={styles.productImage}
            resizeMode="cover"
          />
        </View>

        {/* Product Details */}
        <View style={styles.detailsContainer}>
          <Text style={styles.productName}>{product.name}</Text>

          {/* Platform and Brand */}
          <View style={styles.badgeContainer}>
            <View style={styles.badge}>
              <Text style={styles.badgeText}>{product.platform || 'Multiple'}</Text>
            </View>
            {product.brand_name && (
              <View style={[styles.badge, styles.brandBadge]}>
                <Text style={styles.badgeText}>{product.brand_name}</Text>
              </View>
            )}
            {product.availability !== false ? (
              <View style={[styles.badge, styles.availableBadge]}>
                <Text style={styles.badgeText}>Available</Text>
              </View>
            ) : (
              <View style={[styles.badge, styles.unavailableBadge]}>
                <Text style={styles.badgeText}>Out of Stock</Text>
              </View>
            )}
          </View>

          {/* Price */}
          <View style={styles.priceContainer}>
            {product.price ? (
              <>
                <Text style={styles.price}>Rs. {parseInt(product.price).toLocaleString()}</Text>
                {product.original_price && parseFloat(product.original_price) > parseFloat(product.price) && (
                  <Text style={styles.originalPrice}>Rs. {parseInt(product.original_price).toLocaleString()}</Text>
                )}
              </>
            ) : (
              <Text style={styles.price}>Contact Seller</Text>
            )}
          </View>

          {/* Description */}
          {(product.description || product.short_description) && (
            <View style={styles.descriptionContainer}>
              <Text style={styles.descriptionTitle}>Description</Text>
              <Text style={styles.description}>
                {product.description || product.short_description}
              </Text>
            </View>
          )}

          {/* Product Information */}
          <View style={styles.infoContainer}>
            <Text style={styles.infoTitle}>Product Information</Text>
            <View style={styles.infoRow}>
              <Text style={styles.infoLabel}>Platform:</Text>
              <Text style={styles.infoValue}>{product.platform || 'Multiple'}</Text>
            </View>
            {product.brand_name && (
              <View style={styles.infoRow}>
                <Text style={styles.infoLabel}>Brand:</Text>
                <Text style={styles.infoValue}>{product.brand_name}</Text>
              </View>
            )}
            {product.category_name && (
              <View style={styles.infoRow}>
                <Text style={styles.infoLabel}>Category:</Text>
                <Text style={styles.infoValue}>{product.category_name}</Text>
              </View>
            )}
          </View>

          {/* Action Buttons */}
          <View style={styles.actionsContainer}>
            <TouchableOpacity
              style={[
                styles.actionButton,
                inWishlist ? styles.wishlistButtonActive : styles.wishlistButton,
              ]}
              onPress={handleAddToWishlist}
            >
              <Text
                style={[
                  styles.actionButtonText,
                  inWishlist && styles.actionButtonTextActive,
                ]}
              >
                {inWishlist ? 'Remove from Wishlist' : 'Add to Wishlist'}
              </Text>
            </TouchableOpacity>

            {(product.contact_info || product.contactInfo) && (
              <TouchableOpacity
                style={[styles.actionButton, styles.contactButton]}
                onPress={handleContactSeller}
              >
                <Text style={styles.actionButtonText}>Contact Seller</Text>
              </TouchableOpacity>
            )}

            {(product.platform_url || product.platformUrl) && (
              <TouchableOpacity
                style={[styles.actionButton, styles.platformButton]}
                onPress={handleViewOnPlatform}
              >
                <Text style={styles.actionButtonText}>
                  View on {product.platform || 'Platform'}
                </Text>
              </TouchableOpacity>
            )}
          </View>
        </View>
      </ScrollView>
    </View>
    </SafeAreaView>
  );
};

export default ProductDetailScreen;

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
    backgroundColor: '#f5f5f5',
  },
  loadingText: {
    marginTop: 10,
    fontSize: 16,
    color: '#666',
  },
  errorContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: '#f5f5f5',
    padding: 20,
  },
  errorText: {
    fontSize: 18,
    color: '#666',
    marginBottom: 20,
  },
  backButton: {
    backgroundColor: '#2563eb',
    paddingVertical: 12,
    paddingHorizontal: 24,
    borderRadius: 8,
  },
  backButtonText: {
    color: '#fff',
    fontSize: 16,
    fontWeight: 'bold',
  },
  imageContainer: {
    width: '100%',
    height: 400,
    backgroundColor: '#fff',
  },
  productImage: {
    width: '100%',
    height: '100%',
  },
  detailsContainer: {
    backgroundColor: '#fff',
    padding: 20,
    marginTop: 10,
  },
  productName: {
    fontSize: 24,
    fontWeight: 'bold',
    color: '#333',
    marginBottom: 12,
  },
  badgeContainer: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    marginBottom: 16,
  },
  badge: {
    backgroundColor: '#e0e0e0',
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 16,
    marginRight: 8,
    marginBottom: 8,
  },
  brandBadge: {
    backgroundColor: '#e3f2fd',
  },
  availableBadge: {
    backgroundColor: '#c8e6c9',
  },
  unavailableBadge: {
    backgroundColor: '#ffcdd2',
  },
  badgeText: {
    fontSize: 12,
    color: '#333',
    fontWeight: '600',
  },
  priceContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 20,
    paddingVertical: 12,
    borderTopWidth: 1,
    borderBottomWidth: 1,
    borderColor: '#e0e0e0',
  },
  price: {
    fontSize: 32,
    fontWeight: 'bold',
    color: '#2563eb',
    marginRight: 12,
  },
  originalPrice: {
    fontSize: 18,
    color: '#999',
    textDecorationLine: 'line-through',
  },
  descriptionContainer: {
    marginBottom: 20,
  },
  descriptionTitle: {
    fontSize: 18,
    fontWeight: 'bold',
    color: '#333',
    marginBottom: 8,
  },
  description: {
    fontSize: 16,
    color: '#666',
    lineHeight: 24,
  },
  infoContainer: {
    marginBottom: 20,
    paddingTop: 16,
    borderTopWidth: 1,
    borderColor: '#e0e0e0',
  },
  infoTitle: {
    fontSize: 18,
    fontWeight: 'bold',
    color: '#333',
    marginBottom: 12,
  },
  infoRow: {
    flexDirection: 'row',
    marginBottom: 8,
  },
  infoLabel: {
    fontSize: 14,
    color: '#999',
    width: 100,
  },
  infoValue: {
    fontSize: 14,
    color: '#333',
    fontWeight: '600',
    flex: 1,
  },
  actionsContainer: {
    marginTop: 20,
  },
  actionButton: {
    paddingVertical: 14,
    paddingHorizontal: 20,
    borderRadius: 8,
    marginBottom: 12,
    alignItems: 'center',
  },
  wishlistButton: {
    backgroundColor: '#fff',
    borderWidth: 1,
    borderColor: '#e0e0e0',
  },
  wishlistButtonActive: {
    backgroundColor: '#e74c3c',
  },
  contactButton: {
    backgroundColor: '#27ae60',
  },
  platformButton: {
    backgroundColor: '#2563eb',
  },
  actionButtonText: {
    fontSize: 16,
    fontWeight: 'bold',
    color: '#333',
  },
  actionButtonTextActive: {
    color: '#fff',
  },
});

