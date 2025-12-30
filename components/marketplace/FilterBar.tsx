import { Ionicons } from '@expo/vector-icons';
import React, { useState } from 'react';
import { Modal, Pressable, StyleSheet, Text, TextInput, TouchableOpacity, View } from 'react-native';

interface FilterBarProps {
    onSearch: (text: string) => void;
    onSortChange: (sortType: 'price_asc' | 'price_desc' | null) => void;
}

export function FilterBar({ onSearch, onSortChange }: FilterBarProps) {
    const [searchQuery, setSearchQuery] = useState('');
    const [sortType, setSortType] = useState<'price_asc' | 'price_desc' | null>(null);
    const [modalVisible, setModalVisible] = useState(false);

    const handleSearch = (text: string) => {
        setSearchQuery(text);
        onSearch(text);
    };

    const handleSort = (type: 'price_asc' | 'price_desc' | null) => {
        setSortType(type);
        onSortChange(type);
        setModalVisible(false);
    };

    const getSortLabel = () => {
        if (sortType === 'price_asc') return 'Price: Low to High';
        if (sortType === 'price_desc') return 'Price: High to Low';
        return 'Sort by';
    };

    return (
        <View style={styles.container}>
            <TouchableOpacity style={styles.filterButton}>
                <Text style={styles.filterButtonText}>All Services</Text>
            </TouchableOpacity>

            <View style={styles.searchContainer}>
                <Ionicons name="search" size={18} color="#9ca3af" />
                <TextInput
                    placeholder="Search products..."
                    style={styles.input}
                    placeholderTextColor="#9ca3af"
                    value={searchQuery}
                    onChangeText={handleSearch}
                />
                {searchQuery.length > 0 && (
                    <TouchableOpacity onPress={() => handleSearch('')}>
                        <Ionicons name="close-circle" size={16} color="#9ca3af" />
                    </TouchableOpacity>
                )}
            </View>

            <TouchableOpacity
                style={[styles.sortButton, sortType && styles.activeSort]}
                onPress={() => setModalVisible(true)}
            >
                <Text style={[styles.sortText, sortType && styles.activeSortText]}>
                    {getSortLabel()}
                </Text>
                <Ionicons
                    name="chevron-down"
                    size={16}
                    color={sortType ? '#6366f1' : "#4b5563"}
                />
            </TouchableOpacity>

            {/* Simple Sort Modal */}
            <Modal
                animationType="fade"
                transparent={true}
                visible={modalVisible}
                onRequestClose={() => setModalVisible(false)}
            >
                <Pressable style={styles.modalOverlay} onPress={() => setModalVisible(false)}>
                    <View style={styles.modalContent}>
                        <Text style={styles.modalTitle}>Sort By</Text>

                        <TouchableOpacity style={styles.modalOption} onPress={() => handleSort(null)}>
                            <Text style={[styles.modalOptionText, !sortType && styles.selectedOption]}>Default</Text>
                            {!sortType && <Ionicons name="checkmark" size={16} color="#6366f1" />}
                        </TouchableOpacity>

                        <TouchableOpacity style={styles.modalOption} onPress={() => handleSort('price_asc')}>
                            <Text style={[styles.modalOptionText, sortType === 'price_asc' && styles.selectedOption]}>Price: Low to High</Text>
                            {sortType === 'price_asc' && <Ionicons name="checkmark" size={16} color="#6366f1" />}
                        </TouchableOpacity>

                        <TouchableOpacity style={styles.modalOption} onPress={() => handleSort('price_desc')}>
                            <Text style={[styles.modalOptionText, sortType === 'price_desc' && styles.selectedOption]}>Price: High to Low</Text>
                            {sortType === 'price_desc' && <Ionicons name="checkmark" size={16} color="#6366f1" />}
                        </TouchableOpacity>
                    </View>
                </Pressable>
            </Modal>
        </View>
    );
}

const styles = StyleSheet.create({
    container: {
        flexDirection: 'row',
        alignItems: 'center',
        marginBottom: 24,
        gap: 12,
        zIndex: 5, // Ensure dropdown/modal handling works well if adjusted
    },
    filterButton: {
        backgroundColor: '#6366f1', // Indigo 500
        paddingVertical: 10,
        paddingHorizontal: 16,
        borderRadius: 8,
    },
    filterButtonText: {
        color: 'white',
        fontWeight: '600',
        fontSize: 14,
    },
    searchContainer: {
        flex: 1,
        flexDirection: 'row',
        alignItems: 'center',
        backgroundColor: 'white',
        borderRadius: 8,
        paddingHorizontal: 12,
        height: 40,
        borderWidth: 1,
        borderColor: '#e5e7eb',
    },
    input: {
        flex: 1,
        marginLeft: 8,
        fontSize: 14,
        outlineStyle: 'none', // Web specific
    } as any, // Cast to any to avoid TS error for outlineStyle on native
    sortButton: {
        flexDirection: 'row',
        alignItems: 'center',
        gap: 4,
        backgroundColor: 'white',
        paddingVertical: 10,
        paddingHorizontal: 12,
        borderRadius: 8,
        borderWidth: 1,
        borderColor: '#e5e7eb',
        minWidth: 100,
        justifyContent: 'space-between'
    },
    activeSort: {
        borderColor: '#6366f1',
        backgroundColor: '#e0e7ff',
    },
    sortText: {
        color: '#4b5563',
        fontSize: 14,
        fontWeight: '500',
    },
    activeSortText: {
        color: '#6366f1',
    },
    modalOverlay: {
        flex: 1,
        backgroundColor: 'rgba(0,0,0,0.2)',
        justifyContent: 'center',
        alignItems: 'center',
    },
    modalContent: {
        backgroundColor: 'white',
        borderRadius: 12,
        padding: 16,
        width: 250,
        shadowColor: '#000',
        shadowOffset: {
            width: 0,
            height: 2,
        },
        shadowOpacity: 0.25,
        shadowRadius: 3.84,
        elevation: 5,
    },
    modalTitle: {
        fontSize: 16,
        fontWeight: 'bold',
        marginBottom: 12,
        color: '#111827',
    },
    modalOption: {
        paddingVertical: 12,
        flexDirection: 'row',
        justifyContent: 'space-between',
        alignItems: 'center',
        borderBottomWidth: 1,
        borderBottomColor: '#f3f4f6',
    },
    modalOptionText: {
        fontSize: 14,
        color: '#4b5563',
    },
    selectedOption: {
        color: '#6366f1',
        fontWeight: '600',
    }
});
