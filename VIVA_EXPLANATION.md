# 🎓 Project Viva / Defense Guide

This document contains technical details, architecture explanations, and key concepts to help you answer questions during your project viva or presentation.

---

## 1. 💡 Project Overview
**App Name:** Home Services Marketplace
**Goal:** To connect users with home service providers (Electricians, Plumbers, Beauticians) and provide an intelligent AI Assistant to help them find the right service.

**Why this project?**
*   SOLVES the problem of finding reliable local prices.
*   USES modern AI to make searching conversational (instead of just browsing lists).
*   CROSS-PLATFORM (Works on Android & iOS).

---

## 2. 🛠️ Technology Stack (Why did we use these?)

| Technology | Purpose | Why this choice? |
| :--- | :--- | :--- |
| **React Native** | UI Framework | Allows building **native apps** for both Android & iOS using JavaScript. Better performance than web views. |
| **Expo** | Build Tool | Simplifies development. Provides "Expo Go" for instant testing and "EAS" for cloud building. |
| **Google Gemini (AI)** | Artificial Intelligence | Powerful LLM (Large Language Model) that is free-to-start and faster than OpenAI for this use case (`gemini-2.0-flash`). |
| **TypeScript** | Programming Language | Adds "Types" to JavaScript, reducing bugs and making code easier to read/maintain. |
| **Expo Router** | Navigation | Uses file-based routing (like Next.js), making navigation intuitive based on folder structure. |

---

## 3. 🤖 Key Feature: AI Chatbot (The Star Feature)

The chatbot is not just a "talker"; it is a **RAG (Retrieval-Augmented Generation)** system.

### **How it works (The Logic):**
1.  **User Asks a Question:** e.g., *"How much for AC service?"*
2.  **Retrieval (Search):**
    *   The app **does not** just send this text to Google.
    *   First, it searches our LOCAL database (`mockData.ts`) for relevant keywords ("AC", "Service").
    *   **Scoring System:** It ranks services. Exact matches get higher scores.
3.  **Context Construction:**
    *   It takes the top 5 most relevant results (e.g., "AC General Service @ Rs 3300", "AC Install @ Rs 5000").
    *   It creates a hidden "System Prompt" like:
        > *"You are a helper. Here isn't general info, here is OUR price list: [List]. Answer the user based on THIS list."*
4.  **Generation:**
    *   This prompt is sent to Google Gemini.
    *   Gemini writes a human-like response using our *exact* prices.
5.  **Fallback (Safety):**
    *   If internet fails or API is down, it switches to "Offline Mode" (a simple keyword matcher) so the app never crashes.

---

## 4. 📂 Code Structure Walkthrough

If the examiner asks "Show me your code", point them here:

*   **`components/chatbot/GeminiService.ts`**:
    *   This is the brain. It connects to Google.
    *   It contains the **Scoring Logic** (filtering irrelevant results).
    *   **Viva Tip:** Mention how you fixed the "Washing Machine showing up for AC" bug by implementing a relative score threshold.
*   **`scripts/import_data.js`**:
    *   We don't manually type thousands of services.
    *   This script reads **CSV files** (Excel data) and automatically writes code (`mockData.ts`).
    *   It handles multiple sources (Mahir, Guru) and merges them.
*   **`.env`**:
    *   Stores the **Secret API Key**.
    *   **Security Feature:** Mention that you use `.gitignore` so your secret key is never uploaded to GitHub.

---

## 5. ⚠️ Challenges & Solutions (Impress the Examiner!)

**Challenge 1: "The AI hallucinated (made up) prices."**
*   *Solution:* We used **RAG**. We force the AI to only look at *our* provided context list, so it only quotes real database prices.

**Challenge 2: "API Key Security."**
*   *Solution:* Initially, the key was in the code (bad). We moved it to environment variables (`.env`) to prevent hacking/leaks.

**Challenge 3: "Messy Data."**
*   *Solution:* The raw data was in multiple CSVs with different columns. I wrote a custom **Node.js script** to normalize and merge them into a standard format.

---

## 6. 🔮 Future Scope
*   **Voice Support:** Add "Speak to Chat".
*   **Booking System:** Allow users to "Book Now" directly inside the chat.
*   **Multi-Language:** Support Urdu/Hindi using Gemini's translation capabilities.
