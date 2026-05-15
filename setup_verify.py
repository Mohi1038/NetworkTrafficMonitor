#!/usr/bin/env python3
"""
Network Traffic Monitor - Setup Verification Script
Checks if all requirements are met before running the application
"""

import sys
import os
import subprocess
from pathlib import Path

class Colors:
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BLUE = '\033[94m'
    RESET = '\033[0m'

def print_header():
    print(f"\n{Colors.BLUE}{'='*60}{Colors.RESET}")
    print(f"{Colors.BLUE}Network Traffic Monitor - Setup Verification{Colors.RESET}")
    print(f"{Colors.BLUE}{'='*60}{Colors.RESET}\n")

def check_python():
    """Check if Python 3.8+ is installed"""
    try:
        version = sys.version_info
        if version.major >= 3 and version.minor >= 8:
            print(f"{Colors.GREEN}✓{Colors.RESET} Python {version.major}.{version.minor}.{version.micro}")
            return True
        else:
            print(f"{Colors.RED}✗{Colors.RESET} Python version is {version.major}.{version.minor}, need 3.8+")
            return False
    except Exception as e:
        print(f"{Colors.RED}✗{Colors.RESET} Error checking Python: {e}")
        return False

def check_node():
    """Check if Node.js is installed"""
    try:
        result = subprocess.run(['node', '--version'], capture_output=True, text=True)
        if result.returncode == 0:
            version = result.stdout.strip()
            print(f"{Colors.GREEN}✓{Colors.RESET} Node.js {version}")
            return True
        else:
            print(f"{Colors.RED}✗{Colors.RESET} Node.js not found")
            return False
    except FileNotFoundError:
        print(f"{Colors.RED}✗{Colors.RESET} Node.js is not installed")
        return False

def check_npm():
    """Check if npm is installed"""
    try:
        result = subprocess.run(['npm', '--version'], capture_output=True, text=True)
        if result.returncode == 0:
            version = result.stdout.strip()
            print(f"{Colors.GREEN}✓{Colors.RESET} npm {version}")
            return True
        else:
            print(f"{Colors.RED}✗{Colors.RESET} npm not found")
            return False
    except FileNotFoundError:
        print(f"{Colors.RED}✗{Colors.RESET} npm is not installed")
        return False

def check_privileges():
    """Check if running with proper privileges"""
    if os.name == 'posix':  # Linux/macOS
        if os.geteuid() != 0:
            print(f"{Colors.YELLOW}⚠{Colors.RESET} Not running as root (required for packet capture)")
            print(f"  → Run with: {Colors.BLUE}sudo python3 setup_verify.py{Colors.RESET}")
            return False
        else:
            print(f"{Colors.GREEN}✓{Colors.RESET} Running with root privileges")
            return True
    else:
        print(f"{Colors.GREEN}✓{Colors.RESET} Windows detected (will use administrator when needed)")
        return True

def check_libpcap():
    """Check if libpcap is installed (Linux/macOS)"""
    if os.name != 'posix':
        return True
    
    try:
        result = subprocess.run(['pkg-config', '--exists', 'libpcap'], capture_output=True)
        if result.returncode == 0:
            print(f"{Colors.GREEN}✓{Colors.RESET} libpcap found")
            return True
        else:
            print(f"{Colors.YELLOW}⚠{Colors.RESET} libpcap not found")
            if sys.platform == 'darwin':
                print(f"  → Install with: {Colors.BLUE}brew install libpcap{Colors.RESET}")
            else:
                print(f"  → Install with: {Colors.BLUE}sudo apt-get install libpcap-dev{Colors.RESET}")
            return False
    except FileNotFoundError:
        print(f"{Colors.YELLOW}⚠{Colors.RESET} pkg-config not found (libpcap may not be installed)")
        return False

def check_directory_structure():
    """Check if required directories exist"""
    required_dirs = [
        'backend',
        'frontend',
        'backend/ml_models',
    ]
    
    all_exist = True
    for dir_name in required_dirs:
        if Path(dir_name).exists():
            print(f"{Colors.GREEN}✓{Colors.RESET} Directory: {dir_name}")
        else:
            print(f"{Colors.RED}✗{Colors.RESET} Missing directory: {dir_name}")
            all_exist = False
    
    return all_exist

def check_ml_models():
    """Check if ML model files exist"""
    model_files = [
        'backend/ml_models/rf_model.pkl',
        'backend/ml_models/scaler.pkl',
        'backend/ml_models/pca.pkl',
    ]
    
    all_exist = True
    for model_file in model_files:
        if Path(model_file).exists():
            size_mb = Path(model_file).stat().st_size / (1024 * 1024)
            print(f"{Colors.GREEN}✓{Colors.RESET} ML Model: {model_file} ({size_mb:.1f} MB)")
        else:
            print(f"{Colors.YELLOW}⚠{Colors.RESET} Missing ML model: {model_file}")
            all_exist = False
    
    return all_exist

def check_config_files():
    """Check if configuration files exist"""
    files = {
        '.env': 'User configuration',
        'README.md': 'Documentation',
        'QUICKSTART.md': 'Quick start guide',
    }
    
    all_exist = True
    for file_name, description in files.items():
        if Path(file_name).exists():
            print(f"{Colors.GREEN}✓{Colors.RESET} {description}: {file_name}")
        else:
            print(f"{Colors.YELLOW}⚠{Colors.RESET} Missing {description}: {file_name}")
            all_exist = False
    
    return all_exist

def check_launcher_scripts():
    """Check if launcher scripts exist"""
    scripts = {
        'run_network_monitor.sh': 'Linux/macOS launcher',
        'run_network_monitor.bat': 'Windows launcher',
    }
    
    all_exist = True
    for script_name, description in scripts.items():
        if Path(script_name).exists():
            print(f"{Colors.GREEN}✓{Colors.RESET} {description}: {script_name}")
        else:
            print(f"{Colors.YELLOW}⚠{Colors.RESET} Missing {description}: {script_name}")
            all_exist = False
    
    return all_exist

def check_ports():
    """Check if required ports are available"""
    ports_to_check = [
        (5000, 'Backend API'),
        (3000, 'Frontend (if dev mode)'),
    ]
    
    import socket
    results = []
    
    for port, name in ports_to_check:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            result = sock.connect_ex(('127.0.0.1', port))
            sock.close()
            
            if result == 0:
                print(f"{Colors.YELLOW}⚠{Colors.RESET} Port {port} is in use ({name})")
                print(f"  → Kill process: {Colors.BLUE}lsof -i :{port} | grep LISTEN{Colors.RESET}")
                results.append(False)
            else:
                print(f"{Colors.GREEN}✓{Colors.RESET} Port {port} is available ({name})")
                results.append(True)
        except Exception as e:
            print(f"{Colors.YELLOW}⚠{Colors.RESET} Could not check port {port}: {e}")
            results.append(True)  # Assume it's OK if we can't check
    
    return all(results)

def main():
    print_header()
    
    results = {}
    
    print(f"{Colors.BLUE}[1/7] Checking System Requirements...{Colors.RESET}")
    results['python'] = check_python()
    results['node'] = check_node()
    results['npm'] = check_npm()
    
    print(f"\n{Colors.BLUE}[2/7] Checking Privileges...{Colors.RESET}")
    results['privileges'] = check_privileges()
    
    print(f"\n{Colors.BLUE}[3/7] Checking System Libraries...{Colors.RESET}")
    results['libpcap'] = check_libpcap()
    
    print(f"\n{Colors.BLUE}[4/7] Checking Directory Structure...{Colors.RESET}")
    results['directories'] = check_directory_structure()
    
    print(f"\n{Colors.BLUE}[5/7] Checking ML Models...{Colors.RESET}")
    results['ml_models'] = check_ml_models()
    
    print(f"\n{Colors.BLUE}[6/7] Checking Configuration Files...{Colors.RESET}")
    results['config_files'] = check_config_files()
    
    print(f"\n{Colors.BLUE}[7/7] Checking Network Ports...{Colors.RESET}")
    results['ports'] = check_ports()
    
    # Summary
    print(f"\n{Colors.BLUE}{'='*60}{Colors.RESET}")
    print(f"{Colors.BLUE}Summary{Colors.RESET}")
    print(f"{Colors.BLUE}{'='*60}{Colors.RESET}\n")
    
    required_checks = ['python', 'node', 'npm', 'directories', 'config_files', 'ports']
    optional_checks = ['privileges', 'libpcap', 'ml_models']
    
    passed = sum(1 for check in required_checks if results.get(check, False))
    failed = len(required_checks) - passed
    
    optional_passed = sum(1 for check in optional_checks if results.get(check, False))
    optional_failed = len(optional_checks) - optional_passed
    
    print(f"Required Checks: {Colors.GREEN}{passed}/{len(required_checks)} passed{Colors.RESET}")
    print(f"Optional Checks: {Colors.GREEN}{optional_passed}/{len(optional_checks)} passed{Colors.RESET}")
    
    if failed == 0:
        print(f"\n{Colors.GREEN}✓ All required dependencies are installed!{Colors.RESET}")
        print(f"\nYou can now run the application:")
        if os.name == 'posix':
            print(f"  {Colors.BLUE}./run_network_monitor.sh{Colors.RESET}")
        else:
            print(f"  {Colors.BLUE}run_network_monitor.bat{Colors.RESET}")
        return 0
    else:
        print(f"\n{Colors.RED}✗ Please install the missing dependencies above{Colors.RESET}")
        return 1

if __name__ == '__main__':
    sys.exit(main())
