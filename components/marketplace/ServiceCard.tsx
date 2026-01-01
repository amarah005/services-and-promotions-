import { Ionicons } from '@expo/vector-icons';
import { Image } from 'expo-image';
import React from 'react';
import { Linking, Pressable, StyleSheet, Text, View } from 'react-native';

interface Props {
    item: any;
}

export function ServiceCard({ item }: Props) {
    const handlePress = () => {
        if (item.link) {
            Linking.openURL(item.link).catch(err => console.error("Couldn't load page", err));
        }
    };

    return (
        <Pressable onPress={handlePress} style={({ pressed }) => [
            styles.card,
            pressed && { transform: [{ scale: 0.98 }], opacity: 0.9 } // Add subtle press effect
        ]}>
            <View style={[styles.imageContainer, { backgroundColor: item.color ? item.color + '15' : '#f3f4f6' }]}>
                {item.image ? (
                    <Image
                        source={item.image}
                        style={styles.image}
                        contentFit="cover"
                        transition={200}
                    />
                ) : (
                    <View style={[styles.placeholderImage, { backgroundColor: item.color || '#ccc' }]}>
                        <Text style={styles.placeholderText}>{item.title.charAt(0)}</Text>
                    </View>
                )}

                {item.badge && (
                    <View style={styles.badge}>
                        <Text style={styles.badgeText}>{item.badge}</Text>
                    </View>
                )}
            </View>
            <View style={styles.content}>
                <Text style={styles.title} numberOfLines={1}>{item.title}</Text>
                <Text style={styles.subtitle} numberOfLines={2}>
                    {item.details || 'Professional Service'}
                </Text>
                <View style={styles.footer}>
                    <Text style={styles.price}>{item.price}</Text>
                    <View style={[styles.iconButton]}>
                        <Ionicons name="arrow-forward-circle" size={24} color={item.color || "#000"} />
                    </View>
                </View>
            </View>
        </Pressable>
    );
}

const styles = StyleSheet.create({
    card: {
        backgroundColor: 'white',
        borderRadius: 16,
        width: '100%',
        borderWidth: 1,
        borderColor: '#f0f0f0',
        overflow: 'hidden',
    },
    imageContainer: {
        height: 160,
        justifyContent: 'center',
        alignItems: 'center',
        position: 'relative',
        backgroundColor: '#f9fafb',
        width: '100%',
    },
    image: {
        width: '100%',
        height: '100%',
    },
    placeholderImage: {
        width: 60,
        height: 60,
        borderRadius: 30,
        justifyContent: 'center',
        alignItems: 'center',
        marginBottom: 8,
    },
    placeholderText: {
        color: 'white',
        fontSize: 24,
        fontWeight: 'bold',
    },
    badge: {
        position: 'absolute',
        top: 12,
        right: 12,
        backgroundColor: '#ec4899',
        paddingHorizontal: 8,
        paddingVertical: 4,
        borderRadius: 20,
        zIndex: 10,
    },
    badgeText: {
        color: 'white',
        fontSize: 10,
        fontWeight: '700',
    },
    content: {
        padding: 12,
    },
    title: {
        fontSize: 15,
        fontWeight: '700',
        color: '#111827',
        marginBottom: 4,
    },
    subtitle: {
        fontSize: 12,
        color: '#6b7280',
        marginBottom: 12,
        height: 32, // Fixed height for 2 lines alignment
        lineHeight: 16,
    },
    footer: {
        flexDirection: 'row',
        justifyContent: 'space-between',
        alignItems: 'center',
    },
    price: {
        fontSize: 16,
        fontWeight: '800',
        color: '#111827',
    },
    iconButton: {
        // 
    }
});
