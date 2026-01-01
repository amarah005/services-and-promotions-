import { Ionicons } from '@expo/vector-icons';
import React, { useEffect, useRef, useState } from 'react';
import {
    Animated,
    FlatList, KeyboardAvoidingView,
    Modal,
    Platform,
    StyleSheet, Text,
    TextInput, TouchableOpacity,
    View
} from 'react-native';
import { ServiceCard } from '../marketplace/ServiceCard';
import { ChatMessage } from './ChatLogic';
import { generateSmartResponse } from './GeminiService';
// import { processUserQuery } from './ChatLogic'; // Old logic

export function ChatButton() {
    const [visible, setVisible] = useState(false);
    const [messages, setMessages] = useState<ChatMessage[]>([
        {
            id: 'welcome',
            text: 'Hi! I use AI to help you find the best services. Ask me anything!',
            sender: 'bot'
        }
    ]);
    const [input, setInput] = useState('');
    const [loading, setLoading] = useState(false);
    const scaleAnim = useRef(new Animated.Value(0)).current;

    useEffect(() => {
        if (visible) {
            Animated.spring(scaleAnim, {
                toValue: 1,
                useNativeDriver: true,
            }).start();
        } else {
            scaleAnim.setValue(0);
        }
    }, [visible]);

    const handleSend = async () => {
        if (!input.trim()) return;

        const userMsg: ChatMessage = {
            id: Date.now().toString(),
            text: input,
            sender: 'user'
        };

        setMessages(prev => [...prev, userMsg]);
        setInput('');
        setLoading(true);

        try {
            // Use Gemini AI
            const botResponse = await generateSmartResponse(userMsg.text);
            setMessages(prev => [...prev, botResponse]);
        } catch (e) {
            console.error("Chat Error", e);
        } finally {
            setLoading(false);
        }
    };

    const renderMessage = ({ item }: { item: ChatMessage }) => {
        const isUser = item.sender === 'user';
        return (
            <View style={[styles.messageRow, isUser ? styles.userRow : styles.botRow]}>
                {!isUser && (
                    <View style={styles.botAvatar}>
                        <Ionicons name="sparkles" size={16} color="white" />
                    </View>
                )}

                <View style={[styles.bubble, isUser ? styles.userBubble : styles.botBubble]}>
                    <Text style={[styles.messageText, isUser ? styles.userText : styles.botText]}>{item.text}</Text>
                </View>

                {/* Render any attached cards */}
                {!isUser && item.data && item.data.length > 0 && (
                    <View style={styles.resultContainer}>
                        {item.data.map((service, index) => (
                            <View key={service.id} style={styles.resultItem}>
                                <ServiceCard item={service} />
                            </View>
                        ))}
                    </View>
                )}
            </View>
        );
    };

    return (
        <>
            <TouchableOpacity
                style={styles.fab}
                onPress={() => setVisible(true)}
                activeOpacity={0.8}
            >
                <Ionicons name="chatbubbles" size={28} color="white" />
            </TouchableOpacity>

            <Modal
                visible={visible}
                animationType="slide"
                transparent={true}
                onRequestClose={() => setVisible(false)}
            >
                <KeyboardAvoidingView
                    style={styles.modalOverlay}
                    behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
                >
                    <View style={styles.modalContent}>
                        {/* Header */}
                        <View style={styles.header}>
                            <View style={styles.headerTitleContainer}>
                                <Ionicons name="sparkles" size={20} color="#6366f1" />
                                <Text style={styles.headerTitle}>AI Assistant</Text>
                            </View>
                            <TouchableOpacity onPress={() => setVisible(false)} style={styles.closeBtn}>
                                <Ionicons name="close" size={24} color="#64748b" />
                            </TouchableOpacity>
                        </View>

                        {/* Chat Area */}
                        <FlatList
                            data={messages}
                            renderItem={renderMessage}
                            keyExtractor={item => item.id}
                            contentContainerStyle={styles.listContent}
                            showsVerticalScrollIndicator={false}
                        />

                        {/* Input Area */}
                        <View style={styles.inputContainer}>
                            <TextInput
                                style={styles.input}
                                placeholder="Ask for a service..."
                                placeholderTextColor="#94a3b8"
                                value={input}
                                onChangeText={setInput}
                                onSubmitEditing={handleSend}
                            />
                            <TouchableOpacity
                                style={[styles.sendBtn, !input.trim() && styles.sendBtnDisabled]}
                                onPress={handleSend}
                                disabled={!input.trim()}
                            >
                                <Ionicons name="send" size={20} color="white" />
                            </TouchableOpacity>
                        </View>
                    </View>
                </KeyboardAvoidingView>
            </Modal>
        </>
    );
}

const styles = StyleSheet.create({
    fab: {
        position: 'absolute',
        bottom: 24,
        right: 24,
        width: 60,
        height: 60,
        borderRadius: 30,
        backgroundColor: '#6366f1',
        justifyContent: 'center',
        alignItems: 'center',
        shadowColor: '#6366f1',
        shadowOffset: { width: 0, height: 4 },
        shadowOpacity: 0.3,
        shadowRadius: 8,
        elevation: 8,
        zIndex: 100,
    },
    modalOverlay: {
        flex: 1,
        backgroundColor: 'rgba(0,0,0,0.5)',
        justifyContent: 'flex-end',
    },
    modalContent: {
        backgroundColor: '#f8fafc', // Light gray bg
        borderTopLeftRadius: 24,
        borderTopRightRadius: 24,
        height: '80%', // Takes up 80% of screen
        overflow: 'hidden',
    },
    header: {
        flexDirection: 'row',
        justifyContent: 'space-between',
        alignItems: 'center',
        padding: 16,
        borderBottomWidth: 1,
        borderBottomColor: '#e2e8f0',
        backgroundColor: 'white',
    },
    headerTitleContainer: {
        flexDirection: 'row',
        alignItems: 'center',
        gap: 8,
    },
    headerTitle: {
        fontSize: 18,
        fontWeight: 'bold',
        color: '#1e293b',
    },
    closeBtn: {
        padding: 4,
    },
    listContent: {
        padding: 16,
        paddingBottom: 20,
    },
    messageRow: {
        marginBottom: 16,
        maxWidth: '100%',
    },
    userRow: {
        alignItems: 'flex-end',
    },
    botRow: {
        alignItems: 'flex-start',
    },
    botAvatar: {
        width: 24,
        height: 24,
        borderRadius: 12,
        backgroundColor: '#6366f1',
        justifyContent: 'center',
        alignItems: 'center',
        marginBottom: 4,
    },
    bubble: {
        padding: 12,
        borderRadius: 16,
        maxWidth: '85%',
    },
    userBubble: {
        backgroundColor: '#6366f1',
        borderBottomRightRadius: 4,
    },
    botBubble: {
        backgroundColor: 'white',
        borderTopLeftRadius: 4,
        borderWidth: 1,
        borderColor: '#e2e8f0',
    },
    userText: {
        color: 'white',
        fontSize: 15,
    },
    botText: {
        color: '#1e293b',
        fontSize: 15,
    },
    messageText: {
        lineHeight: 22,
    },
    resultContainer: {
        marginTop: 12,
        width: '85%',
        gap: 12,
    },
    resultItem: {
        width: '100%',
    },
    inputContainer: {
        flexDirection: 'row',
        padding: 16,
        backgroundColor: 'white',
        borderTopWidth: 1,
        borderTopColor: '#e2e8f0',
        alignItems: 'center',
        gap: 12,
    },
    input: {
        flex: 1,
        backgroundColor: '#f1f5f9',
        borderRadius: 24,
        paddingHorizontal: 16,
        paddingVertical: 12,
        fontSize: 16,
        color: '#334155',
    },
    sendBtn: {
        width: 44,
        height: 44,
        borderRadius: 22,
        backgroundColor: '#6366f1',
        justifyContent: 'center',
        alignItems: 'center',
    },
    sendBtnDisabled: {
        backgroundColor: '#cbd5e1',
    },
});
