import Ionicons from 'react-native-vector-icons/Ionicons';
import { Image, Linking, Pressable, StyleSheet, Text, View } from 'react-native';
import React, { useMemo } from 'react';
import { SERVICES } from './mockData';

export function MarketplaceHero() {
    // Get a random service for the full banner
    const randomService = useMemo(() => {
        const randomIndex = Math.floor(Math.random() * SERVICES.length);
        return SERVICES[randomIndex];
    }, []);

    const handlePress = () => {
        if (randomService.link) {
            Linking.openURL(randomService.link).catch(err => console.error("Couldn't load page", err));
        }
    };

    return (
        <Pressable onPress={handlePress} style={styles.container}>
            <Image
                source={randomService.image}
                style={styles.backgroundImage}
                resizeMode="cover"
            />

            {/* Dark Overlay for text readability */}
            <View style={styles.overlay} />

            <View style={styles.content}>
                <View style={styles.topRow}>
                    <View style={styles.brandContainer}>
                        <Ionicons name="pricetag" size={20} color="#fff" />
                        <Text style={styles.brandTitle}>Featured Service</Text>
                    </View>
                </View>

                <View style={styles.centerContent}>
                    <Text style={styles.heroTitle} numberOfLines={2}>
                        {randomService.title}
                    </Text>

                    <View style={styles.priceTag}>
                        <Text style={styles.priceText}>{randomService.price}</Text>
                    </View>

                    {randomService.details && (
                        <Text style={styles.heroSubtitle} numberOfLines={2}>
                            {randomService.details}
                        </Text>
                    )}
                </View>

                <View style={styles.bottomRow}>
                    <View style={styles.actionButton}>
                        <Text style={styles.actionText}>View Details</Text>
                        <Ionicons name="arrow-forward" size={16} color="white" />
                    </View>
                </View>
            </View>
        </Pressable>
    );
}

const styles = StyleSheet.create({
    container: {
        height: 320, // Taller banner
        width: '100%',
        position: 'relative',
        overflow: 'hidden',
        borderRadius: 16, // Rounded corners for modern app look
        marginBottom: 32,
        borderRadius: 16,
        overflow: 'hidden', // Ensures image stays within rounded corners
        backgroundColor: '#1e293b',
    },
    backgroundImage: {
        ...StyleSheet.absoluteFillObject,
        width: '100%',
        height: '100%',
    },
    overlay: {
        ...StyleSheet.absoluteFillObject,
        backgroundColor: 'rgba(0,0,0,0.5)', // 50% dark overlay
    },
    content: {
        flex: 1,
        padding: 24,
        justifyContent: 'space-between',
    },
    topRow: {
        flexDirection: 'row',
        justifyContent: 'space-between',
        alignItems: 'flex-start',
    },
    brandContainer: {
        flexDirection: 'row',
        alignItems: 'center',
        gap: 8,
        backgroundColor: 'rgba(255,255,255,0.2)',
        paddingHorizontal: 12,
        paddingVertical: 6,
        borderRadius: 20,
    },
    brandTitle: {
        color: 'white',
        fontSize: 12,
        fontWeight: '600',
        letterSpacing: 0.5,
    },
    centerContent: {
        justifyContent: 'center',
        alignItems: 'flex-start',
        maxWidth: '80%',
    },
    heroTitle: {
        color: 'white',
        fontSize: 32,
        fontWeight: '800',
        marginBottom: 12,
        textShadowColor: 'rgba(0, 0, 0, 0.5)',
        textShadowOffset: { width: 0, height: 2 },
        textShadowRadius: 4,
    },
    heroSubtitle: {
        color: '#e2e8f0',
        fontSize: 16,
        fontWeight: '500',
        marginBottom: 16,
        opacity: 0.9,
    },
    priceTag: {
        backgroundColor: '#6366f1', // Primary Brand Color
        paddingHorizontal: 16,
        paddingVertical: 8,
        borderRadius: 8,
        marginBottom: 16,
        alignSelf: 'flex-start',
    },
    priceText: {
        color: 'white',
        fontWeight: 'bold',
        fontSize: 18,
    },
    bottomRow: {
        flexDirection: 'row',
        justifyContent: 'flex-start', // specific alignment
    },
    actionButton: {
        flexDirection: 'row',
        alignItems: 'center',
        gap: 8,
        backgroundColor: 'white',
        paddingHorizontal: 24,
        paddingVertical: 12,
        borderRadius: 30, // Pill shape
    },
    actionText: {
        color: '#0f172a',
        fontWeight: '700',
        fontSize: 14,
    },
});
