#!/usr/bin/env python3
"""
ChromeDriver Setup Script for BuyVaultHub Scrapers
Automatically downloads and sets up ChromeDriver for Selenium
"""

import os
import sys
import zipfile
import requests
from pathlib import Path

def get_chrome_version():
    """Get installed Chrome version"""
    try:
        import subprocess
        if sys.platform == "win32":
            # Windows
            result = subprocess.run([
                "reg", "query", 
                "HKEY_CURRENT_USER\\Software\\Google\\Chrome\\BLBeacon", 
                "/v", "version"
            ], capture_output=True, text=True)
            if result.returncode == 0:
                version = result.stdout.split()[-1]
                return version.split('.')[0]  # Return major version
    except Exception:
        pass
    
    print("⚠️  Could not detect Chrome version automatically")
    return input("Please enter your Chrome major version (e.g., 120): ").strip()

def download_chromedriver(version):
    """Download ChromeDriver for the given version"""
    try:
        # Get latest ChromeDriver version for the Chrome version
        api_url = f"https://googlechromelabs.github.io/chrome-for-testing/LATEST_RELEASE_{version}"
        response = requests.get(api_url)
        if response.status_code == 200:
            driver_version = response.text.strip()
        else:
            print(f"⚠️  Could not get ChromeDriver version for Chrome {version}")
            driver_version = version + ".0.0.0"
        
        # Download URL
        if sys.platform == "win32":
            platform = "win32"
            driver_name = "chromedriver.exe"
        elif sys.platform == "darwin":
            platform = "mac-x64"
            driver_name = "chromedriver"
        else:
            platform = "linux64"
            driver_name = "chromedriver"
        
        download_url = f"https://storage.googleapis.com/chrome-for-testing-public/{driver_version}/{platform}/chromedriver-{platform}.zip"
        
        print(f"📥 Downloading ChromeDriver {driver_version} for {platform}...")
        response = requests.get(download_url)
        
        if response.status_code == 200:
            # Save and extract
            zip_path = Path("chromedriver.zip")
            with open(zip_path, "wb") as f:
                f.write(response.content)
            
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(".")
            
            # Move to scrapers directory
            scrapers_dir = Path(__file__).parent
            driver_path = scrapers_dir / driver_name
            
            # Find the extracted driver
            for root, dirs, files in os.walk("."):
                if driver_name in files:
                    os.rename(os.path.join(root, driver_name), driver_path)
                    break
            
            # Clean up
            os.remove(zip_path)
            import shutil
            for root, dirs, files in os.walk("."):
                if "chromedriver" in root and root != str(scrapers_dir):
                    shutil.rmtree(root)
                    break
            
            print(f"✅ ChromeDriver installed at: {driver_path}")
            return str(driver_path)
        else:
            print(f"❌ Failed to download ChromeDriver: HTTP {response.status_code}")
            return None
            
    except Exception as e:
        print(f"❌ Error downloading ChromeDriver: {e}")
        return None

def setup_chromedriver():
    """Main setup function"""
    print("🔧 ChromeDriver Setup for BuyVaultHub Scrapers")
    print("=" * 50)
    
    scrapers_dir = Path(__file__).parent
    driver_name = "chromedriver.exe" if sys.platform == "win32" else "chromedriver"
    driver_path = scrapers_dir / driver_name
    
    # Check if already exists
    if driver_path.exists():
        print(f"✅ ChromeDriver already exists at: {driver_path}")
        return str(driver_path)
    
    # Get Chrome version and download
    version = get_chrome_version()
    if not version:
        print("❌ Chrome version required to download ChromeDriver")
        return None
    
    return download_chromedriver(version)

if __name__ == "__main__":
    setup_chromedriver()
