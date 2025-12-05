import subprocess
import os
import shutil
from pathlib import Path
from models import AppItem, FolderItem
from rules import classify_item
from storage import storage

class MoverError(Exception):
    pass

def run_command(cmd_args, shell=True):
    """Run a system command and return output. Raises MoverError on failure."""
    try:
        # Robocopy has special return codes:
        # 0 = No files copied? 
        # 1 = Files copied successfully
        # 4 = Mismatched files
        # 8 = Copy failed
        result = subprocess.run(
            cmd_args,
            shell=shell,
            capture_output=True,
            text=True
        )
        return result
    except Exception as e:
        raise MoverError(f"Command execution failed: {e}")

def move_item(item: AppItem | FolderItem, target_root: str):
    """Move an item to target_root and link back."""
    
    # 1. Safety Check (Redundant but necessary)
    classification = classify_item(item)
    if classification.category == "FORBIDDEN":
        raise MoverError(f"Safety Block: {classification.reason}")
    
    source_path = os.path.normpath(item.path)
    if not os.path.exists(source_path):
        raise MoverError(f"Source not found: {source_path}")

    # Determine target path
    # Preserve folder name
    folder_name = os.path.basename(source_path)
    target_path = os.path.join(target_root, folder_name)
    target_path = os.path.normpath(target_path)

    # Collision Handling
    if os.path.exists(target_path):
        # Auto-rename if target exists and is not empty
        if os.listdir(target_path):
            base_name = folder_name
            counter = 1
            while os.path.exists(target_path) and os.listdir(target_path):
                new_name = f"{base_name}_{counter}"
                target_path = os.path.join(target_root, new_name)
                counter += 1
            print(f"Target Collision: Renamed to {target_path}")

    # Log start (optional, we log success at end)
    print(f"Moving {source_path} -> {target_path}")

    # 2. Robocopy Move
    # /E = recursive, including empty
    # /COPYALL = copy info, timestamps, permissions
    # /MOVE = move files AND dirs (delete from source)
    # /R:3 /W:1 = retry 3 times, wait 1 sec
    robocopy_cmd = [
        "robocopy",
        f'"{source_path}"',
        f'"{target_path}"',
        "/E", "/COPYALL", "/MOVE",
        "/R:3", "/W:1"
    ]
    
    # robocopy args need to be a string for shell=True usually to handle quotes right, 
    # OR list with shell=False. Windows is tricky.
    # We will use string command for fewer issues with quote parsing in subprocess on Windows
    cmd_str = " ".join(robocopy_cmd)
    
    result = run_command(cmd_str)
    
    # Robocopy return codes: < 8 is success
    if result.returncode >= 8:
         raise MoverError(f"Robocopy failed (Code {result.returncode}): {result.stdout}\n{result.stderr}")
         
    # 3. Verify
    if not os.path.exists(target_path) or not os.listdir(target_path):
        raise MoverError("Move appeared to finish but target is empty or missing.")
        
    # Check if source is truly gone (Robocopy /MOVE should do it)
    if os.path.exists(source_path):
        # Sometimes root folder is left if it was locked, but empty
        try:
            os.rmdir(source_path)
        except OSError:
            # If it still has files, that's a problem. Abort linking.
            if os.listdir(source_path):
                 raise MoverError("Files are in use. Please close the application (check System Tray) and try again.")

    # 4. Link
    # mklink /J Link Target
    link_cmd = f'mklink /J "{source_path}" "{target_path}"'
    link_res = run_command(link_cmd)

    if link_res.returncode != 0:
        # CRITICAL: Failed to link. User has split data now.
        # Log this strictly.
        raise MoverError(f"Junction creation failed: {link_res.stdout} {link_res.stderr}")

    # 5. Log Success
    storage.log_move(source_path, target_path, "OK", classification.category)
    return True

def rollback_move(move_id: int):
    """Rollback a move by ID."""
    record = storage.get_move(move_id)
    if not record:
        raise MoverError("Move ID not found")
        
    # Unpack record (id, src, tgt, time, status, output...)
    # Schema: id, source_path, target_path, timestamp, status, category
    row_id, source_path, target_path, _, status, _ = record
    
    if status != "OK":
        raise MoverError("Cannot rollback a failed or already rolled-back move")

    if not os.path.exists(target_path):
        raise MoverError(f"Target data missing: {target_path}")

    # 1. Remove Junction
    # Verify source is actually a junction
    if os.path.exists(source_path):
         # check if reparse point
         # Python < 3.8 islink matches symlinks, not junctions always. 
         # But standard os.rmdir removes junction without deleting content suitable for 3.11
         try:
             os.rmdir(source_path)
         except OSError as e:
             raise MoverError(f"Failed to remove junction '{source_path}': {e}. Is it a real folder?")
    
    # 2. Move Back
    robocopy_cmd = f'robocopy "{target_path}" "{source_path}" /E /COPYALL /MOVE /R:3 /W:1'
    result = run_command(robocopy_cmd)
    
    if result.returncode >= 8:
        raise MoverError(f"Rollback copy failed: {result.stdout}")
        
    # 3. Cleanup Target
    if os.path.exists(target_path):
        try:
            os.rmdir(target_path)
        except OSError:
             pass # Might be minor leftovers
             
    # 4. Update DB
    storage.update_status(row_id, "ROLLED_BACK")
    return True
