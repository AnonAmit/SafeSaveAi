import os
from scanner import scan_folders, scan_installed_apps
from rules import classify_item
from models import FolderItem, AppItem
from storage import storage

def test_rules():
    print("\n--- Testing Rules ---")
    
    # Test Forbidden
    bad_items = [
        FolderItem(path="C:\\Windows\\System32", size_gb=1.0),
        FolderItem(path="C:\\Program Files\\Microsoft Office\\Office16", size_gb=2.0),
        FolderItem(path="C:\\ProgramData\\NVIDIA", size_gb=0.5)
    ]
    for i in bad_items:
        c = classify_item(i)
        print(f"Checking {i.path} -> {c.category} ({c.reason})")
        assert c.category == "FORBIDDEN"

    # Test Safe
    safe_path = os.path.join(os.environ["USERPROFILE"], "AppData", "Local", "TempMyApp")
    good_item = FolderItem(path=safe_path, size_gb=0.2)
    c = classify_item(good_item)
    print(f"Checking {good_item.path} -> {c.category}")
    
def test_scanner():
    print("\n--- Testing Scanner ---")
    apps = scan_installed_apps()
    print(f"Found {len(apps)} apps in Registry (on C:).")
    for a in apps[:5]:
        print(f"- {a.name} ({a.size_gb} GB) @ {a.path}")
        
    folders = scan_folders()
    print(f"Found {len(folders)} heavy folders.")
    for f in folders[:5]:
        print(f"- {f.path} ({f.size_gb} GB)")

def main():
    test_rules()
    test_scanner()
    print("\nVerification Script Finished.")

if __name__ == "__main__":
    main()
