import { StyleSheet, Text, View, ScrollView, TouchableOpacity, FlatList } from 'react-native'
import React, { useState, useMemo } from 'react'
import { SafeAreaView } from 'react-native-safe-area-context'
import Header from '../components/Header'
import SubHeader from '../components/SubHeader'
import Category from '../components/Category'
import TopRatedSection from '../components/TopRatedSection'
import WhatsNewsection from '../components/WhatsNewsection'
import FloatingChat from '../components/FloatingChat';
import { MarketplaceHero } from './Services/components/marketplace/MarketplaceHero';
import { FilterBar } from './Services/components/marketplace/FilterBar';

import { ServiceCard } from './Services/components/marketplace/ServiceCard';
import { SERVICES } from './Services/components/marketplace/mockData';

const HomeScreen = () => {
  const [activeTab, setActiveTab] = useState('Products');
  const [searchQuery, setSearchQuery] = useState('');
  const [sortType, setSortType] = useState(null);

  const filteredServices = useMemo(() => {
    let result = [...SERVICES];

    if (searchQuery) {
      const lowerQ = searchQuery.toLowerCase();
      result = result.filter(item =>
        item.title.toLowerCase().includes(lowerQ) ||
        (item.details && item.details.toLowerCase().includes(lowerQ))
      );
    }

    if (sortType) {
      result.sort((a, b) => {
        // Extract price number: "Rs  3300" -> 3300
        const priceA = parseInt(a.price.replace(/[^0-9]/g, '')) || 0;
        const priceB = parseInt(b.price.replace(/[^0-9]/g, '')) || 0;
        return sortType === 'price_asc' ? priceA - priceB : priceB - priceA;
      });
    }

    return result;
  }, [searchQuery, sortType]);

  const renderTabSwitcher = () => (
    <View style={styles.tabContainer}>
      <TouchableOpacity
        onPress={() => setActiveTab('Products')}
        style={[styles.tabButton, activeTab === 'Products' && styles.activeTab]}
      >
        <Text style={[styles.tabText, activeTab === 'Products' && styles.activeTabText]}>Products</Text>
      </TouchableOpacity>
      <TouchableOpacity
        onPress={() => setActiveTab('Services')}
        style={[styles.tabButton, activeTab === 'Services' && styles.activeTab]}
      >
        <Text style={[styles.tabText, activeTab === 'Services' && styles.activeTabText]}>Services</Text>
      </TouchableOpacity>
    </View>
  );

  const renderServiceItem = ({ item }) => (
    <View style={styles.cardWrapper}>
      <ServiceCard item={item} />
    </View>
  );

  const renderServicesHeader = () => (
    <View>
      <Header />
      {renderTabSwitcher()}
      <View style={styles.servicesHeaderContent}>
        <MarketplaceHero />
        <FilterBar onSearch={setSearchQuery} onSortChange={setSortType} />
      </View>
    </View>
  );

  const renderServicesEmpty = () => (
    <View style={styles.noResults}>
      <Text style={styles.noResultsText}>No services found matching your criteria.</Text>
    </View>
  );

  return (
    <SafeAreaView style={{ flex: 1 }} edges={['top']}>
      <View style={{ flex: 1 }}>
        {activeTab === 'Products' ? (
          <ScrollView showsVerticalScrollIndicator={false}>
            <Header />
            {renderTabSwitcher()}
            <SubHeader />
            <Category />
            <TopRatedSection />
            <WhatsNewsection />
          </ScrollView>
        ) : (
          <FlatList
            data={filteredServices}
            keyExtractor={(item) => item.id}
            renderItem={renderServiceItem}
            numColumns={2}
            columnWrapperStyle={styles.serviceGrid}
            contentContainerStyle={styles.flatListContent}
            ListHeaderComponent={renderServicesHeader}

            ListEmptyComponent={renderServicesEmpty}
            showsVerticalScrollIndicator={false}
            initialNumToRender={6}
            maxToRenderPerBatch={6}
            windowSize={5}
            removeClippedSubviews={true}
          />
        )}
        <FloatingChat />
      </View>
    </SafeAreaView>
  )
}

export default HomeScreen

const styles = StyleSheet.create({
  tabContainer: {
    flexDirection: 'row',
    justifyContent: 'center',
    marginVertical: 15,
    marginHorizontal: 20,
    backgroundColor: '#f3f4f6',
    borderRadius: 25,
    padding: 4,
  },
  tabButton: {
    flex: 1,
    paddingVertical: 10,
    alignItems: 'center',
    borderRadius: 20,
  },
  activeTab: {
    backgroundColor: '#ffffff',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.1,
    shadowRadius: 2,
    elevation: 2,
  },
  tabText: {
    fontSize: 16,
    fontWeight: '600',
    color: '#6b7280',
  },
  activeTabText: {
    color: '#2563eb',
  },
  flatListContent: {
    paddingBottom: 20,
  },
  servicesHeaderContent: {
    paddingHorizontal: 16,
  },
  serviceGrid: {
    justifyContent: 'space-between',
    paddingHorizontal: 16,
  },
  cardWrapper: {
    width: '48%', // Approx half width
    marginBottom: 16,
  },
  noResults: {
    padding: 32,
    alignItems: 'center',
    width: '100%',
  },
  noResultsText: {
    color: '#6b7280',
    fontSize: 14,
    fontStyle: 'italic',
  }
})