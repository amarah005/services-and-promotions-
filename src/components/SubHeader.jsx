import React, { useState } from 'react';
import { StyleSheet, Text, TextInput, View, TouchableOpacity, Dimensions } from 'react-native';
import LinearGradient from 'react-native-linear-gradient';
import Feather from 'react-native-vector-icons/Feather';
import { useNavigation } from '@react-navigation/native';

const { width, height } = Dimensions.get('window');

const GradientText = ({ children, style }) => {
  return (
    <Text style={[styles.gradientText, style]}>{children}</Text>
  );
};

const HeroSection = () => {
  const navigation = useNavigation();
  const [searchQuery, setSearchQuery] = useState('');

  const handleSearch = () => {
    if (searchQuery.trim()) {
      navigation.navigate('Search', { query: searchQuery.trim() });
    } else {
      navigation.navigate('Search');
    }
  };

  return (
    <LinearGradient
      colors={['#32047D', '#2419F7', '#200f90']}
      style={styles.container}
    >
      {/* Main Content */}
      <View style={styles.content}>
        {/* Title with Two Color Styles */}
        <View style={styles.titleContainer}>
          <Text style={styles.titleWhite}>
            Find, Compare & Buy
          </Text>
          <GradientText style={styles.titleGradient}>
            Everything In One Place!
          </GradientText>
        </View>

        <Text style={styles.subtitle}>
          Pakistan's first centralized platform that aggregates products from various online sources. Compare prices, read reviews, and make informed decisions effortlessly.
        </Text>

        {/* Search Input */}
        <TouchableOpacity 
          style={styles.searchContainer}
          onPress={handleSearch}
          activeOpacity={0.9}
        >
          <View style={styles.searchRow}>
            <TextInput
              placeholder="Search for products, brands, categories.."
              placeholderTextColor="#9CA3AF"
              value={searchQuery}
              onChangeText={setSearchQuery}
              onSubmitEditing={handleSearch}
              returnKeyType="search"
              style={styles.textInput}
              editable={true}
            />
            <TouchableOpacity onPress={handleSearch}>
              <Feather name="search" size={20} color="#6B7280" />
            </TouchableOpacity>
          </View>
        </TouchableOpacity>

        {/* Two Buttons in One Row */}
        <View style={styles.buttonContainer}>
          <LinearGradient
            colors={['#4F46E5', '#7C3AED']}
            style={styles.primaryButton}
            start={{ x: 0, y: 0 }}
            end={{ x: 1, y: 0 }}
          >
            <TouchableOpacity
              onPress={() => navigation.navigate('Products')}
              style={styles.buttonTouchable}
            >
              <Text style={styles.primaryButtonText}>Start Shopping</Text>
            </TouchableOpacity>
          </LinearGradient>
          
          <TouchableOpacity
            onPress={() => navigation.navigate('Products')}
            style={styles.secondaryButton}
          >
            <Text style={styles.secondaryButtonText}>Browse Categories</Text>
          </TouchableOpacity>
        </View>
      </View>
    </LinearGradient>
  );
};

export default HeroSection;

const styles = StyleSheet.create({
  container: {
    flexDirection: 'row',
    paddingVertical: height * 0.01, 
    paddingHorizontal: 20,
    minHeight: height * 0.48, 
    maxHeight: height * 0.6, 
  },
  content: {
    flex: 1, 
    justifyContent: 'center',
    paddingRight: 10,
  },
  titleContainer: {
    marginBottom: 18,
  },
  titleWhite: {
    fontSize: width < 380 ? 22 : 26,
    fontWeight: 'bold',
    color: '#FFFFFF',
    textAlign: 'left',
    lineHeight: 32,
  },
  titleGradient: {
    fontSize: width < 380 ? 22 : 26,
    fontWeight: 'bold',
    textAlign: 'left',
    lineHeight: 32,
  },
  gradientText: {
    fontSize: width < 380 ? 22 : 26,
    fontWeight: 'bold',
    textAlign: 'left',
    color: '#C084FC', // Solid purple color
    lineHeight: 32,
  },
  subtitle: {
    color: '#E5E7EB',
    fontSize: width < 380 ? 13 : 15,
    textAlign: 'left',
    marginBottom: 25,
    lineHeight: 20,
    maxWidth: '100%',
  },
  searchContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    borderWidth: 2,
    borderColor: '#000000',
    borderRadius: 10,
    backgroundColor: '#FFFFFF',
    width: '100%',
    maxWidth: 500, // Reduced width
    marginBottom: 20,
    elevation: 4,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 8,
    height: 60,
  },
  searchRow: {
    flexDirection: 'row',
    alignItems: 'center',
    flex: 1,
    paddingHorizontal: 12,
    paddingVertical: 10,
  },
  textInput: {
    flex: 1,
    paddingHorizontal: 10,
    fontSize: 14, 
    color: '#1F2937',
  },
  buttonContainer: {
    flexDirection: 'row',
    gap: 12,
    alignItems: 'center',
  },
  primaryButton: {
    borderRadius: 8,
    elevation: 3,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.1,
    shadowRadius: 3,
    minWidth: 120,
    flex: 1,
  },
  buttonTouchable: {
    paddingVertical: 12,
    paddingHorizontal: 16,
    alignItems: 'center',
  },
  primaryButtonText: {
    color: '#FFFFFF',
    fontWeight: '600',
    fontSize: 14,
  },
  secondaryButton: {
    backgroundColor: 'transparent',
    paddingVertical: 12,
    paddingHorizontal: 8,
    borderRadius: 8,
    borderWidth: 1.5,
    borderColor: '#FFFFFF',
    minWidth: 130,
    flex: 1,
    alignItems: 'center',
  },
  secondaryButtonText: {
    color: '#FFFFFF',
    fontWeight: '600',
    fontSize: 14,
  },
  
});