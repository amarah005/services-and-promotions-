# 🚀 BuyVaultHub - Full Stack Project

Welcome to **BuyVaultHub**, a comprehensive shopping platform featuring a **React Native Mobile App** (Frontend) and a **Django REST Framework** (Backend).

This guide is designed for both beginners and team collaborators to get the project up and running smoothly.

---

## 📂 Folder Structure

Here is how the project is organized. Understanding this will help you navigate and modify the code.

```text
BuyVaultHub/
├── android/             # Android native source code
├── ios/                 # iOS native source code
├── src/                 # 🌐 FRONTEND CORE (React Native)
│   ├── assets/          # Images, fonts, and static files
│   ├── components/      # Reusable UI elements (buttons, inputs)
│   ├── screens/         # Main app pages (Home, Login, Product Detail)
│   ├── navigations/     # App routing logic
│   └── utils/           # Helper functions
├── backend/             # 🐍 BACKEND CORE (Django)
│   ├── buyvaulthub/     # Main project settings & config
│   ├── products/        # Product management API
│   ├── users/           # User authentication & profiles
│   ├── recommendations/ # AI-driven recommendation logic
│   ├── manage.py        # Django CLI entry point
│   └── requirements.txt # Python dependencies
├── AppBackend/          # 🔌 NETWORKING LAYER (Detailed below)
│   ├── config.js        # API Base URL & Endpoints
│   ├── apiClient.js     # Centralized networking logic (Fetch + JWT)
│   ├── api.js           # High-level API methods (Auth, Products,etc.)
│   └── googleLogin.js   # Google Sign-In integration
├── App.tsx              # Main entry point for the mobile app
├── package.json         # Frontend dependencies and scripts
└── .gitignore           # Tells Git which files to ignore
```

---

## 🔗 How They Connect

The **Frontend** and **Backend** communicate via an **API (Application Programming Interface)**.

1.  **Backend (Django)** runs a local server (usually at `http://127.0.0.1:8000`).
2.  **Frontend (React Native)** makes requests to this server to fetch products, log in users, etc.
3.  **AppBackend/config.js** is the "bridge". It holds the `BASE_URL`:
    - For Android: `http://10.0.2.2:8000` (Emulator's way to see your PC).
    - For iOS: `http://localhost:8000`.

---

## 🔌 Detailed: AppBackend (The Networking Layer)

The `AppBackend` folder is the brain of the app's communication. It handles how the data travels between your phone and the server.

### 1. `config.js` (The Settings)
*   **What it does**: Stores the "Address" of your server and the names of all "Doors" (Endpoints) to get data.
*   **Why we need it**: Instead of writing the server URL everywhere, we change it only here.

### 2. `apiClient.js` (The Engine)
*   **What it does**: This is the most complex file. It handles:
    *   **JWT Tokens**: Automatically attaches your "Identity Card" (Login Token) to every request.
    *   **Auto-Refresh**: If your token expires while using the app, this file automatically asks the server for a new one without interrupting the user.
    *   **Timeouts**: Stops a request if it takes too long (e.g., bad internet).
*   **Why we need it**: It keeps the app secure and stable.

### 3. `api.js` (The Menu)
*   **What it does**: A high-level list of "Orders" you can make.
    *   `authAPI.login()`: Order a login.
    *   `productsAPI.getProducts()`: Get a list of products.
    *   `wishlistAPI.addToWishlist()`: Add an item to your favorites.
*   **Why we need it**: It makes the code very easy to read. Developers just call one function instead of writing raw code.

### 4. `googleLogin.js` (The Google Key)
*   **What it does**: Specifically handles signing in with a Google account. It talks to Google first, gets a special code, and then sends it to our Django server.

---

## 🛠️ Installation & Setup

Follow these steps in order to run the project on your machine.

### 1. Backend Setup (Django)
Open a terminal in the `backend/` folder:

```bash
# Navigate to backend
cd backend

# Create a virtual environment (recommended)
python -m venv venv
venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt

# Configure your .env file
# (Copy credentials from your team lead)

# Run migrations (Setup database)
python manage.py migrate

# Start the server
python manage.py runserver
```

### 2. Frontend Setup (React Native)
Open another terminal in the **root** folder (`BuyVaultHub/`):

```bash
# Install Node modules
npm install

# Start Metro Bundler
npm start

# Run on Android
npm run android
```

---

## 👥 Information for Team Members

If you just downloaded this project from GitHub, please note:

- **Missing Files**: Files like `.env` and `node_modules` are NOT pushed to GitHub for security and size reasons.
- **Setup Required**: You must follow the **Installation & Setup** steps above to generate these files locally.
- **Database**: The project uses **PostgreSQL**. Ensure you have it installed and a database named `buyvaulthub_db` created before running migrations.

---

## ✅ Ready for Production?
The code pushed to GitHub is clean and follows industry standards. Once your teammate downloads it and follows the setup steps, everything will work perfectly!

---
* Happy Coding!*
