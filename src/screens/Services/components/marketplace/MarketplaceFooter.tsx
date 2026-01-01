import Ionicons from 'react-native-vector-icons/Ionicons';
import React from 'react';
import { StyleSheet, Text, View } from 'react-native';

export function MarketplaceFooter() {
    return (
        <View style={styles.footer}>
            <View style={styles.row}>
                <View style={styles.column}>
                    <Text style={styles.header}>About</Text>
                    <Text style={styles.link}>Home</Text>
                    <Text style={styles.link}>Our story</Text>
                </View>
                <View style={styles.column}>
                    <Text style={styles.header}>Help</Text>
                    <Text style={styles.link}>FAQs</Text>
                </View>
                <View style={styles.column}>
                    <Text style={styles.header}>Contact</Text>
                    <Text style={styles.smallText}>Phone: +1 123 456 7890</Text>
                    <Text style={styles.smallText}>Email: buyvault@email.com</Text>
                </View>
            </View>

            <View style={styles.bottomRow}>
                <View style={styles.socials}>
                    <Ionicons name="logo-twitter" size={16} color="#6b7280" />
                    <Ionicons name="logo-facebook" size={16} color="#6b7280" />
                    <Ionicons name="logo-instagram" size={16} color="#6b7280" />
                    <Ionicons name="logo-youtube" size={16} color="#6b7280" />
                </View>
                <Text style={styles.copyright}>© 2022 Brand, Inc. • Privacy • Terms • Sitemap</Text>
            </View>
        </View>
    );
}

const styles = StyleSheet.create({
    footer: {
        backgroundColor: '#111827', // Gray 900
        padding: 32,
        marginTop: 40,
        borderRadius: 0,
    },
    row: {
        flexDirection: 'row',
        justifyContent: 'space-between',
        flexWrap: 'wrap',
        gap: 24,
        marginBottom: 32,
    },
    column: {
        minWidth: 100,
    },
    header: {
        color: 'white',
        fontWeight: 'bold',
        marginBottom: 16,
        fontSize: 14,
    },
    link: {
        color: '#9ca3af',
        marginBottom: 8,
        fontSize: 14,
    },
    smallText: {
        color: '#9ca3af',
        marginBottom: 8,
        fontSize: 12,
    },
    bottomRow: {
        borderTopWidth: 1,
        borderTopColor: '#374151',
        paddingTop: 24,
        flexDirection: 'row',
        justifyContent: 'space-between',
        alignItems: 'center',
        flexWrap: 'wrap',
        gap: 16,
    },
    socials: {
        flexDirection: 'row',
        gap: 16,
    },
    copyright: {
        color: '#6b7280',
        fontSize: 12,
    }
});
