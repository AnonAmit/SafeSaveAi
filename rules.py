import re
import os
from models import AppItem, FolderItem, ClassifiedItem

# Hard-coded rules for FORBIDDEN paths
FORBIDDEN_PATTERNS = [
    r"^C:\\Windows",
    r"^C:\\ProgramData",
    r"^C:\\Program Files\\WindowsApps",
    r"^C:\\Program Files \(x86\)\\Microsoft",
    r"^C:\\Program Files\\Microsoft",
    r"\\Microsoft Office",
    r"\\Drivers",
    r"\\NVIDIA",
    r"\\Intel",
    r"\\AMD",
    r"\\Common Files",
    r"\\Antivirus",
    r"\\Avast",
    r"\\AVG",
    r"\\Kaspersky",
    r"\\Norton",
    r"\\McAfee",
    r"\\Sophos",
    r"\\Bitdefender",
    r"\\dotnet",  # System runtimes
    r"\\vcredist"
]

# SAFE candidates (User Data, Games, known independent caches)
SAFE_PATTERNS = [
    r"\\AppData\\Local\\[^\\]+$", # Top level folders in AppData Local often safe, but check carefully
    r"\\AppData\\Roaming\\[^\\]+$",
    r"\\.minecraft",
    r"\\.gradle",
    r"\\.m2",
    r"\\Steam\\steamapps\\common", # Steam games generally movable but better via Steam
    # We will be conservative: If it looks like user data or standalone app content
]

def is_junction(path: str) -> bool:
    """Check if path is a directory junction."""
    try:
        if hasattr(os.path, "isjunction"):
             return os.path.isjunction(path)
        return False # Fallback if not supported (though we know it is on 3.13)
    except:
        return False

def is_forbidden(path: str) -> str:
    """Check if path matches any FORBIDDEN pattern. Returns reason or None."""
    # Normalize path for comparison
    norm_path = os.path.normpath(path)
    
    # Check drive - must be C:
    if not norm_path.lower().startswith("c:"):
         # Technically if it's not on C, we don't need to move it, but logic says we scan C.
         # If scanning D, it's not forbidden but maybe 'SKIPPED'.
         pass

    for pattern in FORBIDDEN_PATTERNS:
        if re.search(pattern, norm_path, re.IGNORECASE):
            return f"Matches forbidden pattern: {pattern}"
            
    # Explicit system check
    if "system32" in norm_path.lower():
        return "System directory"
        
    return None

def classify_item(item: AppItem | FolderItem) -> ClassifiedItem:
    path = item.path
    if not path:
        return ClassifiedItem(item, "FORBIDDEN", "No path provided")

    # 0. Check MOVED (Junction)
    if is_junction(path):
        return ClassifiedItem(item, "MOVED", "Already moved (Junction detected)")

    # 1. Check FORBIDDEN
    forbidden_reason = is_forbidden(path)
    if forbidden_reason:
        return ClassifiedItem(item, "FORBIDDEN", forbidden_reason)

    # 2. Check REINSTALL candidates
    # Apps in Program Files that are NOT forbidden are generally REINSTALL
    # because moving them might break registry links or services without a proper reinstall/move tool.
    # However, if it's a simple portable app folder manually placed, it *might* be legal, but we default to REINSTALL for safety.
    is_program_files = "Program Files" in path
    
    # 3. Check SAFE
    # Explicit safe zones:
    # Users/<user>/AppData/...
    # Users/<user>/... (except system hidden ones)
    
    cmd_lower = path.lower()
    if "\\users\\" in cmd_lower:
        if "\\appdata\\" in cmd_lower:
            # Check if it is strictly Microsoft
            if "microsoft" in cmd_lower and "visualstudio" not in cmd_lower and "vscode" not in cmd_lower:
                 # Be careful with AppData/Local/Microsoft
                 return ClassifiedItem(item, "REINSTALL", "Microsoft AppData folder - high risk")
            return ClassifiedItem(item, "SAFE", "User AppData folder")
        
        # Other user folders like .minecraft, .vscode match here
        if os.path.basename(path).startswith("."):
             return ClassifiedItem(item, "SAFE", "Dot-folder in User profile")
             
    # If it's a game in a known library path (simple heuristic)
    if "steamapps\\common" in cmd_lower:
         return ClassifiedItem(item, "SAFE", "Steam Game folder")
    
    if is_program_files:
        return ClassifiedItem(item, "REINSTALL", "Installed in Program Files - Move might break shortcuts/registry")

    # Default to REINSTALL if unsure
    return ClassifiedItem(item, "REINSTALL", "Unknown category - Safer to reinstall")
