import { ChatButton } from '@/components/chatbot/ChatButton';
import { FilterBar } from '@/components/marketplace/FilterBar';
import { MarketplaceFooter } from '@/components/marketplace/MarketplaceFooter';
import { MarketplaceHero } from '@/components/marketplace/MarketplaceHero';
import { SERVICES } from '@/components/marketplace/mockData';
import { ServiceCard } from '@/components/marketplace/ServiceCard';
import React, { useMemo, useState } from 'react';
import { Platform, SafeAreaView, ScrollView, StyleSheet, Text, useWindowDimensions, View } from 'react-native';

export default function HomeScreen() {
  const { width } = useWindowDimensions();
  const [searchQuery, setSearchQuery] = useState('');
  const [sortType, setSortType] = useState<'price_asc' | 'price_desc' | null>(null);

  // Responsive Grid Calculation
  const getGridSettings = () => {
    // Breakpoints
    if (width >= 1024) return { numColumns: 4, padding: 80 }; // Desktop
    if (width >= 768) return { numColumns: 3, padding: 32 };  // Tablet
    return { numColumns: 2, padding: 16 };                    // Mobile
  };

  const { numColumns, padding } = getGridSettings();
  const gap = 20; // Increased gap for better look

  // Calculate card width
  const availableWidth = width - (padding * 2) - (gap * (numColumns - 1));
  const cardWidth = Math.max(0, availableWidth / numColumns);

  // Filter and Sort Data
  const filteredServices = useMemo(() => {
    let result = [...SERVICES];

    // Filter by search query
    if (searchQuery) {
      const query = searchQuery.toLowerCase();
      result = result.filter(item =>
        item.title.toLowerCase().includes(query) ||
        (item.details && item.details.toLowerCase().includes(query))
      );
    }

    // Sort by price
    if (sortType) {
      result.sort((a, b) => {
        // Parse "Rs 3300" -> 3300
        const priceA = parseInt(a.price.replace(/[^0-9]/g, ''), 10) || 0;
        const priceB = parseInt(b.price.replace(/[^0-9]/g, ''), 10) || 0;

        return sortType === 'price_asc' ? priceA - priceB : priceB - priceA;
      });
    }

    return result;
  }, [searchQuery, sortType]);

  return (
    <SafeAreaView style={styles.safeArea}>
      <ScrollView contentContainerStyle={styles.scrollContent} showsVerticalScrollIndicator={false}>

        {/* Marketplace Container */}
        <View style={[styles.container, { paddingHorizontal: padding }]}>
          <MarketplaceHero />

          <FilterBar
            onSearch={setSearchQuery}
            onSortChange={setSortType}
          />

          {filteredServices.length === 0 ? (
            <View style={styles.emptyState}>
              <Text style={styles.emptyText}>No services found matching "{searchQuery}"</Text>
            </View>
          ) : (
            <View style={[styles.grid, { gap }]}>
              {filteredServices.map((item) => (
                <View key={item.id} style={{ width: cardWidth }}>
                  <ServiceCard item={item} />
                </View>
              ))}
            </View>
          )}
        </View>

        <MarketplaceFooter />
      </ScrollView>
      <ChatButton />
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safeArea: {
    flex: 1,
    backgroundColor: '#fff',
    paddingTop: Platform.OS === 'android' ? 30 : 0,
  },
  scrollContent: {
    flexGrow: 1,
    backgroundColor: '#fff',
  },
  container: {
    paddingVertical: 24,
    maxWidth: 1600,
    alignSelf: 'center',
    width: '100%',
  },
  grid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
  },
  emptyState: {
    padding: 40,
    alignItems: 'center',
    justifyContent: 'center',
  },
  emptyText: {
    fontSize: 16,
    color: '#6b7280',
  }
});
