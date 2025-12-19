import { StyleSheet, Text, View, TouchableOpacity, Image, ActivityIndicator } from 'react-native'
import React, { useState, useEffect } from 'react'
import { useNavigation } from '@react-navigation/native'
import { productsAPI } from '../../AppBackend/api'

const WhatsNewsection = () => {
  const navigation = useNavigation();
  const [products, setProducts] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchNewProducts = async () => {
      try {
        setLoading(true);
        // Get newest products
        const data = await productsAPI.getProducts({ ordering: '-created_at' });
        setProducts(Array.isArray(data.results || data) ? (data.results || data).slice(0, 4) : []);
      } catch (error) {
        console.error('Error fetching new products:', error);
        setProducts([]);
      } finally {
        setLoading(false);
      }
    };

    fetchNewProducts();
  }, []);

  if (loading) {
    return (
      <View style={styles.container}>
        <Text style={styles.title}>What's New</Text>
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
      {/* Title + Explore More in one row */}
      <View style={styles.headerRow}>
        <Text style={styles.title}>What's New</Text>

        <TouchableOpacity 
          style={styles.exploreButton}
          onPress={() => navigation.navigate('Products')}
        >
          <Text style={styles.exploreText}>Explore More</Text>
        </TouchableOpacity>
      </View>

      <Text style={styles.afterwhatsnewtext}>
        Looking for more than just products? Discover services too — all in one smart search
      </Text>

      <View style={styles.gridContainer}>
        {products.map((item, index) => (
          <View key={item.id || index} style={styles.card}>
            
            {/* Image Section */}
            <View style={styles.productimgsection}>
              <Image
                source={{ uri: item.main_image_url || item.image_url || 'https://via.placeholder.com/300' }}
                style={styles.productimg}
                resizeMode="cover"
              />
              <View style={styles.badgeContainer}>
                <Text style={styles.badgeText}>New</Text>
              </View>
            </View>

            {/* Product Details */}
            <View style={styles.productdetailsection}>
              <Text style={styles.productname} numberOfLines={2}>{item.name}</Text>
              <Text style={styles.description} numberOfLines={2}>
                {item.description || item.short_description || 'Check out this new product!'}
              </Text>

              <View style={styles.row}>
                <Text style={styles.availabletxt}>Available on:</Text>
                <Text style={styles.platform}>{item.platform || 'Multiple'}</Text>
              </View>
            </View>
          </View>
        ))}
      </View>
    </View>
  )
}

export default WhatsNewsection

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
  headerRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginVertical: 10,
  },
  title: {
    fontSize: 22,
    fontWeight: 'bold',
    color: '#000',
  },
  exploreButton: {
    backgroundColor: '#FFFFFF',
    paddingVertical: 6,
    paddingHorizontal: 12,
    borderRadius: 8,
    borderWidth: 1.5,
    borderColor: '#2563eb',
  },
  exploreText: {
    color: '#2563eb',
    fontWeight: 'bold',
    fontSize: 12,
  },
  afterwhatsnewtext: {
    fontSize: 12,
    color: "grey",
    fontWeight: 'bold',
    marginTop: 5,
    marginBottom: 10,
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
    position: 'relative',
  },
  productimg: {
    width: "100%",
    height: 120,
    borderRadius: 8,
  },
  badgeContainer: {
    position: 'absolute',
    top: 8,
    left: 8,
    backgroundColor: '#2563eb',
    borderRadius: 6,
    paddingVertical: 2,
    paddingHorizontal: 6,
  },
  badgeText: {
    color: '#fff',
    fontSize: 10,
    fontWeight: 'bold',
  },
  productdetailsection: {
    flex: 1,
  },
  productname: {
    fontSize: 14,
    fontWeight: "bold",
    marginBottom: 4,
  },
  description: {
    fontSize: 12,
    color: "gray",
    marginBottom: 6,
  },
  row: {
    flexDirection: "row",
    alignItems: "center",
    flexWrap: 'wrap',
    marginBottom: 5,
  },
  availabletxt: {
    fontSize: 12,
    fontWeight: "bold",
  },
  platform: {
    fontSize: 12,
    fontWeight: "bold",
    color: "#2563eb",
    marginLeft: 4,
  },
})
