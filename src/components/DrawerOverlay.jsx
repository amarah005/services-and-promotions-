import React, { useState, useEffect, useRef } from 'react';
import {
  StyleSheet,
  Text,
  View,
  TouchableOpacity,
  Animated,
  Dimensions,
  ScrollView,
  ActivityIndicator,
  Modal,
  TouchableWithoutFeedback
} from 'react-native';
import { useNavigation } from '@react-navigation/native';
import Feather from 'react-native-vector-icons/Feather';
import { categoriesAPI } from '../../AppBackend/api';
import {
  getCategoryIconName,
  sortCategoriesByOrder
} from '../utils/categoryUtils';

const { width, height } = Dimensions.get('window');
const SIDEBAR_WIDTH = width * 0.8;

const DrawerOverlay = ({ isOpen, onClose }) => {
  const navigation = useNavigation();
  const [expandedCategories, setExpandedCategories] = useState({});
  const [filterOptions, setFilterOptions] = useState({
    main_categories: [],
    subcategories: {},
  });
  const [loading, setLoading] = useState(true);

  // Animation value
  const slideAnim = useRef(new Animated.Value(-SIDEBAR_WIDTH)).current;

  useEffect(() => {
    if (isOpen) {
      Animated.timing(slideAnim, {
        toValue: 0,
        duration: 300,
        useNativeDriver: true,
      }).start();
      fetchCategories();
    } else {
      Animated.timing(slideAnim, {
        toValue: -SIDEBAR_WIDTH,
        duration: 300,
        useNativeDriver: true,
      }).start();
    }
  }, [isOpen]);

  const fetchCategories = async () => {
    try {
      setLoading(true);
      const response = await categoriesAPI.getCategories();
      const categoriesData = Array.isArray(response) ? response : (response?.results || []);

      if (categoriesData && Array.isArray(categoriesData)) {
        // Create hierarchical structure
        const mainCategories = Array.from(
          new Set(categoriesData.map(cat => cat.main_category).filter(Boolean))
        );

        // Group subcategories by main category
        const subcategoriesByMain = {};
        mainCategories.forEach(mainCat => {
          subcategoriesByMain[mainCat] = categoriesData
            .filter(cat => cat.main_category === mainCat && cat.subcategory && cat.subcategory !== '')
            .map(cat => cat.name);
        });

        setFilterOptions({
          main_categories: sortCategoriesByOrder(mainCategories),
          subcategories: subcategoriesByMain,
        });
      }
    } catch (err) {
      console.error('Error fetching categories:', err);
    } finally {
      setLoading(false);
    }
  };

  const toggleCategory = (index) => {
    setExpandedCategories(prev => ({
      ...prev,
      [index]: !prev[index]
    }));
  };

  const handleMainCategoryClick = (mainCategory) => {
    navigation.navigate('Products', { main_category: mainCategory });
    onClose();
  };

  const handleSubcategoryClick = (subcategory) => {
    navigation.navigate('Products', { subcategory: subcategory });
    onClose();
  };

  if (!isOpen && slideAnim._value === -SIDEBAR_WIDTH) return null;

  return (
    <Modal
      transparent={true}
      visible={isOpen}
      onRequestClose={onClose}
      animationType="none"
    >
      <View style={styles.overlay}>
        <TouchableWithoutFeedback onPress={onClose}>
          <View style={styles.backdrop} />
        </TouchableWithoutFeedback>

        <Animated.View
          style={[
            styles.sidebar,
            { transform: [{ translateX: slideAnim }] }
          ]}
        >
          {/* Header */}
          <View style={styles.header}>
            <Text style={styles.headerTitle}>Categories</Text>
            <TouchableOpacity onPress={onClose} style={styles.closeButton}>
              <Feather name="x" size={24} color="#4b5563" />
            </TouchableOpacity>
          </View>

          {/* Categories List */}
          {loading ? (
            <View style={styles.loadingContainer}>
              <ActivityIndicator size="large" color="#2563eb" />
              <Text style={styles.loadingText}>Loading categories...</Text>
            </View>
          ) : (
            <ScrollView style={styles.content} showsVerticalScrollIndicator={false}>
              {filterOptions.main_categories.length > 0 ? (
                filterOptions.main_categories.map((mainCategory, index) => {
                  const iconName = getCategoryIconName(mainCategory);
                  const subcategories = filterOptions.subcategories[mainCategory] || [];
                  const isExpanded = expandedCategories[index];

                  return (
                    <View key={index} style={styles.categoryItem}>
                      <View style={styles.mainCategoryRow}>
                        <TouchableOpacity
                          style={styles.mainCategoryButton}
                          onPress={() => handleMainCategoryClick(mainCategory)}
                        >
                          <Feather name={iconName} size={20} color="#4b5563" style={styles.categoryIcon} />
                          <Text style={styles.categoryText}>{mainCategory}</Text>
                        </TouchableOpacity>

                        {subcategories.length > 0 && (
                          <TouchableOpacity
                            style={styles.expandButton}
                            onPress={() => toggleCategory(index)}
                          >
                            <Feather
                              name={isExpanded ? "chevron-down" : "chevron-right"}
                              size={20}
                              color="#9ca3af"
                            />
                          </TouchableOpacity>
                        )}
                      </View>

                      {/* Subcategories */}
                      {isExpanded && subcategories.length > 0 && (
                        <View style={styles.subcategoriesContainer}>
                          {subcategories.map((subcategory, subIndex) => (
                            <TouchableOpacity
                              key={subIndex}
                              style={styles.subcategoryButton}
                              onPress={() => handleSubcategoryClick(subcategory)}
                            >
                              <Text style={styles.subcategoryText}>{subcategory}</Text>
                            </TouchableOpacity>
                          ))}
                        </View>
                      )}
                    </View>
                  );
                })
              ) : (
                <View style={styles.emptyContainer}>
                  <Text style={styles.emptyText}>No categories available</Text>
                </View>
              )}
              <View style={{ height: 80 }} />
            </ScrollView>
          )}

          {/* Footer */}
          <View style={styles.footer}>
            <TouchableOpacity
              style={styles.viewAllButton}
              onPress={() => {
                navigation.navigate('Products');
                onClose();
              }}
            >
              <Text style={styles.viewAllText}>View All Products</Text>
            </TouchableOpacity>
          </View>
        </Animated.View>
      </View>
    </Modal>
  );
};

const styles = StyleSheet.create({
  overlay: {
    flex: 1,
    backgroundColor: 'rgba(0, 0, 0, 0.5)',
  },
  backdrop: {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
  },
  sidebar: {
    width: SIDEBAR_WIDTH,
    height: '100%',
    backgroundColor: '#fff',
    shadowColor: '#000',
    shadowOffset: { width: 2, height: 0 },
    shadowOpacity: 0.25,
    shadowRadius: 3.84,
    elevation: 5,
  },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    padding: 16,
    borderBottomWidth: 1,
    borderBottomColor: '#e5e7eb',
  },
  headerTitle: {
    fontSize: 18,
    fontWeight: '600',
    color: '#1f2937',
  },
  closeButton: {
    padding: 4,
  },
  content: {
    flex: 1,
  },
  loadingContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    padding: 20,
  },
  loadingText: {
    marginTop: 10,
    color: '#6b7280',
  },
  categoryItem: {
    borderBottomWidth: 1,
    borderBottomColor: '#f3f4f6',
  },
  mainCategoryRow: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  mainCategoryButton: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'center',
    padding: 16,
  },
  categoryIcon: {
    marginRight: 12,
  },
  categoryText: {
    fontSize: 16,
    color: '#1f2937',
    fontWeight: '500',
  },
  expandButton: {
    padding: 16,
    borderLeftWidth: 1,
    borderLeftColor: '#f3f4f6',
  },
  subcategoriesContainer: {
    backgroundColor: '#f9fafb',
  },
  subcategoryButton: {
    paddingVertical: 12,
    paddingHorizontal: 16,
    paddingLeft: 48,
  },
  subcategoryText: {
    fontSize: 14,
    color: '#4b5563',
  },
  emptyContainer: {
    padding: 20,
    alignItems: 'center',
  },
  emptyText: {
    color: '#6b7280',
  },
  footer: {
    padding: 16,
    borderTopWidth: 1,
    borderTopColor: '#e5e7eb',
    backgroundColor: '#fff',
  },
  viewAllButton: {
    backgroundColor: '#2563eb',
    paddingVertical: 12,
    borderRadius: 8,
    alignItems: 'center',
  },
  viewAllText: {
    color: '#fff',
    fontSize: 16,
    fontWeight: '600',
  },
});

export default DrawerOverlay;
