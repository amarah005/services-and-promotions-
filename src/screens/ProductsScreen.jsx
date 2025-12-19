import React, { useState, useEffect } from 'react';
import {
  StyleSheet,
  Text,
  View,
  ScrollView,
  FlatList,
  Image,
  TouchableOpacity,
  TextInput,
  ActivityIndicator,
  Animated,
  Modal,
} from 'react-native';
import { useNavigation, useRoute } from '@react-navigation/native';
import { SafeAreaView } from 'react-native-safe-area-context';
import LinearGradient from 'react-native-linear-gradient';
import { productsAPI, categoriesAPI } from '../../AppBackend/api';
import { sortCategoriesByOrder } from '../utils/categoryUtils';
import Feather from 'react-native-vector-icons/Feather';
import Ionicons from 'react-native-vector-icons/Ionicons';

// Custom Dropdown Component
const CustomDropdown = ({ options, selectedValue, onValueChange, placeholder, style, borderColor }) => {
  const [isOpen, setIsOpen] = useState(false);

  const selectedLabel = options.find(opt => opt.value === selectedValue)?.label || placeholder;

  return (
    <>
      <TouchableOpacity
        style={[styles.dropdownButton, style, { borderColor }]}
        onPress={() => setIsOpen(true)}
      >
        <Text style={styles.dropdownText}>{selectedLabel}</Text>
        <Feather name="chevron-down" size={16} color="#6b7280" />
      </TouchableOpacity>

      <Modal
        visible={isOpen}
        transparent={true}
        animationType="fade"
        onRequestClose={() => setIsOpen(false)}
      >
        <TouchableOpacity
          style={styles.dropdownOverlay}
          activeOpacity={1}
          onPress={() => setIsOpen(false)}
        >
          <View style={styles.dropdownModal}>
            <ScrollView style={styles.dropdownList}>
              <TouchableOpacity
                style={styles.dropdownItem}
                onPress={() => {
                  onValueChange('');
                  setIsOpen(false);
                }}
              >
                <Text style={[styles.dropdownItemText, !selectedValue && styles.dropdownItemTextSelected]}>
                  {placeholder}
                </Text>
              </TouchableOpacity>
              {options.map((option) => (
                <TouchableOpacity
                  key={option.value}
                  style={styles.dropdownItem}
                  onPress={() => {
                    onValueChange(option.value);
                    setIsOpen(false);
                  }}
                >
                  <Text style={[styles.dropdownItemText, selectedValue === option.value && styles.dropdownItemTextSelected]}>
                    {option.label}
                  </Text>
                </TouchableOpacity>
              ))}
            </ScrollView>
          </View>
        </TouchableOpacity>
      </Modal>
    </>
  );
};

const ProductsScreen = () => {
  const navigation = useNavigation();
  const route = useRoute();
  const initialCategory = route.params?.main_category || route.params?.category || '';
  const initialSubcategory = route.params?.subcategory || '';

  const [products, setProducts] = useState([]);
  const [totalProducts, setTotalProducts] = useState(0);
  const [loading, setLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [page, setPage] = useState(1);
  const [hasMore, setHasMore] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [isFilterExpanded, setIsFilterExpanded] = useState(false);
  const [tempCategory, setTempCategory] = useState(initialCategory);
  const [tempSubcategory, setTempSubcategory] = useState(initialSubcategory);
  const [tempPlatform, setTempPlatform] = useState('');
  const [tempBrand, setTempBrand] = useState('');
  const [tempSortBy, setTempSortBy] = useState('-created_at');
  const [tempMinPrice, setTempMinPrice] = useState('');
  const [tempMaxPrice, setTempMaxPrice] = useState('');

  // Applied filters
  const [selectedCategory, setSelectedCategory] = useState(initialCategory);
  const [selectedSubcategory, setSelectedSubcategory] = useState(initialSubcategory);
  const [selectedPlatform, setSelectedPlatform] = useState('');
  const [selectedBrand, setSelectedBrand] = useState('');
  const [sortBy, setSortBy] = useState('-created_at');
  const [minPrice, setMinPrice] = useState('');
  const [maxPrice, setMaxPrice] = useState('');

  // Filter options
  const [filterOptions, setFilterOptions] = useState({
    main_categories: [],
    subcategories: [],
    platforms: [],
    brands: [],
    price_range: { min: 0, max: 0 },
  });
  const [allSubcategories, setAllSubcategories] = useState({});

  const sortOptions = [
    { label: 'Newest First', value: '-created_at' },
    { label: 'Price: Low to High', value: 'price' },
    { label: 'Price: High to Low', value: '-price' },
    { label: 'Most Viewed', value: '-view_count' },
    { label: 'Most Wishlisted', value: '-wishlist_count' },
    { label: 'Name: A to Z', value: 'name' },
    { label: 'Name: Z to A', value: '-name' },
  ];

  // Fetch categories and structure them like Sidebar
  useEffect(() => {
    const fetchCategories = async () => {
      try {
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

          const sortedMainCategories = sortCategoriesByOrder(mainCategories);

          setAllSubcategories(subcategoriesByMain);
          setFilterOptions(prev => ({
            ...prev,
            main_categories: sortedMainCategories,
            subcategories: initialCategory ? (subcategoriesByMain[initialCategory] || []) : [],
          }));
        }
      } catch (error) {
        console.error('Error fetching categories:', error);
      }
    };

    fetchCategories();
  }, []);

  // Fetch other filter options (brands, platforms)
  useEffect(() => {
    const fetchOtherOptions = async () => {
      try {
        const options = await productsAPI.getFilterOptions(selectedCategory, selectedSubcategory);
        setFilterOptions(prev => ({
          ...prev,
          platforms: options.platforms || [],
          brands: options.brands || [],
          price_range: options.price_range || { min: 0, max: 0 },
        }));
      } catch (error) {
        console.error('Error fetching other filter options:', error);
      }
    };
    fetchOtherOptions();
  }, [selectedCategory, selectedSubcategory]);

  // Update available subcategories when temp category changes
  useEffect(() => {
    if (tempCategory) {
      const subs = allSubcategories[tempCategory] || [];
      setFilterOptions(prev => ({
        ...prev,
        subcategories: subs
      }));
    } else {
      setFilterOptions(prev => ({
        ...prev,
        subcategories: []
      }));
    }
  }, [tempCategory, allSubcategories]);

  const getActiveFiltersCount = () => {
    let count = 0;
    if (selectedCategory) count++;
    if (selectedSubcategory) count++;
    if (selectedPlatform) count++;
    if (selectedBrand) count++;
    if (minPrice) count++;
    if (maxPrice) count++;
    if (sortBy && sortBy !== '-created_at') count++;
    return count;
  };

  // Fetch products function
  const fetchProducts = async (pageNumber = 1, shouldAppend = false) => {
    if (pageNumber === 1) setLoading(true);
    else setLoadingMore(true);

    try {
      const params = { page: pageNumber };

      if (selectedCategory) params.main_category = selectedCategory;
      if (selectedSubcategory) params.subcategory = selectedSubcategory;
      if (selectedPlatform) params.platform = selectedPlatform;
      if (selectedBrand) params.brand = selectedBrand;
      if (minPrice) params.min_price = minPrice;
      if (maxPrice) params.max_price = maxPrice;
      if (sortBy) params.ordering = sortBy;
      if (searchQuery) params.search = searchQuery;

      const response = await productsAPI.getProducts(params);

      const newProducts = Array.isArray(response.results) ? response.results : (Array.isArray(response) ? response : []);
      const nextUrl = response.next;

      if (response.count !== undefined) {
        setTotalProducts(response.count);
      }

      if (shouldAppend) {
        setProducts(prev => [...prev, ...newProducts]);
      } else {
        setProducts(newProducts);
      }

      setHasMore(!!nextUrl);
    } catch (error) {
      console.error('Error fetching products:', error);
      if (!shouldAppend) setProducts([]);
    } finally {
      setLoading(false);
      setLoadingMore(false);
    }
  };

  // Reset and fetch when filters change
  useEffect(() => {
    setPage(1);
    fetchProducts(1, false);
  }, [selectedCategory, selectedSubcategory, selectedPlatform, selectedBrand, minPrice, maxPrice, sortBy, searchQuery]);

  const handleLoadMore = () => {
    if (!loadingMore && hasMore && !loading) {
      const nextPage = page + 1;
      setPage(nextPage);
      fetchProducts(nextPage, true);
    }
  };

  // Products are already filtered by backend, no need for client-side filtering
  const filteredProducts = products;

  const handleProductPress = (product) => {
    navigation.navigate('ProductDetail', { productId: product.id });
  };

  const applyFilters = () => {
    setSelectedCategory(tempCategory);
    setSelectedSubcategory(tempSubcategory);
    setSelectedPlatform(tempPlatform);
    setSelectedBrand(tempBrand);
    setSortBy(tempSortBy);
    setMinPrice(tempMinPrice);
    setMaxPrice(tempMaxPrice);
    setIsFilterExpanded(false);
  };

  const clearAllFilters = () => {
    setSelectedCategory('');
    setSelectedSubcategory('');
    setSelectedPlatform('');
    setSelectedBrand('');
    setSortBy('-created_at');
    setMinPrice('');
    setMaxPrice('');
    setTempCategory('');
    setTempSubcategory('');
    setTempPlatform('');
    setTempBrand('');
    setTempSortBy('-created_at');
    setTempMinPrice('');
    setTempMaxPrice('');
  };

  const renderProductItem = ({ item }) => {
    const price = item.price ? parseFloat(item.price).toFixed(0) : null;
    const originalPrice = item.original_price ? parseFloat(item.original_price).toFixed(0) : null;
    const imageUrl = item.main_image_url || item.image_url || 'https://via.placeholder.com/300';

    return (
      <TouchableOpacity
        style={styles.productCard}
        onPress={() => handleProductPress(item)}
      >
        <Image
          source={{ uri: imageUrl }}
          style={styles.productImage}
          resizeMode="cover"
        />
        <View style={styles.productInfo}>
          <Text style={styles.productName} numberOfLines={2}>
            {item.name}
          </Text>
          <View style={styles.priceContainer}>
            {price ? (
              <>
                <Text style={styles.price}>Rs. {parseInt(price).toLocaleString()}</Text>
                {originalPrice && parseFloat(originalPrice) > parseFloat(price) && (
                  <Text style={styles.originalPrice}>Rs. {parseInt(originalPrice).toLocaleString()}</Text>
                )}
              </>
            ) : (
              <Text style={styles.price}>Contact Seller</Text>
            )}
          </View>
          <View style={styles.badgeContainer}>
            <View style={styles.platformBadge}>
              <Text style={styles.badgeText}>{item.platform || 'Multiple'}</Text>
            </View>
            {item.brand_name && (
              <View style={styles.brandBadge}>
                <Text style={styles.badgeText}>{item.brand_name}</Text>
              </View>
            )}
          </View>
          <TouchableOpacity
            style={styles.viewButton}
            onPress={() => handleProductPress(item)}
          >
            <Text style={styles.viewButtonText}>View Details</Text>
          </TouchableOpacity>
        </View>
      </TouchableOpacity>
    );
  };

  if (loading) {
    return (
      <SafeAreaView style={styles.safeArea} edges={['top', 'bottom']}>
        <View style={styles.loadingContainer}>
          <ActivityIndicator size="large" color="#2563eb" />
          <Text style={styles.loadingText}>Loading products...</Text>
        </View>
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView style={styles.safeArea} edges={['top', 'bottom']}>
      <ScrollView style={styles.container} showsVerticalScrollIndicator={false}>
        {/* Header Section */}
        <View style={styles.headerSection}>
          <View style={styles.headerRow}>
            <TouchableOpacity onPress={() => navigation.goBack()}>
              <Feather name="arrow-left" size={20} color="#2563eb" />
            </TouchableOpacity>
            <Text style={styles.headerTitle}>All Products</Text>
            <View style={styles.placeholder} />
          </View>
        </View>

        {/* Title Section - Matching Web */}
        <View style={styles.titleSection}>
          <Text style={styles.mainTitle}>All Products</Text>
          <Text style={styles.subtitle}>
            {totalProducts > 0 ? `Showing ${totalProducts} products` : 'Discover amazing products'}
          </Text>
        </View>

        {/* Breadcrumb - When filters active */}
        {(selectedCategory || selectedSubcategory) && (
          <View style={styles.breadcrumbContainer}>
            <View style={styles.breadcrumbRow}>
              <Text style={styles.breadcrumbLabel}>Filtered by:</Text>
              {selectedCategory && (
                <View style={styles.breadcrumbBadge}>
                  <Text style={styles.breadcrumbBadgeText}>{selectedCategory}</Text>
                </View>
              )}
              {selectedSubcategory && (
                <>
                  <Text style={styles.breadcrumbArrow}>→</Text>
                  <View style={[styles.breadcrumbBadge, styles.breadcrumbBadgeGreen]}>
                    <Text style={styles.breadcrumbBadgeTextGreen}>{selectedSubcategory}</Text>
                  </View>
                </>
              )}
              <TouchableOpacity onPress={clearAllFilters} style={styles.clearFiltersBtn}>
                <Feather name="x" size={12} color="#dc2626" />
                <Text style={styles.clearFiltersText}>Clear filters</Text>
              </TouchableOpacity>
            </View>
          </View>
        )}

        {/* Filter Section - Matching Web Design */}
        <LinearGradient
          colors={['#eff6ff', '#eef2ff']}
          style={styles.filterContainer}
        >
          {/* Filter Header */}
          <View style={styles.filterHeader}>
            <View style={styles.filterHeaderRow}>
              <View style={styles.filterTitleRow}>
                <Feather name="filter" size={20} color="#2563eb" />
                <Text style={styles.filterTitle}>Filter Products</Text>
                {getActiveFiltersCount() > 0 && (
                  <View style={styles.activeBadge}>
                    <Text style={styles.activeBadgeText}>{getActiveFiltersCount()} active</Text>
                  </View>
                )}
              </View>
              <TouchableOpacity
                style={styles.toggleButton}
                onPress={() => setIsFilterExpanded(!isFilterExpanded)}
              >
                <Feather
                  name={isFilterExpanded ? "chevron-up" : "chevron-down"}
                  size={16}
                  color="#374151"
                />
                <Text style={styles.toggleButtonText}>
                  {isFilterExpanded ? 'Hide Filters' : 'Show Filters'}
                </Text>
              </TouchableOpacity>
            </View>

            {!isFilterExpanded && (
              <View style={styles.filterSummary}>
                <Text style={styles.filterSummaryText}>
                  {getActiveFiltersCount() > 0
                    ? `${getActiveFiltersCount()} filter${getActiveFiltersCount() > 1 ? 's' : ''} applied - Click "Show Filters" to modify`
                    : "Use filters to find the products you're looking for"}
                </Text>
                {getActiveFiltersCount() > 0 && (
                  <TouchableOpacity onPress={clearAllFilters}>
                    <Text style={styles.clearAllLink}>Clear All</Text>
                  </TouchableOpacity>
                )}
              </View>
            )}
          </View>

          {/* Collapsible Filter Content */}
          {isFilterExpanded && (
            <View style={styles.filterContent}>
              <Text style={styles.filterHint}>
                Use the colorful filters below to find the products you're looking for
              </Text>

              {/* Filter Grid */}
              <View style={styles.filterGrid}>
                {/* Category Filter - Red */}
                <View style={styles.filterItem}>
                  <View style={styles.filterLabelRow}>
                    <Feather name="target" size={12} color="#dc2626" />
                    <Text style={styles.filterLabel}>Category</Text>
                  </View>
                  <CustomDropdown
                    options={filterOptions.main_categories.map(cat => ({ label: cat, value: cat }))}
                    selectedValue={tempCategory}
                    onValueChange={(value) => {
                      setTempCategory(value);
                      setTempSubcategory('');
                      setTempPlatform('');
                    }}
                    placeholder="All Categories"
                    style={styles.pickerContainer}
                    borderColor="#fecaca"
                  />
                </View>

                {/* Subcategory Filter - Green */}
                {tempCategory && (
                  <View style={styles.filterItem}>
                    <View style={styles.filterLabelRow}>
                      <Feather name="search" size={12} color="#16a34a" />
                      <Text style={styles.filterLabel}>Subcategory</Text>
                    </View>
                    <CustomDropdown
                      options={filterOptions.subcategories
                        .map(sub => ({ label: sub, value: sub }))}
                      selectedValue={tempSubcategory}
                      onValueChange={(value) => {
                        setTempSubcategory(value);
                        setTempPlatform('');
                      }}
                      placeholder={`All ${tempCategory || 'Subcategories'}`}
                      style={styles.pickerContainer}
                      borderColor="#bbf7d0"
                    />
                  </View>
                )}

                {/* Platform Filter - Orange */}
                <View style={styles.filterItem}>
                  <View style={styles.filterLabelRow}>
                    <Feather name="globe" size={12} color="#ea580c" />
                    <Text style={styles.filterLabel}>Platform</Text>
                  </View>
                  <CustomDropdown
                    options={filterOptions.platforms.map(platform => ({ label: platform, value: platform }))}
                    selectedValue={tempPlatform}
                    onValueChange={setTempPlatform}
                    placeholder="All Platforms"
                    style={styles.pickerContainer}
                    borderColor="#fed7aa"
                  />
                </View>

                {/* Brand Filter - Purple */}
                <View style={styles.filterItem}>
                  <View style={styles.filterLabelRow}>
                    <Feather name="star" size={12} color="#9333ea" />
                    <Text style={styles.filterLabel}>Brand</Text>
                  </View>
                  <CustomDropdown
                    options={filterOptions.brands.map(brand => ({ label: brand, value: brand }))}
                    selectedValue={tempBrand}
                    onValueChange={setTempBrand}
                    placeholder="All Brands"
                    style={styles.pickerContainer}
                    borderColor="#e9d5ff"
                  />
                </View>
              </View>

              {/* Price Range Filter - Green */}
              <View style={styles.priceFilterContainer}>
                <View style={styles.filterLabelRow}>
                  <Feather name="dollar-sign" size={12} color="#16a34a" />
                  <Text style={styles.filterLabel}>Price Range (PKR)</Text>
                </View>
                <View style={styles.priceInputsRow}>
                  <View style={styles.priceInputContainer}>
                    <Text style={styles.priceInputLabel}>Minimum Price</Text>
                    <TextInput
                      style={[styles.priceInput, styles.priceInputGreen]}
                      placeholder="Min (e.g., 1000)"
                      value={tempMinPrice}
                      onChangeText={setTempMinPrice}
                      keyboardType="numeric"
                      placeholderTextColor="#9ca3af"
                    />
                  </View>
                  <View style={styles.priceInputContainer}>
                    <Text style={styles.priceInputLabel}>Maximum Price</Text>
                    <TextInput
                      style={[styles.priceInput, styles.priceInputGreen]}
                      placeholder="Max (e.g., 100000)"
                      value={tempMaxPrice}
                      onChangeText={setTempMaxPrice}
                      keyboardType="numeric"
                      placeholderTextColor="#9ca3af"
                    />
                  </View>
                </View>
                {(tempMinPrice || tempMaxPrice) && (
                  <Text style={styles.priceRangeText}>
                    Showing products {tempMinPrice && `from ₨${parseInt(tempMinPrice || 0).toLocaleString()}`}
                    {tempMinPrice && tempMaxPrice && ' '}
                    {tempMaxPrice && `to ₨${parseInt(tempMaxPrice || 0).toLocaleString()}`}
                  </Text>
                )}
              </View>

              {/* Sort By Filter - Blue */}
              <View style={styles.sortFilterContainer}>
                <View style={styles.filterLabelRow}>
                  <Feather name="arrow-up" size={12} color="#2563eb" />
                  <Text style={styles.filterLabel}>Sort By</Text>
                </View>
                <CustomDropdown
                  options={sortOptions}
                  selectedValue={tempSortBy}
                  onValueChange={setTempSortBy}
                  placeholder="Newest First"
                  style={styles.pickerContainer}
                  borderColor="#bfdbfe"
                />
              </View>

              {/* Apply Filters Button */}
              <TouchableOpacity
                style={styles.applyButton}
                onPress={applyFilters}
              >
                <LinearGradient
                  colors={['#2563eb', '#1d4ed8']}
                  style={styles.applyButtonGradient}
                >
                  <Feather name="target" size={16} color="#ffffff" />
                  <Text style={styles.applyButtonText}>Apply Filters</Text>
                </LinearGradient>
              </TouchableOpacity>
            </View>
          )}
        </LinearGradient>

        {/* Products Grid */}
        <View style={styles.productsSection}>
          <FlatList
            data={filteredProducts}
            renderItem={renderProductItem}
            keyExtractor={(item) => item.id.toString()}
            numColumns={2}
            scrollEnabled={false}
            contentContainerStyle={styles.productsList}
            columnWrapperStyle={styles.row}
            ListEmptyComponent={
              <View style={styles.emptyContainer}>
                <Text style={styles.emptyText}>No products found</Text>
                <Text style={styles.emptySubtext}>Try adjusting your filters</Text>
              </View>
            }
            onEndReached={handleLoadMore}
            onEndReachedThreshold={0.5}
            ListFooterComponent={
              loadingMore ? (
                <View style={styles.footerLoader}>
                  <ActivityIndicator size="small" color="#2563eb" />
                </View>
              ) : null
            }
          />
        </View>
      </ScrollView>
    </SafeAreaView>
  );
};

export default ProductsScreen;

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
    color: '#4b5563',
  },
  headerSection: {
    backgroundColor: '#ffffff',
    paddingHorizontal: 16,
    paddingVertical: 12,
    borderBottomWidth: 1,
    borderBottomColor: '#e5e7eb',
  },
  headerRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  headerTitle: {
    fontSize: 20,
    fontWeight: 'bold',
    color: '#1f2937',
  },
  placeholder: {
    width: 24,
  },
  titleSection: {
    alignItems: 'center',
    paddingVertical: 24,
    paddingHorizontal: 16,
  },
  mainTitle: {
    fontSize: 36,
    fontWeight: 'bold',
    color: '#2563eb',
    marginBottom: 8,
  },
  subtitle: {
    fontSize: 18,
    color: '#4b5563',
  },
  breadcrumbContainer: {
    backgroundColor: '#f9fafb',
    marginHorizontal: 16,
    marginBottom: 16,
    padding: 16,
    borderRadius: 12,
    borderWidth: 1,
    borderColor: '#e5e7eb',
  },
  breadcrumbRow: {
    flexDirection: 'row',
    alignItems: 'center',
    flexWrap: 'wrap',
  },
  breadcrumbLabel: {
    fontSize: 14,
    color: '#374151',
    marginRight: 8,
  },
  breadcrumbBadge: {
    backgroundColor: '#dbeafe',
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 16,
    marginRight: 8,
  },
  breadcrumbBadgeGreen: {
    backgroundColor: '#d1fae5',
  },
  breadcrumbBadgeText: {
    fontSize: 12,
    color: '#1e40af',
    fontWeight: '600',
  },
  breadcrumbBadgeTextGreen: {
    color: '#065f46',
  },
  breadcrumbArrow: {
    fontSize: 16,
    color: '#9ca3af',
    marginHorizontal: 8,
  },
  clearFiltersBtn: {
    flexDirection: 'row',
    alignItems: 'center',
    marginLeft: 'auto',
    paddingHorizontal: 12,
    paddingVertical: 6,
  },
  clearFiltersText: {
    fontSize: 12,
    color: '#dc2626',
    marginLeft: 4,
    fontWeight: '600',
  },
  filterContainer: {
    marginHorizontal: 16,
    marginBottom: 24,
    borderRadius: 12,
    borderWidth: 1,
    borderColor: '#bfdbfe',
    elevation: 4,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 8,
  },
  filterHeader: {
    padding: 24,
    paddingBottom: 16,
  },
  filterHeaderRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 8,
  },
  filterTitleRow: {
    flexDirection: 'row',
    alignItems: 'center',
    flex: 1,
  },
  filterTitle: {
    fontSize: 20,
    fontWeight: 'bold',
    color: '#1f2937',
    marginLeft: 12,
  },
  activeBadge: {
    backgroundColor: '#dbeafe',
    paddingHorizontal: 10,
    paddingVertical: 4,
    borderRadius: 12,
    marginLeft: 12,
  },
  activeBadgeText: {
    fontSize: 12,
    color: '#1e40af',
    fontWeight: '600',
  },
  toggleButton: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#ffffff',
    paddingHorizontal: 16,
    paddingVertical: 8,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: '#e5e7eb',
  },
  toggleButtonText: {
    fontSize: 14,
    color: '#374151',
    marginLeft: 8,
    fontWeight: '500',
  },
  filterSummary: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  filterSummaryText: {
    fontSize: 14,
    color: '#4b5563',
    flex: 1,
  },
  clearAllLink: {
    fontSize: 12,
    color: '#dc2626',
    textDecorationLine: 'underline',
    fontWeight: '600',
  },
  filterContent: {
    paddingHorizontal: 24,
    paddingBottom: 24,
  },
  filterHint: {
    fontSize: 14,
    color: '#4b5563',
    marginBottom: 16,
  },
  filterGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    marginBottom: 16,
  },
  filterItem: {
    width: '48%',
    marginRight: '2%',
    marginBottom: 16,
  },
  filterLabelRow: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 8,
  },
  filterLabel: {
    fontSize: 12,
    fontWeight: '600',
    color: '#374151',
    marginLeft: 8,
  },
  pickerContainer: {
    borderWidth: 2,
    borderRadius: 8,
    backgroundColor: '#ffffff',
    height: 40,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: 12,
  },
  dropdownButton: {
    borderWidth: 2,
    borderRadius: 8,
    backgroundColor: '#ffffff',
    height: 40,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: 12,
  },
  dropdownText: {
    fontSize: 14,
    color: '#1f2937',
    flex: 1,
  },
  footerLoader: {
    paddingVertical: 20,
    alignItems: 'center',
    justifyContent: 'center',
    width: '100%',
  },
  dropdownOverlay: {
    flex: 1,
    backgroundColor: 'rgba(0, 0, 0, 0.5)',
    justifyContent: 'center',
    alignItems: 'center',
  },
  dropdownModal: {
    backgroundColor: '#ffffff',
    borderRadius: 12,
    width: '80%',
    maxHeight: '60%',
    elevation: 8,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.3,
    shadowRadius: 8,
  },
  dropdownList: {
    maxHeight: 300,
  },
  dropdownItem: {
    paddingVertical: 12,
    paddingHorizontal: 16,
    borderBottomWidth: 1,
    borderBottomColor: '#f3f4f6',
  },
  dropdownItemText: {
    fontSize: 14,
    color: '#1f2937',
  },
  dropdownItemTextSelected: {
    color: '#2563eb',
    fontWeight: '600',
  },
  priceFilterContainer: {
    marginBottom: 16,
  },
  priceInputsRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginTop: 8,
  },
  priceInputContainer: {
    width: '48%',
  },
  priceInputLabel: {
    fontSize: 12,
    color: '#4b5563',
    marginBottom: 4,
  },
  priceInput: {
    borderWidth: 2,
    borderRadius: 8,
    paddingHorizontal: 12,
    paddingVertical: 10,
    fontSize: 14,
    color: '#1f2937',
    backgroundColor: '#ffffff',
  },
  priceInputGreen: {
    borderColor: '#bbf7d0',
  },
  priceRangeText: {
    fontSize: 12,
    color: '#4b5563',
    marginTop: 8,
  },
  sortFilterContainer: {
    marginBottom: 24,
  },
  applyButton: {
    borderRadius: 8,
    overflow: 'hidden',
    elevation: 4,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.2,
    shadowRadius: 4,
  },
  applyButtonGradient: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    paddingVertical: 12,
    paddingHorizontal: 32,
  },
  applyButtonText: {
    fontSize: 16,
    fontWeight: '600',
    color: '#ffffff',
    marginLeft: 8,
  },
  productsSection: {
    paddingHorizontal: 8,
  },
  productsList: {
    paddingBottom: 24,
  },
  row: {
    justifyContent: 'space-between',
    paddingHorizontal: 4,
  },
  productCard: {
    flex: 1,
    backgroundColor: '#ffffff',
    borderRadius: 12,
    margin: 4,
    overflow: 'hidden',
    elevation: 2,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
  },
  productImage: {
    width: '100%',
    height: 180,
    backgroundColor: '#f3f4f6',
  },
  productInfo: {
    padding: 12,
  },
  productName: {
    fontSize: 14,
    fontWeight: '600',
    color: '#1f2937',
    marginBottom: 8,
    minHeight: 36,
  },
  priceContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 8,
  },
  price: {
    fontSize: 16,
    fontWeight: 'bold',
    color: '#2563eb',
    marginRight: 8,
  },
  originalPrice: {
    fontSize: 12,
    color: '#9ca3af',
    textDecorationLine: 'line-through',
  },
  badgeContainer: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    marginBottom: 8,
  },
  platformBadge: {
    backgroundColor: '#dbeafe',
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 12,
    marginRight: 6,
    marginBottom: 4,
  },
  brandBadge: {
    backgroundColor: '#f3f4f6',
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 12,
    marginBottom: 4,
  },
  badgeText: {
    fontSize: 10,
    color: '#1f2937',
    fontWeight: '600',
  },
  viewButton: {
    backgroundColor: '#2563eb',
    paddingVertical: 8,
    borderRadius: 6,
    alignItems: 'center',
    marginTop: 4,
  },
  viewButtonText: {
    color: '#ffffff',
    fontSize: 14,
    fontWeight: 'bold',
  },
  emptyContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    paddingVertical: 60,
  },
  emptyText: {
    fontSize: 18,
    fontWeight: 'bold',
    color: '#4b5563',
    marginBottom: 8,
  },
  emptySubtext: {
    fontSize: 14,
    color: '#9ca3af',
  },
});
