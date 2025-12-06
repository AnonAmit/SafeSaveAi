from dataclasses import dataclass, field
from typing import Optional

@dataclass
class AppItem:
    name: str
    path: str
    size_gb: float
    type: str  # 'AppData', 'Program Files', 'User', etc.
    source: str = 'registry'  # 'registry' or 'scan'
    
    @property
    def key(self):
        return f"{self.path}"

@dataclass
class ClassifiedItem:
    item: AppItem
    category: str  # "SAFE", "REINSTALL", "FORBIDDEN"
    reason: str

@dataclass
class MovePlan:
    item: AppItem
    source_path: str
    target_path: str
    status: str = "PENDING"  # PENDING, DONE, FAILED, SKIPPED

@dataclass
class FolderItem:
    path: str
    size_gb: float
    source: str = 'scan'

    @property
    def name(self):
        import os
        return os.path.basename(self.path)

    @property
    def type(self):
        return "Folder"
