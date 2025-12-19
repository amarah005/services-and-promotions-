# PowerShell script to create .env file for Django backend
# This script helps you configure the PostgreSQL database password

Write-Host "=== Django Backend Environment Setup ===" -ForegroundColor Cyan
Write-Host ""

# Check if .env already exists
if (Test-Path .env) {
    Write-Host "⚠️  .env file already exists!" -ForegroundColor Yellow
    $overwrite = Read-Host "Do you want to overwrite it? (y/n)"
    if ($overwrite -ne "y" -and $overwrite -ne "Y") {
        Write-Host "Cancelled. Exiting..." -ForegroundColor Yellow
        exit
    }
}

Write-Host "Enter your PostgreSQL database configuration:" -ForegroundColor Green
Write-Host ""

# Get database password
$dbPassword = Read-Host "PostgreSQL Password (for user 'postgres')" -AsSecureString
$dbPasswordPlain = [Runtime.InteropServices.Marshal]::PtrToStringAuto(
    [Runtime.InteropServices.Marshal]::SecureStringToBSTR($dbPassword)
)

# Get other settings (with defaults)
$dbName = Read-Host "Database Name [buyvaulthub_db]"
if ([string]::IsNullOrWhiteSpace($dbName)) { $dbName = "buyvaulthub_db" }

$dbUser = Read-Host "Database User [postgres]"
if ([string]::IsNullOrWhiteSpace($dbUser)) { $dbUser = "postgres" }

$dbHost = Read-Host "Database Host [localhost]"
if ([string]::IsNullOrWhiteSpace($dbHost)) { $dbHost = "localhost" }

$dbPort = Read-Host "Database Port [5432]"
if ([string]::IsNullOrWhiteSpace($dbPort)) { $dbPort = "5432" }

# Create .env file content
$envContent = @"
# Django Settings
SECRET_KEY=django-insecure-c@_b%-je6hcn=*mpx@qn*c2&=_hhibp^8cfok`$%bwg#+`$hda!+
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1,10.0.2.2

# PostgreSQL Database Configuration
DATABASE_NAME=$dbName
DATABASE_USER=$dbUser
DATABASE_PASSWORD=$dbPasswordPlain
DATABASE_HOST=$dbHost
DATABASE_PORT=$dbPort

# Apify Configuration (Optional)
APIFY_API_TOKEN=
APIFY_ACTOR_ID=apify/instagram-scraper

# Celery Configuration (Optional)
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0
"@

# Write .env file
$envContent | Out-File -FilePath .env -Encoding utf8 -NoNewline

Write-Host ""
Write-Host "✅ .env file created successfully!" -ForegroundColor Green
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Cyan
Write-Host "1. Verify the .env file was created correctly"
Write-Host "2. Activate virtual environment: .\venv\Scripts\Activate.ps1"
Write-Host "3. Test database connection: python manage.py dbshell"
Write-Host "4. Start the server: python manage.py runserver 0.0.0.0:8000"
Write-Host ""

