import os
import subprocess
import shutil
from PIL import Image

def run_build():
    print("Starting Robust Build Process...")

    # 1. Convert Logo
    if os.path.exists("logo.png"):
        print("Converting Logo to ICO...")
        try:
            img = Image.open("logo.png")
            img.save("logo.ico", format='ICO')
        except Exception as e:
            print(f"Warning: Logo conversion failed: {e}")
            
    # 2. Define Spec File Content
    # We use a Spec file to strictly control the build environment
    project_dir = os.getcwd().replace('\\', '\\\\') # Escape for string
    
    spec_content = f"""
# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['main.py'],
    pathex=['{project_dir}'],
    binaries=[],
    datas=[('logo.png', '.')],
    hiddenimports=[
        'ui_main', 'scanner', 'rules', 'mover', 'storage', 
        'config', 'ai_client', 'models', 'logger', 'themes',
        'cleaner'
    ],
    hookspath=[],
    hooksconfig={{}},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

# 1. One Directory (Portable)
exe_dir = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='SafeMoveAI',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='logo.ico',
    uac_admin=True
)
coll = COLLECT(
    exe_dir,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='SafeMoveAI_Portable',
)

# 2. One File (Installer)
exe_one = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='SafeMoveAI_Setup',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='logo.ico',
    uac_admin=True
)
"""

    # 3. Write Spec File
    with open("SafeMoveAI.spec", "w", encoding="utf-8") as f:
        f.write(spec_content)
    
    # 3. Write Spec File
    with open("SafeMoveAI.spec", "w", encoding="utf-8") as f:
        f.write(spec_content)
    
    # 4. Clean Dist/Build
    print("Attempting to close running instances...")
    subprocess.call("taskkill /F /IM SafeMoveAI.exe", shell=True)
    subprocess.call("taskkill /F /IM SafeMoveAI_Setup.exe", shell=True)
    
    import time
    time.sleep(2) # Wait for release

    if os.path.exists("dist"):
        try:
            shutil.rmtree("dist")
        except PermissionError:
             print("⚠️ Could not delete 'dist' folder. Files might be in use.")
             print("Please CLOSE the folder in Explorer and any running App instances.")
             return
    
    if os.path.exists("build"):
        shutil.rmtree("build", ignore_errors=True)

    # 5. Run PyInstaller with Spec
    print("Running PyInstaller with Spec File...")
    subprocess.run(["pyinstaller", "SafeMoveAI.spec", "--clean", "--noconfirm"], check=True)

    # 6. Post-Process (Zip)
    print("Zipping Portable Version...")
    portable_src = os.path.join("dist", "SafeMoveAI_Portable")
    # Add README
    shutil.copy("README.md", portable_src)
    
    shutil.make_archive(
        os.path.join("dist", "SafeMoveAI_Portable"), 
        'zip', 
        portable_src
    )
    
    print("Build Complete! Check 'dist' folder.")

if __name__ == "__main__":
    run_build()
