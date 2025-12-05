import sys
import os
import traceback
from PyQt6.QtWidgets import QApplication

def check_syntax(files):
    print("Checking Syntax...")
    for f in files:
        try:
            with open(f, 'r') as file:
                compile(file.read(), f, 'exec')
            print(f"OK: {f}")
        except Exception as e:
            print(f"SYNTAX ERROR in {f}: {e}")

def test_ui_init():
    print("\nTesting MainWindow Init...")
    try:
        from ui_main import MainWindow
        app = QApplication(sys.argv)
        w = MainWindow()
        print("MainWindow instantiated successfully.")
        # Don't show, just exit
    except Exception:
        traceback.print_exc()

if __name__ == "__main__":
    check_syntax(["ui_main.py", "config.py", "mover.py", "main.py"])
    test_ui_init()
