import React, { useState, useEffect, useRef } from 'react';
import { 
  View, 
  Text, 
  TouchableOpacity, 
  TextInput, 
  StyleSheet, 
  ScrollView, 
  KeyboardAvoidingView,
  Platform,
  Keyboard,
  Dimensions,
  Animated
} from 'react-native';
import Ionicons from 'react-native-vector-icons/Ionicons';

const { height, width } = Dimensions.get('window');

const FloatingChatPopup = () => {
  const [visible, setVisible] = useState(false);
  const [messages, setMessages] = useState([
    { text: "Hello! I'm Buy Vault Hub Assistant. How can I help you today?", fromBot: true },
  ]);
  const [input, setInput] = useState('');
  const [keyboardHeight, setKeyboardHeight] = useState(0);
  
  // Animation values
  const pulseAnim = useRef(new Animated.Value(1)).current;
  const scrollViewRef = useRef(null);

  // Pulse animation for chat button
  useEffect(() => {
    const pulseAnimation = Animated.loop(
      Animated.sequence([
        Animated.timing(pulseAnim, {
          toValue: 1.1,
          duration: 1000,
          useNativeDriver: true,
        }),
        Animated.timing(pulseAnim, {
          toValue: 1,
          duration: 1000,
          useNativeDriver: true,
        }),
      ])
    );

    pulseAnimation.start();

    return () => {
      pulseAnimation.stop();
    };
  }, []);

  // Auto scroll to bottom when new messages come
  useEffect(() => {
    if (scrollViewRef.current) {
      setTimeout(() => {
        scrollViewRef.current?.scrollToEnd({ animated: true });
      }, 100);
    }
  }, [messages]);

  // Keyboard height track karein
  useEffect(() => {
    const keyboardDidShowListener = Keyboard.addListener(
      Platform.OS === 'ios' ? 'keyboardWillShow' : 'keyboardDidShow',
      (e) => {
        setKeyboardHeight(e.endCoordinates.height);
      }
    );

    const keyboardDidHideListener = Keyboard.addListener(
      Platform.OS === 'ios' ? 'keyboardWillHide' : 'keyboardDidHide',
      () => {
        setKeyboardHeight(0);
      }
    );

    return () => {
      keyboardDidShowListener.remove();
      keyboardDidHideListener.remove();
    };
  }, []);

  // Send message and bot reply
  const sendMessage = () => {
    if (input.trim() === '') return;

    // user message
    const userMessage = { text: input, fromBot: false };

    // bot reply
    const botMessage = { text: "I'm still learning — but I'm here to help!", fromBot: true };

    setMessages([...messages, userMessage, botMessage]);
    setInput('');
  };

  return (
    <View style={{ flex: 1 }}>
      {/* Floating Chat Button with Pulse Animation and Blue Shadow */}
      <Animated.View 
        style={[
          styles.chatButtonContainer,
          {
            transform: [{ scale: pulseAnim }],
          }
        ]}
      >
        <TouchableOpacity 
          style={styles.chatButton} 
          onPress={() => setVisible(!visible)}
          activeOpacity={0.8}
        >
          <Ionicons name="chatbubble-outline" size={28} color="#fff" />
        </TouchableOpacity>
      </Animated.View>

      {/* Chat Popup with Keyboard Avoiding */}
      {visible && (
        <KeyboardAvoidingView
          style={[
            styles.chatPopupContainer,
            { 
              bottom: keyboardHeight > 0 ? keyboardHeight + 35 : 120 
            }
          ]}
          behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
          keyboardVerticalOffset={Platform.OS === 'ios' ? 60 : 40}
        >
          <View style={styles.chatPopup}>
            {/* Header */}
            <View style={styles.header}>
              <View style={styles.headerLeft}>
                <View style={styles.botIndicator}></View>
                <Text style={styles.headerTitle}>Buy Vault Hub AI</Text>
              </View>
              <TouchableOpacity onPress={() => setVisible(false)} style={styles.closeButton}>
                <Ionicons name="close" size={22} color="#fff" />
              </TouchableOpacity>
            </View>

            {/* Messages Area */}
            <ScrollView 
              style={styles.messagesArea}
              showsVerticalScrollIndicator={false}
              ref={scrollViewRef}
              contentContainerStyle={styles.messagesContent}
            >
              {messages.map((msg, index) => (
                <View
                  key={index}
                  style={[
                    styles.messageBubble,
                    msg.fromBot ? styles.botMessage : styles.userMessage,
                  ]}
                >
                  <Text style={[
                    styles.messageText,
                    msg.fromBot ? styles.botText : styles.userText
                  ]}>
                    {msg.text}
                  </Text>
                </View>
              ))}
            </ScrollView>

            {/* Input Area */}
            <View style={styles.inputArea}>
              <TextInput
                style={styles.input}
                placeholder="Type a message..."
                value={input}
                onChangeText={setInput}
                multiline={true}
                placeholderTextColor="#999"
                textAlignVertical="center"
              />
              <TouchableOpacity 
                style={[
                  styles.sendButton,
                  input.trim() === '' && styles.sendButtonDisabled
                ]} 
                onPress={sendMessage}
                disabled={input.trim() === ''}
              >
                <Ionicons name="send" size={18} color="#fff" />
              </TouchableOpacity>
            </View>
          </View>
        </KeyboardAvoidingView>
      )}
    </View>
  );
};

const styles = StyleSheet.create({
  chatButtonContainer: {
    position: 'absolute',
    bottom: 30,
    right: 25,
    zIndex: 1000,
    // Blue Shadow Effect
    shadowColor: '#006bddff',
    shadowOffset: {
      width: 0,
      height: 0,
    },
    shadowOpacity: 0.8,
    shadowRadius: 20,
    elevation: 15,
  },
  chatButton: {
    backgroundColor: '#007bff',
    width: 65,
    height: 65,
    borderRadius: 32.5,
    justifyContent: 'center',
    alignItems: 'center',
    // Inner glow effect
    shadowColor: '#0064ceff',
    shadowOffset: {
      width: 0,
      height: 4,
    },
    shadowOpacity: 0.6,
    shadowRadius: 8,
    elevation: 8,
    borderWidth: 2,
    borderColor: 'rgba(255,255,255,0.2)',
  },
  chatPopupContainer: {
    position: 'absolute',
    right: 20,
    width: width * 0.85, // 85% of screen width
    maxWidth: 320,
    height: 400, // Slightly increased height
    zIndex: 999,
  },
  chatPopup: {
    width: '100%',
    height: '100%',
    backgroundColor: '#fff',
    borderRadius: 16,
    overflow: 'hidden',
    elevation: 12,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 6 },
    shadowOpacity: 0.25,
    shadowRadius: 8,
    borderWidth: 1,
    borderColor: '#e8e8e8',
  },
  header: {
    backgroundColor: '#007bff',
    paddingVertical: 14,
    paddingHorizontal: 16,
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  headerLeft: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  botIndicator: {
    width: 12,
    height: 12,
    borderRadius: 6,
    backgroundColor: '#34f354ff',
    marginRight: 10,
  },
  headerTitle: {
    color: '#fff',
    fontWeight: '700',
    fontSize: 16,
  },
  closeButton: {
    padding: 4,
  },
  messagesArea: {
    flex: 1,
    backgroundColor: '#f8f9fa',
  },
  messagesContent: {
    paddingVertical: 8,
    paddingHorizontal: 12,
  },
  messageBubble: {
    paddingVertical: 10,
    paddingHorizontal: 14,
    marginVertical: 5,
    borderRadius: 18,
    maxWidth: '85%',
  },
  botMessage: {
    backgroundColor: '#ffffff',
    alignSelf: 'flex-start',
    borderWidth: 1,
    borderColor: '#e9ecef',
  },
  userMessage: {
    backgroundColor: '#007bff',
    alignSelf: 'flex-end',
  },
  messageText: {
    fontSize: 15,
    lineHeight: 20,
  },
  botText: {
    color: '#2d3748',
  },
  userText: {
    color: '#ffffff',
  },
  inputArea: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: 12,
    paddingHorizontal: 16,
    borderTopWidth: 1,
    borderColor: '#e9ecef',
    backgroundColor: '#fff',
    minHeight: 70,
  },
  input: {
    flex: 1,
    backgroundColor: '#f8f9fa',
    borderRadius: 24,
    paddingHorizontal: 16,
    paddingVertical: 10,
    maxHeight: 100,
    fontSize: 15,
    borderWidth: 1,
    borderColor: '#e9ecef',
    marginRight: 10,
  },
  sendButton: {
    backgroundColor: '#007bff',
    width: 44,
    height: 44,
    borderRadius: 22,
    alignItems: 'center',
    justifyContent: 'center',
    elevation: 3,
    shadowColor: '#007bff',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.3,
    shadowRadius: 3,
  },
  sendButtonDisabled: {
    backgroundColor: '#cbd5e0',
    shadowColor: 'transparent',
  },
});

export default FloatingChatPopup;