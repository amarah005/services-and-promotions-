# 🛠️ Project Setup Guide

This guide will help you set up, run, and build the **Home Services Marketplace App**.

## 📋 Prerequisites

Before you begin, ensure you have the following installed:
1.  **Node.js** (LTS version recommeded): [Download Here](https://nodejs.org/)
2.  **Git**: [Download Here](https://git-scm.com/)
3.  **Expo Go App** (on your mobile):
    *   [Android (Play Store)](https://play.google.com/store/apps/details?id=host.exp.exponent)
    *   [iOS (App Store)](https://apps.apple.com/us/app/expo-go/id982107779)

---

## 🚀 Installation

1.  **Clone the Repository**
    ```bash
    git clone https://github.com/amarah005/services-and-promotions-.git
    cd services-and-promotions-
    ```

2.  **Install Dependencies**
    ```bash
    npm install
    ```
    *This downloads all required libraries (React Native, Expo, Google Generative AI, etc.).*

---

## 🔑 Environment Setup (Important!)

The app uses Google Gemini AI, which requires a secure API Key. This key is **not** included in the code for security reasons.

1.  **Get a Free API Key**:
    *   Go to [Google AI Studio](https://aistudio.google.com/app/apikey) and create a key.

2.  **Create a `.env` file**:
    *   In the root folder of the project, create a new file named `.env`.
    *   Add your key inside it like this:
        ```text
        EXPO_PUBLIC_GEMINI_API_KEY=AIzaSyxxxxxxxxxxxxxxxxxxxxxxxxxxxx
        ```
    *   *Note: This file is ignored by Git to keep your key safe.*

---

## 🏃‍♂️ Running the App

1.  **Start the Development Server**:
    ```bash
    npm start
    ```

2.  **Open the App**:
    *   You will see a QR code in the terminal.
    *   **Android**: Open "Expo Go" and scan the QR code.
    *   **iOS**: Open the Camera app and scan the QR code.
    *   **Emulator**: Press `a` (Android) or `i` (iOS) in the terminal.

---

## 📱 Building the APK (Android)

To create a standalone `.apk` file that you can install on any Android phone without Expo Go:

1.  **Install EAS CLI**:
    ```bash
    npm install -g eas-cli
    ```

2.  **Login to Expo**:
    ```bash
    eas login
    ```

3.  **Build the APK**:
    ```bash
    eas build -p android --profile preview
    ```
    *   This process takes ~10-15 minutes.
    *   Once finished, it will provide a **Direct Download Link** for your APK.

---

## 🔄 Updating Data

If you have new CSV data files (e.g., inside `assets/data` or `assets/data2`):

1.  Run the import script to regenerate the `mockData.ts` file:
    ```bash
    node scripts/import_data.js
    ```
2.  Restart the server (`npm start`) to see changes.
