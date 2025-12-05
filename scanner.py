import os
import winreg
from pathlib import Path
from typing import List
from models import AppItem, FolderItem

def get_folder_size_gb(path: str) -> float:
    """Calculate folder size in GB recursively."""
    total_size = 0
    try:
        if not os.path.exists(path):
            return 0.0
        for dirpath, dirnames, filenames in os.walk(path):
            for f in filenames:
                fp = os.path.join(dirpath, f)
                # skip if it is symbolic link
                if os.path.islink(fp):
                    continue
                try:
                    total_size += os.path.getsize(fp)
                except OSError:
                    pass
    except Exception:
         # Permission errors or locked files
         pass
    return round(total_size / (1024 ** 3), 2)

def scan_installed_apps() -> List[AppItem]:
    """Scan Registry for installed apps."""
    apps = []
    roots = [
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall"),
        (winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Uninstall")
    ]

    for hive, subkey in roots:
        try:
            with winreg.OpenKey(hive, subkey) as key:
                count = winreg.QueryInfoKey(key)[0]
                for i in range(count):
                    try:
                        subkey_name = winreg.EnumKey(key, i)
                        with winreg.OpenKey(key, subkey_name) as app_key:
                            try:
                                name = winreg.QueryValueEx(app_key, "DisplayName")[0]
                                try:
                                    install_loc = winreg.QueryValueEx(app_key, "InstallLocation")[0]
                                except FileNotFoundError:
                                    install_loc = None
                                
                                # Sometimes InstallLocation is empty string
                                if install_loc and len(install_loc) > 3:
                                    # Normalize
                                    install_loc = os.path.normpath(install_loc)
                                    
                                    # Check if on C:
                                    if install_loc.lower().startswith("c:") and os.path.exists(install_loc):
                                        # Deduplicate by path
                                        if not any(a.path == install_loc for a in apps):
                                            size = get_folder_size_gb(install_loc)
                                            apps.append(AppItem(
                                                name=name,
                                                path=install_loc,
                                                size_gb=size,
                                                type="Program",
                                                source="registry"
                                            ))
                            except FileNotFoundError:
                                pass # Missing DisplayName
                    except OSError:
                        pass
        except OSError:
            pass # Permissions or key missing

    return apps

def scan_folders() -> List[FolderItem]:
    """Scan specific heavy folders."""
    items = []
    user_profile = os.environ.get("USERPROFILE")
    if not user_profile:
        return items

    scan_targets = [
        os.path.join(user_profile, "AppData", "Local"),
        os.path.join(user_profile, "AppData", "Roaming"),
        # We can add more scan targets here if needed
    ]

    for root_dir in scan_targets:
        if os.path.exists(root_dir):
            try:
                # List top level directories
                for name in os.listdir(root_dir):
                    full_path = os.path.join(root_dir, name)
                    if os.path.isdir(full_path) and not os.path.islink(full_path):
                        size = get_folder_size_gb(full_path)
                        if size > 0.1: # Only show substantial folders > 100MB
                            items.append(FolderItem(
                                path=full_path,
                                size_gb=size,
                                source="folder_scan"
                            ))
            except PermissionError:
                pass

    return items
