import { StyleSheet, Text, View, TouchableOpacity, Image, ScrollView, ActivityIndicator } from 'react-native'
import React, { useEffect, useState } from 'react'
import { useNavigation } from '@react-navigation/native'
import { categoriesAPI } from '../../AppBackend/api'
import { getUniqueCategories, getCategoryImage } from '../utils/categoryUtils'

const Category = () => {
  const navigation = useNavigation();
  const [categories, setCategories] = useState([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    fetchCategories();
  }, []);

  const fetchCategories = async () => {
    try {
      const response = await categoriesAPI.getCategories();
      // Handle paginated response structure
      const categoriesData = Array.isArray(response) ? response : (response?.results || []);

      if (categoriesData && Array.isArray(categoriesData)) {
        // Ensure categories are unique by name
        const uniqueCategories = getUniqueCategories(categoriesData);

        // Get unique main categories only
        const mainCategories = Array.from(
          new Set(uniqueCategories.map(c => c.main_category).filter(Boolean))
        );

        // Create home categories object
        const homeCategories = mainCategories.map(mainCategory => ({
          id: `main-${mainCategory.toLowerCase().replace(/\s+/g, '-')}`,
          name: mainCategory
        }));

        setCategories(homeCategories);
      } else {
        setCategories([]);
      }
    } catch (error) {
      console.error('Failed to fetch categories:', error);
      setCategories([]);
    } finally {
      setIsLoading(false);
    }
  };

  if (isLoading) {
    return (
      <View style={styles.loadingContainer}>
        <ActivityIndicator size="large" color="#2563eb" />
      </View>
    );
  }

  return (
    <ScrollView style={styles.container}>
      <Text style={styles.heading}>Our Categories</Text>

      <View style={styles.gridContainer}>
        {categories.map((category) => (
          <TouchableOpacity
            key={category.id}
            style={styles.card}
            onPress={() => navigation.navigate('Products', { category: category.name })}
          >
            <Image
              source={{ uri: getCategoryImage(category.name) }}
              style={styles.imageStyle}
              resizeMode="cover"
            />
            <Text style={styles.cardText}>{category.name}</Text>
          </TouchableOpacity>
        ))}
      </View>
    </ScrollView>
  )
}

export default Category

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#fff',
    padding: 16,
  },
  loadingContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    padding: 20,
  },
  heading: {
    fontSize: 22,
    fontWeight: 'bold',
    color: '#000',
    textAlign: 'center',
    marginVertical: 16,
  },
  gridContainer: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    justifyContent: 'space-between',
  },
  card: {
    width: '47%',
    backgroundColor: '#f9f9f9',
    borderRadius: 12,
    paddingVertical: 16,
    alignItems: 'center',
    marginBottom: 16, // adds spacing between rows
    elevation: 4,
    // shadowColor: '#000',
    shadowOpacity: 0.1,
    shadowOffset: { width: 0, height: 2 },
    shadowRadius: 4,
  },
  imageStyle: {
    width: 90,
    height: 90,
    // borderRadius: 45,
    marginBottom: 10,
    // backgroundColor: '#ddd', // fallback background
  },
  cardText: {
    fontSize: 14,
    fontWeight: '600',
    color: '#333',
    textAlign: 'center',
  },
})
