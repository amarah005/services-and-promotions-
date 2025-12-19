#!/usr/bin/env python3
"""
System Health Check for BuyVaultHub Scrapers
Checks all dependencies, files, and configurations
"""

import os
import sys
import importlib
from pathlib import Path
from typing import Dict, List, Any

class ScrapingSystemHealthCheck:
    """Comprehensive health check for the scraping system"""
    
    def __init__(self):
        self.scrapers_dir = Path(__file__).parent
        self.results = {
            'overall_status': 'UNKNOWN',
            'checks': {},
            'errors': [],
            'warnings': [],
            'recommendations': []
        }
    
    def check_python_version(self):
        """Check Python version compatibility"""
        version = sys.version_info
        if version.major == 3 and version.minor >= 8:
            self.results['checks']['python_version'] = {
                'status': 'PASS',
                'version': f'{version.major}.{version.minor}.{version.micro}',
                'message': 'Python version is compatible'
            }
        else:
            self.results['checks']['python_version'] = {
                'status': 'FAIL',
                'version': f'{version.major}.{version.minor}.{version.micro}',
                'message': 'Python 3.8+ required'
            }
            self.results['errors'].append('Python version too old')
    
    def check_dependencies(self):
        """Check all required dependencies"""
        required_packages = {
            'selenium': 'Web automation',
            'bs4': 'HTML parsing (beautifulsoup4)',
            'requests': 'HTTP requests',
            'pandas': 'Data manipulation',
            'numpy': 'Numerical operations',
            'aiohttp': 'Async HTTP requests',
            'tensorflow': 'AI/ML for categorization',
            'sklearn': 'Machine learning utilities (scikit-learn)',
            'lxml': 'XML/HTML parsing',
            'fake_useragent': 'User agent rotation (fake-useragent)',
            'webdriver_manager': 'ChromeDriver management (webdriver-manager)'
        }
        
        missing_packages = []
        available_packages = []
        
        for package, description in required_packages.items():
            try:
                importlib.import_module(package)
                available_packages.append(package)
            except ImportError:
                missing_packages.append((package, description))
        
        if missing_packages:
            self.results['checks']['dependencies'] = {
                'status': 'FAIL',
                'available': len(available_packages),
                'missing': len(missing_packages),
                'message': f'Missing {len(missing_packages)} packages'
            }
            self.results['errors'].append(f'Missing packages: {[p[0] for p in missing_packages]}')
        else:
            self.results['checks']['dependencies'] = {
                'status': 'PASS',
                'available': len(available_packages),
                'missing': 0,
                'message': 'All dependencies available'
            }
    
    def check_core_files(self):
        """Check if all core scraper files exist"""
        core_files = [
            'base_scraper.py',
            'scraper_factory.py',
            'intelligent_scraper_runner.py',
            'website_structure_analyzer.py',
            'scraper_config_generator.py',
            'ai_category_classifier.py',
            'data_processor.py',
            'validation.py',
            'configs/platforms.json'
        ]
        
        missing_files = []
        existing_files = []
        
        for file_path in core_files:
            full_path = self.scrapers_dir / file_path
            if full_path.exists():
                existing_files.append(file_path)
            else:
                missing_files.append(file_path)
        
        if missing_files:
            self.results['checks']['core_files'] = {
                'status': 'FAIL',
                'existing': len(existing_files),
                'missing': len(missing_files),
                'message': f'Missing {len(missing_files)} core files'
            }
            self.results['errors'].append(f'Missing files: {missing_files}')
        else:
            self.results['checks']['core_files'] = {
                'status': 'PASS',
                'existing': len(existing_files),
                'missing': 0,
                'message': 'All core files present'
            }
    
    def check_chromedriver(self):
        """Check ChromeDriver availability"""
        driver_name = "chromedriver.exe" if sys.platform == "win32" else "chromedriver"
        driver_path = self.scrapers_dir / driver_name
        
        # Check if webdriver-manager is available
        try:
            import webdriver_manager
            webdriver_manager_available = True
        except ImportError:
            webdriver_manager_available = False
        
        if driver_path.exists():
            self.results['checks']['chromedriver'] = {
                'status': 'PASS',
                'path': str(driver_path),
                'message': 'ChromeDriver found locally'
            }
        elif webdriver_manager_available:
            self.results['checks']['chromedriver'] = {
                'status': 'PASS',
                'path': 'webdriver-manager',
                'message': 'ChromeDriver will be auto-downloaded via webdriver-manager'
            }
        else:
            self.results['checks']['chromedriver'] = {
                'status': 'WARN',
                'path': 'Not found',
                'message': 'ChromeDriver not found and webdriver-manager not available'
            }
            self.results['warnings'].append('ChromeDriver setup may fail')
    
    def check_configuration(self):
        """Check configuration files"""
        config_file = self.scrapers_dir / 'configs' / 'platforms.json'
        
        if config_file.exists():
            try:
                import json
                with open(config_file, 'r') as f:
                    config = json.load(f)
                
                if 'dynamic' in config:
                    self.results['checks']['configuration'] = {
                        'status': 'PASS',
                        'platforms': list(config.keys()),
                        'message': 'Configuration file valid'
                    }
                else:
                    self.results['checks']['configuration'] = {
                        'status': 'WARN',
                        'platforms': list(config.keys()),
                        'message': 'No dynamic platform config found'
                    }
                    self.results['warnings'].append('Missing dynamic platform configuration')
            except Exception as e:
                self.results['checks']['configuration'] = {
                    'status': 'FAIL',
                    'error': str(e),
                    'message': 'Configuration file invalid'
                }
                self.results['errors'].append(f'Invalid configuration: {e}')
        else:
            self.results['checks']['configuration'] = {
                'status': 'FAIL',
                'message': 'Configuration file missing'
            }
            self.results['errors'].append('Configuration file missing')
    
    def check_imports(self):
        """Check if all modules can be imported"""
        modules_to_check = [
            'base_scraper',
            'scraper_factory',
            'intelligent_scraper_runner',
            'website_structure_analyzer',
            'scraper_config_generator',
            'ai_category_classifier',
            'data_processor',
            'validation'
        ]
        
        failed_imports = []
        successful_imports = []
        
        # Add scrapers directory to path
        if str(self.scrapers_dir) not in sys.path:
            sys.path.insert(0, str(self.scrapers_dir))
        
        for module in modules_to_check:
            try:
                importlib.import_module(module)
                successful_imports.append(module)
            except Exception as e:
                failed_imports.append((module, str(e)))
        
        if failed_imports:
            self.results['checks']['imports'] = {
                'status': 'FAIL',
                'successful': len(successful_imports),
                'failed': len(failed_imports),
                'message': f'{len(failed_imports)} modules failed to import'
            }
            self.results['errors'].append(f'Import failures: {[m[0] for m in failed_imports]}')
        else:
            self.results['checks']['imports'] = {
                'status': 'PASS',
                'successful': len(successful_imports),
                'failed': 0,
                'message': 'All modules import successfully'
            }
    
    def generate_recommendations(self):
        """Generate recommendations based on check results"""
        if self.results['errors']:
            self.results['recommendations'].append("Install missing dependencies: pip install -r requirements.txt")
            self.results['recommendations'].append("Run setup_chromedriver.py to install ChromeDriver")
        
        if self.results['warnings']:
            self.results['recommendations'].append("Review configuration files for completeness")
        
        if not self.results['errors'] and not self.results['warnings']:
            self.results['recommendations'].append("System is ready for scraping!")
            self.results['recommendations'].append("Run intelligent scraper to test functionality")
    
    def run_all_checks(self):
        """Run all health checks"""
        print("🔍 BuyVaultHub Scraping System Health Check")
        print("=" * 50)
        
        self.check_python_version()
        self.check_dependencies()
        self.check_core_files()
        self.check_chromedriver()
        self.check_configuration()
        self.check_imports()
        
        # Determine overall status
        if self.results['errors']:
            self.results['overall_status'] = 'FAIL'
        elif self.results['warnings']:
            self.results['overall_status'] = 'WARN'
        else:
            self.results['overall_status'] = 'PASS'
        
        self.generate_recommendations()
        
        return self.results
    
    def print_results(self):
        """Print formatted results"""
        print(f"\n📊 Overall Status: {self.results['overall_status']}")
        print("=" * 50)
        
        for check_name, result in self.results['checks'].items():
            status_emoji = "✅" if result['status'] == 'PASS' else "⚠️" if result['status'] == 'WARN' else "❌"
            print(f"{status_emoji} {check_name.replace('_', ' ').title()}: {result['message']}")
        
        if self.results['errors']:
            print(f"\n❌ Errors ({len(self.results['errors'])}):")
            for error in self.results['errors']:
                print(f"  • {error}")
        
        if self.results['warnings']:
            print(f"\n⚠️  Warnings ({len(self.results['warnings'])}):")
            for warning in self.results['warnings']:
                print(f"  • {warning}")
        
        if self.results['recommendations']:
            print(f"\n💡 Recommendations:")
            for rec in self.results['recommendations']:
                print(f"  • {rec}")

def main():
    """Main health check function"""
    # Suppress TensorFlow warnings for cleaner output
    import os
    os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'
    os.environ['TF_ENABLE_ONEDNN_OPTS'] = '0'
    
    health_check = ScrapingSystemHealthCheck()
    results = health_check.run_all_checks()
    health_check.print_results()
    
    # Exit with appropriate code
    if results['overall_status'] == 'FAIL':
        sys.exit(1)
    elif results['overall_status'] == 'WARN':
        sys.exit(2)
    else:
        sys.exit(0)

if __name__ == "__main__":
    main()
