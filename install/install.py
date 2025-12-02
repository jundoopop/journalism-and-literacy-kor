#!/usr/bin/env python3
"""
Highright Native Messaging Host Installer
Installs native messaging host for Chrome extension on Windows and macOS
"""

import os
import sys
import json
import shutil
import platform
import subprocess
from pathlib import Path
from typing import Optional

# Colors for terminal output
class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'

def print_header(text):
    print(f"\n{Colors.HEADER}{Colors.BOLD}{'='*60}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{text:^60}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{'='*60}{Colors.ENDC}\n")

def print_success(text):
    print(f"{Colors.OKGREEN}✓ {text}{Colors.ENDC}")

def print_error(text):
    print(f"{Colors.FAIL}✗ {text}{Colors.ENDC}")

def print_warning(text):
    print(f"{Colors.WARNING}⚠ {text}{Colors.ENDC}")

def print_info(text):
    print(f"{Colors.OKCYAN}ℹ {text}{Colors.ENDC}")


# ============================================
# Configuration
# ============================================

HOST_NAME = "com.highright.analyzer"
EXTENSION_ID_PLACEHOLDER = "{{EXTENSION_ID}}"  # Will be replaced with actual ID


# ============================================
# System Detection
# ============================================

def get_os_type():
    """Detect operating system"""
    system = platform.system()
    if system == "Windows":
        return "windows"
    elif system == "Darwin":
        return "macos"
    elif system == "Linux":
        return "linux"
    else:
        return "unknown"


def get_chrome_manifest_dir():
    """Get Chrome native messaging manifest directory for current OS"""
    os_type = get_os_type()

    if os_type == "windows":
        # HKEY_CURRENT_USER\SOFTWARE\Google\Chrome\NativeMessagingHosts\
        # Manifest will be registered via registry
        return None
    elif os_type == "macos":
        return Path.home() / "Library" / "Application Support" / "Google" / "Chrome" / "NativeMessagingHosts"
    elif os_type == "linux":
        return Path.home() / ".config" / "google-chrome" / "NativeMessagingHosts"
    else:
        return None


def get_install_dir():
    """Get installation directory for native host"""
    os_type = get_os_type()

    if os_type == "windows":
        # AppData\Local\Highright
        return Path(os.getenv('LOCALAPPDATA')) / "Highright"
    elif os_type == "macos":
        # ~/Library/Application Support/Highright
        return Path.home() / "Library" / "Application Support" / "Highright"
    elif os_type == "linux":
        # ~/.local/share/highright
        return Path.home() / ".local" / "share" / "highright"
    else:
        return None


# ============================================
# API Key Management
# ============================================

def prompt_api_key() -> Optional[str]:
    """Prompt user for Gemini API key"""
    print_info("Gemini API key is required for article analysis.")
    print_info("Get your API key from: https://aistudio.google.com/app/apikey")
    print()

    api_key = input(f"{Colors.BOLD}Enter your GEMINI_API_KEY (or press Enter to skip): {Colors.ENDC}").strip()

    if not api_key:
        print_warning("No API key provided. You'll need to set it later.")
        return None

    return api_key


def save_api_key(api_key: str) -> bool:
    """Save API key to secure storage"""
    try:
        import keyring
        keyring.set_password('highright', 'gemini_api_key', api_key)
        print_success("API key saved securely to system keychain")
        return True
    except ImportError:
        print_warning("keyring library not available, trying environment variable...")

        # Fallback: save to .env file
        try:
            env_file = get_install_dir() / ".env"
            env_file.parent.mkdir(parents=True, exist_ok=True)

            with open(env_file, 'w') as f:
                f.write(f"GEMINI_API_KEY={api_key}\n")

            print_success(f"API key saved to {env_file}")
            return True
        except Exception as e:
            print_error(f"Failed to save API key: {e}")
            return False
    except Exception as e:
        print_error(f"Failed to save API key: {e}")
        return False


# ============================================
# Installation Functions
# ============================================

def check_python_version():
    """Check if Python version is compatible"""
    print_info("Checking Python version...")

    major, minor = sys.version_info[:2]

    if major < 3 or (major == 3 and minor < 7):
        print_error(f"Python 3.7+ required, found {major}.{minor}")
        return False

    print_success(f"Python {major}.{minor} detected")
    return True


def install_dependencies():
    """Install required Python packages"""
    print_info("Installing required Python packages...")

    # Get requirements.txt path
    script_dir = Path(__file__).parent.parent
    requirements_file = script_dir / "requirements.txt"

    if not requirements_file.exists():
        print_error(f"requirements.txt not found at {requirements_file}")
        return False

    try:
        subprocess.check_call([
            sys.executable, "-m", "pip", "install", "-r", str(requirements_file)
        ], stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)

        print_success("Dependencies installed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print_error(f"Failed to install dependencies: {e}")
        return False


def copy_files(install_dir: Path):
    """Copy native host and scripts to installation directory"""
    print_info(f"Copying files to {install_dir}...")

    # Create installation directory
    install_dir.mkdir(parents=True, exist_ok=True)

    # Get source directory
    script_dir = Path(__file__).parent.parent

    # Files to copy
    files_to_copy = [
        ("scripts/native_host.py", "native_host.py"),
        ("scripts/gemini_handler.py", "gemini_handler.py"),
        ("scripts/crawler_unified.py", "crawler_unified.py"),
        ("scripts/crawler_chosun.py", "crawler_chosun.py"),
        ("scripts/crawler_joongang.py", "crawler_joongang.py"),
    ]

    try:
        for src_rel, dst_name in files_to_copy:
            src = script_dir / src_rel
            dst = install_dir / dst_name

            if src.exists():
                shutil.copy2(src, dst)
                print_success(f"Copied {dst_name}")
            else:
                print_warning(f"File not found: {src}")

        return True
    except Exception as e:
        print_error(f"Failed to copy files: {e}")
        return False


def create_launcher_script(install_dir: Path):
    """Create launcher script for native host"""
    os_type = get_os_type()

    if os_type == "windows":
        # Create .bat launcher
        launcher_path = install_dir / "native_host.bat"
        python_exe = sys.executable
        native_host = install_dir / "native_host.py"

        launcher_content = f'@echo off\n"{python_exe}" "{native_host}" %*\n'

        with open(launcher_path, 'w') as f:
            f.write(launcher_content)

        print_success(f"Created launcher: {launcher_path}")
        return launcher_path

    else:
        # macOS/Linux: make native_host.py executable and create shebang wrapper
        launcher_path = install_dir / "native_host.sh"
        python_exe = sys.executable
        native_host = install_dir / "native_host.py"

        launcher_content = f'#!/bin/bash\n"{python_exe}" "{native_host}" "$@"\n'

        with open(launcher_path, 'w') as f:
            f.write(launcher_content)

        # Make executable
        launcher_path.chmod(0o755)

        print_success(f"Created launcher: {launcher_path}")
        return launcher_path


def create_manifest(manifest_dir: Path, launcher_path: Path, extension_id: str):
    """Create native messaging manifest"""
    print_info(f"Creating native messaging manifest...")

    # Ensure manifest directory exists
    manifest_dir.mkdir(parents=True, exist_ok=True)

    # Create manifest
    manifest_path = manifest_dir / f"{HOST_NAME}.json"

    manifest = {
        "name": HOST_NAME,
        "description": "Highright Article Analyzer - Literacy Enhancement Tool",
        "path": str(launcher_path.absolute()),
        "type": "stdio",
        "allowed_origins": [
            f"chrome-extension://{extension_id}/"
        ]
    }

    try:
        with open(manifest_path, 'w') as f:
            json.dump(manifest, f, indent=2)

        print_success(f"Created manifest: {manifest_path}")
        return manifest_path
    except Exception as e:
        print_error(f"Failed to create manifest: {e}")
        return None


def register_windows_manifest(manifest_path: Path):
    """Register manifest in Windows registry"""
    print_info("Registering in Windows registry...")

    try:
        import winreg

        # HKEY_CURRENT_USER\SOFTWARE\Google\Chrome\NativeMessagingHosts\com.highright.analyzer
        key_path = r"SOFTWARE\Google\Chrome\NativeMessagingHosts\\" + HOST_NAME

        # Create registry key
        key = winreg.CreateKey(winreg.HKEY_CURRENT_USER, key_path)
        winreg.SetValue(key, "", winreg.REG_SZ, str(manifest_path))
        winreg.CloseKey(key)

        print_success("Registered in Windows registry")
        return True
    except ImportError:
        print_error("winreg module not available (not on Windows?)")
        return False
    except Exception as e:
        print_error(f"Failed to register in registry: {e}")
        return False


def prompt_extension_id() -> str:
    """Prompt for Chrome extension ID"""
    print()
    print_info("Chrome Extension ID is required for native messaging.")
    print_info("To get your extension ID:")
    print_info("  1. Open Chrome and go to chrome://extensions/")
    print_info("  2. Enable 'Developer mode' (top right)")
    print_info("  3. Find 'Highright' extension and copy its ID")
    print()

    while True:
        ext_id = input(f"{Colors.BOLD}Enter Extension ID (or 'skip' to use placeholder): {Colors.ENDC}").strip()

        if ext_id.lower() == 'skip':
            print_warning("Using placeholder - you'll need to update the manifest later")
            return EXTENSION_ID_PLACEHOLDER

        if len(ext_id) == 32 and ext_id.isalnum():
            return ext_id
        else:
            print_error("Invalid extension ID (must be 32 alphanumeric characters)")


# ============================================
# Main Installation
# ============================================

def main():
    """Main installation process"""
    print_header("Highright Native Messaging Host Installer")

    # Detect OS
    os_type = get_os_type()
    print_info(f"Operating System: {os_type}")

    if os_type == "unknown":
        print_error("Unsupported operating system")
        return 1

    # Check Python version
    if not check_python_version():
        return 1

    # Install dependencies
    print()
    if not install_dependencies():
        print_error("Installation failed during dependency installation")
        return 1

    # Prompt for API key
    print()
    api_key = prompt_api_key()

    # Prompt for extension ID
    extension_id = prompt_extension_id()

    # Get installation directories
    install_dir = get_install_dir()
    manifest_dir = get_chrome_manifest_dir()

    if not install_dir:
        print_error("Could not determine installation directory")
        return 1

    print()
    print_info(f"Installation directory: {install_dir}")
    if manifest_dir:
        print_info(f"Manifest directory: {manifest_dir}")

    # Copy files
    print()
    if not copy_files(install_dir):
        print_error("Installation failed during file copy")
        return 1

    # Save API key
    if api_key:
        print()
        save_api_key(api_key)

    # Create launcher
    print()
    launcher_path = create_launcher_script(install_dir)

    # Create and register manifest
    print()
    if os_type == "windows":
        # Windows: create manifest in install dir and register in registry
        manifest_path = install_dir / f"{HOST_NAME}.json"

        manifest = {
            "name": HOST_NAME,
            "description": "Highright Article Analyzer - Literacy Enhancement Tool",
            "path": str(launcher_path.absolute()),
            "type": "stdio",
            "allowed_origins": [
                f"chrome-extension://{extension_id}/"
            ]
        }

        with open(manifest_path, 'w') as f:
            json.dump(manifest, f, indent=2)

        print_success(f"Created manifest: {manifest_path}")

        if not register_windows_manifest(manifest_path):
            print_error("Failed to register in Windows registry")
            print_info("You may need to run this installer as administrator")
            return 1

    else:
        # macOS/Linux: create manifest in Chrome directory
        if not manifest_dir:
            print_error("Could not determine Chrome manifest directory")
            return 1

        manifest_path = create_manifest(manifest_dir, launcher_path, extension_id)
        if not manifest_path:
            print_error("Failed to create manifest")
            return 1

    # Installation complete
    print()
    print_header("Installation Complete!")

    print_success("Native messaging host installed successfully")
    print()
    print_info("Next steps:")
    print_info("  1. Install/reload the Highright Chrome extension")
    print_info("  2. Visit a supported news article (chosun.com, hani.co.kr, etc.)")
    print_info("  3. Extension will automatically highlight sentences")
    print()

    if extension_id == EXTENSION_ID_PLACEHOLDER:
        print_warning("Remember to update the manifest with your actual extension ID!")
        print_info(f"Manifest location: {manifest_path}")

    print()
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print()
        print_warning("Installation cancelled by user")
        sys.exit(1)
    except Exception as e:
        print()
        print_error(f"Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
