import os
import shutil
from typing import List, Tuple
from logger import get_logger

log = get_logger("Cleaner")

class NvidiaCleaner:
    TARGET_PATHS = [
        r"C:\ProgramData\NVIDIA Corporation\NVIDIA App\UpdateFramework\ota-artifacts",
        r"C:\ProgramData\NVIDIA Corporation\NVIDIA App\UpdateFramework\grd",
        r"C:\ProgramData\NVIDIA Corporation\NVIDIA App\post-processing",
        r"C:\ProgramData\NVIDIA Corporation\Downloader",
        r"%LOCALAPPDATA%\NVIDIA Corporation\NV_Cache",
        r"%LOCALAPPDATA%\NVIDIA\DXCache",
        r"%LOCALAPPDATA%\NVIDIA\GLCache"
    ]

    @staticmethod
    def _expand_path(path: str) -> str:
        return os.path.expandvars(path)

    @staticmethod
    def get_folder_size(folder_path: str) -> int:
        total_size = 0
        try:
            for dirpath, _, filenames in os.walk(folder_path):
                for f in filenames:
                    fp = os.path.join(dirpath, f)
                    if not os.path.islink(fp):
                        total_size += os.path.getsize(fp)
        except Exception as e:
            log.error(f"Error calculating size for {folder_path}: {e}")
        return total_size

    def scan(self) -> Tuple[List[dict], int]:
        """
        Scans for NVIDIA junk folders.
        Returns:
            List[dict]: List of found folders with 'path' and 'size' keys.
            int: Total size in bytes.
        """
        found_folders = []
        total_size = 0

        for raw_path in self.TARGET_PATHS:
            path = self._expand_path(raw_path)
            if os.path.exists(path) and os.path.isdir(path):
                size = self.get_folder_size(path)
                found_folders.append({
                    "path": path,
                    "size": size,
                    "original_path": raw_path
                })
                total_size += size
                log.info(f"Found junk folder: {path} ({size} bytes)")
            else:
                log.debug(f"Path not found or not a directory: {path}")

        return found_folders, total_size

    def clean(self, folders: List[dict], progress_callback=None) -> Tuple[int, int, int]:
        """
        Deletes the specified folders.
        Args:
            folders: List of dicts with 'path' key.
            progress_callback: Optional callable(str) for status updates.
        Returns:
            Tuple[count_deleted, count_failed, bytes_freed]
        """
        deleted_count = 0
        failed_count = 0
        bytes_freed = 0

        for item in folders:
            path = item["path"]
            size = item.get("size", 0)
            
            if progress_callback:
                progress_callback(f"Cleaning {path}...")

            try:
                # shutil.rmtree might fail on some files if they are in use or readonly
                # We can implement a more robust retry or error handling mechanism
                if os.path.exists(path):
                    shutil.rmtree(path)
                    deleted_count += 1
                    bytes_freed += size
                    log.info(f"Deleted: {path}")
                    if progress_callback:
                        progress_callback(f"Deleted: {path}")
                else:
                    log.warning(f"Path disappeared: {path}")
            except Exception as e:
                failed_count += 1
                log.error(f"Failed to delete {path}: {e}")
                if progress_callback:
                    progress_callback(f"Failed to delete {path}: {e}")

        return deleted_count, failed_count, bytes_freed
