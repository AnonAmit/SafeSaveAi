import os
import subprocess
import shutil

def test_junction():
    target = "test_target_dir"
    link = "test_junction_link"

    # cleanup
    if os.path.exists(target): shutil.rmtree(target)
    if os.path.exists(link): os.remove(link) if os.path.islink(link) else os.rmdir(link)

    os.makedirs(target)
    
    # Create junction using mklink /J
    cmd = f'mklink /J "{link}" "{target}"'
    subprocess.run(cmd, shell=True, stdout=subprocess.DEVNULL)

    if not os.path.exists(link):
        print("Failed to create junction. Are you Admin?")
        return

    print(f"Testing path: {link}")
    print(f"Exists: {os.path.exists(link)}")
    print(f"IsLink: {os.path.islink(link)}")
    
    if hasattr(os.path, 'isjunction'):
        print(f"IsJunction: {os.path.isjunction(link)}")
    else:
        print("IsJunction: Not available in this python version")

    # cleanup
    os.rmdir(link)
    os.rmdir(target)

if __name__ == "__main__":
    test_junction()
