# 🚀 START HERE: Get Backend and App Running

## The Problem
- ✅ Database imported successfully
- ❌ Backend can't connect (missing password)
- ❌ React Native app can't fetch data (backend not running)

## Quick Fix (5 minutes)

### Step 1: Set Database Password

**Option A: Use the setup script (Easiest)**
```powershell
cd backend
powershell -ExecutionPolicy Bypass -File setup_env.ps1
```
Enter your PostgreSQL password when prompted.

**Option B: Create .env file manually**
1. Go to `backend` folder
2. Create a file named `.env`
3. Add this line (replace with your actual password):
   ```
   DATABASE_PASSWORD=your_postgres_password
   ```

### Step 2: Start Backend Server

**Option A: Use the batch file**
```powershell
cd backend
.\START_BACKEND.bat
```

**Option B: Manual start**
```powershell
cd backend
.\venv\Scripts\Activate.ps1
python manage.py runserver 0.0.0.0:8000
```

**✅ You should see:** `Starting development server at http://0.0.0.0:8000/`

### Step 3: Test Backend (in browser)

Open: http://localhost:8000/api/v1/products/

You should see JSON data (products from your database).

### Step 4: Start React Native App

**Open a NEW terminal** (keep backend running):

```powershell
# Terminal 1: Metro Bundler
cd D:\fyp_app\BuyVaultHub
npx react-native start

# Terminal 2: Run Android App (in another terminal)
cd D:\fyp_app\BuyVaultHub
npx react-native run-android
```

### Step 5: Verify Data in App

- Open the app in the emulator
- Products should load from the database
- Categories, wishlist, etc. should work

---

## Troubleshooting

### "fe_sendauth: no password supplied"
→ You didn't set the database password. Go back to Step 1.

### "Connection refused" in app
→ Backend not running or not accessible. Make sure:
- Backend is running on `0.0.0.0:8000` (not `localhost:8000`)
- Check `AppBackend/config.js` has `http://10.0.2.2:8000/api/v1`

### No data showing
→ Test the API directly: http://localhost:8000/api/v1/products/
→ Check backend terminal for errors

---

## Need More Help?

See detailed guides:
- `RUN_BACKEND_AND_APP.md` - Complete setup guide
- `QUICK_FIX_DATABASE_PASSWORD.md` - Password configuration help

