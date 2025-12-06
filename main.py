import sys
import ctypes
from PyQt6.QtWidgets import QApplication, QMessageBox
from ui_main import MainWindow
from logger import logger

def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

def main():
    logger.info("Starting Application...")
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    
    if not is_admin():
        logger.warning("Not running as Admin")
        # Warn user but allow opening to see instructions or scan (just move will fail)
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Icon.Warning)
        msg.setWindowTitle("Admin Rights Required")
        msg.setText("SafeMove AI needs to run as Administrator to perform moves (create junctions).\n\nYou can Scan and Plan, but moves will fail.")
        msg.exec()
    
    logger.info("Initializing MainWindow")
    window = MainWindow()
    logger.info("Showing MainWindow")
    window.show()
    
    logger.info("Entering Event Loop")
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
