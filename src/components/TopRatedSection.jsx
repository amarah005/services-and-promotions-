import { StyleSheet, Text, View, Image, TouchableOpacity, ActivityIndicator } from 'react-native'
import React, { useState, useEffect } from 'react'
import { useNavigation } from '@react-navigation/native'
import { productsAPI } from '../../AppBackend/api'
import { getRating } from '../utils/helper'

const TopRatedSection = () => {
  const navigation = useNavigation();
  const [products, setProducts] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchTrending = async () => {
      try {
        setLoading(true);
        const data = await productsAPI.getTrending();
        setProducts(Array.isArray(data) ? data.slice(0, 6) : []);
      } catch (error) {
        console.error('Error fetching trending products:', error);
        setProducts([]);
      } finally {
        setLoading(false);
      }
    };

    fetchTrending();
  }, []);

  if (loading) {
    return (
      <View style={styles.container}>
        <Text style={styles.title}>Trending Products</Text>
        <View style={styles.loadingContainer}>
          <ActivityIndicator size="small" color="#2563eb" />
        </View>
      </View>
    );
  }

  if (products.length === 0) {
    return null;
  }

  return (
    <View style={styles.container}>
      <Text style={styles.title}>Trending Products</Text>

      <View style={styles.gridContainer}>
        {products.map((item, index) => {
          const rating = item.average_rating || 0;
          const price = item.price ? parseFloat(item.price).toFixed(0) : null;
          const originalPrice = item.original_price ? parseFloat(item.original_price).toFixed(0) : null;

          return (
            <View key={item.id || index} style={styles.card}>
              <View style={styles.productimgsection}>
                <Image
                  source={{ uri: item.main_image_url || item.image_url || 'https://via.placeholder.com/300' }}
                  style={styles.productimg}
                  resizeMode="contain"
                />
              </View>

              <View style={styles.productdetailsection}>
                <Text style={styles.productname} numberOfLines={2}>{item.name}</Text>

                {rating > 0 && (
                  <View style={styles.row}>
                    {getRating(rating)}
                    <Text style={styles.rating}>{rating.toFixed(1)}</Text>
                  </View>
                )}

                <View style={styles.priceRow}>
                  {price ? (
                    <>
                      <Text style={styles.price}>Rs. {parseInt(price).toLocaleString()}</Text>
                      {originalPrice && parseFloat(originalPrice) > parseFloat(price) && (
                        <Text style={styles.crossout}>Rs. {parseInt(originalPrice).toLocaleString()}</Text>
                      )}
                    </>
                  ) : (
                    <Text style={styles.price}>Contact Seller</Text>
                  )}
                </View>

                {/* Available on row */}
                <View style={styles.platformRow}>
                  <Text style={styles.availabletxt}>Available on:</Text>
                  <Text style={styles.platform}>{item.platform || 'Multiple'}</Text>
                </View>

                {/* View Details button */}
                <TouchableOpacity
                  style={styles.button}
                  onPress={() => navigation.navigate('ProductDetail', { productId: item.id })}
                >
                  <Text style={styles.buttonText}>View Details</Text>
                </TouchableOpacity>
              </View>
            </View>
          );
        })}
      </View>
    </View>
  )
}

export default TopRatedSection

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: "#fff",
    padding: 10,
  },
  loadingContainer: {
    padding: 20,
    alignItems: 'center',
  },
  title: {
    fontSize: 22,
    fontWeight: 'bold',
    color: '#000',
    textAlign: 'center',
    marginVertical: 16,
  },
  gridContainer: {
    flexDirection: "row",
    flexWrap: "wrap",
    justifyContent: "space-between",
  },
  card: {
    width: "48%",
    backgroundColor: "#fff",
    borderRadius: 10,
    padding: 10,
    marginBottom: 15,
    elevation: 3,
    shadowOpacity: 0.1,
    shadowRadius: 5,
  },
  productimgsection: {
    alignItems: "center",
    marginBottom: 10,
  },
  productimg: {
    width: "100%",
    height: 120,
    borderRadius: 8,
  },
  productdetailsection: {
    flex: 1,
  },
  productname: {
    fontSize: 14,
    fontWeight: "bold",
    marginBottom: 5,
    flexWrap: 'wrap',
  },
  row: {
    flexDirection: "row",
    alignItems: "center",
    marginBottom: 5,
  },
  rating: {
    fontSize: 12,
    marginLeft: 4,
    color: '#555',
  },
  priceRow: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 6,
  },
  price: {
    fontSize: 14,
    fontWeight: "bold",
    color: "#2563eb",
  },
  crossout: {
    fontSize: 12,
    textDecorationLine: "line-through",
    marginLeft: 6,
    color: "gray",
  },
  platformRow: {
    flexDirection: 'row',
    alignItems: 'center',
    flexWrap: 'wrap',
    marginBottom: 8,
  },
  availabletxt: {
    fontSize: 12,
    fontWeight: "bold",
    color: '#000',
  },
  platform: {
    fontSize: 12,
    fontWeight: "bold",
    color: "#2563eb",
    marginLeft: 4,
  },
  button: {
    marginTop: 4,
    backgroundColor: '#2563eb',
    paddingVertical: 6,
    borderRadius: 6,
    alignItems: 'center',
  },
  buttonText: {
    color: '#fff',
    fontSize: 13,
    fontWeight: 'bold',
  },
})
