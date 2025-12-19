import { StyleSheet, Text, View, ScrollView} from 'react-native'
import React from 'react'
import { SafeAreaView } from 'react-native-safe-area-context'
import Header from '../components/Header'
import SubHeader from '../components/SubHeader'
import Category from '../components/Category'
import TopRatedSection from '../components/TopRatedSection'
import WhatsNewsection from '../components/WhatsNewsection'
import FloatingChat from '../components/FloatingChat';

const HomeScreen = () => {
  
  return (
    <SafeAreaView style={{ flex: 1 }} edges={['top']}>
      <View style={{ flex: 1 }}>
        <ScrollView showsVerticalScrollIndicator={false}>
          <Header />
          <SubHeader />
          <Category />
          <TopRatedSection />
          <WhatsNewsection />
        </ScrollView>
        <FloatingChat />
      </View>
    </SafeAreaView>
  )
}

export default HomeScreen

const styles = StyleSheet.create({})