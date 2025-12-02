#!/usr/bin/env python3
"""
Highright Native Messaging Host Uninstaller
Removes native messaging host from Windows and macOS
"""

import os
import sys
import shutil
import platform
from pathlib import Path

# Colors for terminal output
class Colors:
    HEADER = '\033[95m'
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


# ============================================
# Configuration
# ============================================

HOST_NAME = "com.highright.analyzer"


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


def get_install_dir():
    """Get installation directory"""
    os_type = get_os_type()

    if os_type == "windows":
        return Path(os.getenv('LOCALAPPDATA')) / "Highright"
    elif os_type == "macos":
        return Path.home() / "Library" / "Application Support" / "Highright"
    elif os_type == "linux":
        return Path.home() / ".local" / "share" / "highright"
    else:
        return None


def get_manifest_path():
    """Get manifest path"""
    os_type = get_os_type()

    if os_type == "windows":
        # Manifest is in registry, not a file
        return None
    elif os_type == "macos":
        manifest_dir = Path.home() / "Library" / "Application Support" / "Google" / "Chrome" / "NativeMessagingHosts"
        return manifest_dir / f"{HOST_NAME}.json"
    elif os_type == "linux":
        manifest_dir = Path.home() / ".config" / "google-chrome" / "NativeMessagingHosts"
        return manifest_dir / f"{HOST_NAME}.json"
    else:
        return None


# ============================================
# Uninstallation Functions
# ============================================

def remove_installation_dir(install_dir: Path):
    """Remove installation directory"""
    if not install_dir.exists():
        print_warning(f"Installation directory not found: {install_dir}")
        return True

    try:
        shutil.rmtree(install_dir)
        print_success(f"Removed installation directory: {install_dir}")
        return True
    except Exception as e:
        print_error(f"Failed to remove installation directory: {e}")
        return False


def remove_manifest(manifest_path: Path):
    """Remove manifest file"""
    if not manifest_path:
        return True  # Not applicable for Windows

    if not manifest_path.exists():
        print_warning(f"Manifest not found: {manifest_path}")
        return True

    try:
        manifest_path.unlink()
        print_success(f"Removed manifest: {manifest_path}")
        return True
    except Exception as e:
        print_error(f"Failed to remove manifest: {e}")
        return False


def unregister_windows_manifest():
    """Unregister from Windows registry"""
    try:
        import winreg

        key_path = r"SOFTWARE\Google\Chrome\NativeMessagingHosts\\" + HOST_NAME

        try:
            winreg.DeleteKey(winreg.HKEY_CURRENT_USER, key_path)
            print_success("Removed from Windows registry")
            return True
        except FileNotFoundError:
            print_warning("Registry key not found (already uninstalled?)")
            return True
        except Exception as e:
            print_error(f"Failed to remove from registry: {e}")
            return False

    except ImportError:
        print_error("winreg module not available (not on Windows?)")
        return False


def remove_api_key():
    """Remove API key from secure storage"""
    try:
        import keyring
        try:
            keyring.delete_password('highright', 'gemini_api_key')
            print_success("Removed API key from keychain")
            return True
        except keyring.errors.PasswordDeleteError:
            print_warning("API key not found in keychain")
            return True
        except Exception as e:
            print_warning(f"Could not remove API key from keychain: {e}")
            return True  # Not critical
    except ImportError:
        print_warning("keyring module not available, skipping API key removal")
        return True


def remove_log_files():
    """Remove log files"""
    log_dir = Path.home() / '.highright'

    if not log_dir.exists():
        return True

    try:
        shutil.rmtree(log_dir)
        print_success(f"Removed log directory: {log_dir}")
        return True
    except Exception as e:
        print_warning(f"Could not remove log directory: {e}")
        return True  # Not critical


# ============================================
# Main Uninstallation
# ============================================

def main():
    """Main uninstallation process"""
    print_header("Highright Native Messaging Host Uninstaller")

    # Detect OS
    os_type = get_os_type()

    if os_type == "unknown":
        print_error("Unsupported operating system")
        return 1

    # Confirm uninstallation
    print(f"{Colors.WARNING}This will remove Highright Native Messaging Host from your system.{Colors.ENDC}")
    print()
    response = input(f"{Colors.BOLD}Continue? (y/N): {Colors.ENDC}").strip().lower()

    if response != 'y':
        print_warning("Uninstallation cancelled")
        return 0

    print()

    # Get paths
    install_dir = get_install_dir()
    manifest_path = get_manifest_path()

    # Remove components
    success = True

    # 1. Remove installation directory
    if install_dir:
        if not remove_installation_dir(install_dir):
            success = False

    # 2. Remove manifest
    if os_type == "windows":
        if not unregister_windows_manifest():
            success = False
    else:
        if manifest_path and not remove_manifest(manifest_path):
            success = False

    # 3. Remove API key
    remove_api_key()

    # 4. Remove log files
    remove_log_files()

    # Done
    print()
    if success:
        print_header("Uninstallation Complete!")
        print_success("Highright has been removed from your system")
    else:
        print_header("Uninstallation Incomplete")
        print_warning("Some components could not be removed")
        print_warning("Please check the error messages above")

    print()
    return 0 if success else 1


if __name__ == '__main__':
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print()
        print_warning("Uninstallation cancelled by user")
        sys.exit(1)
    except Exception as e:
        print()
        print_error(f"Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
