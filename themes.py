from PyQt6.QtGui import QColor, QPalette

class Theme:
    def apply(self, app):
        pass

class StandardTheme(Theme):
    def apply(self, app):
        app.setStyle("Fusion")
        # Reset palette to default Fusion
        app.setPalette(QPalette())

class CyberpunkTheme(Theme):
    def apply(self, app):
        app.setStyle("Fusion")
        
        dark_palette = QPalette()
        
        # Colors
        color_bg = QColor(18, 18, 18)        # Almost Black
        color_fg = QColor(0, 255, 65)        # Neon Green
        color_fg_sec = QColor(200, 200, 200) # Light Gray
        color_acc = QColor(255, 0, 85)       # Neon Pink/Red for errors/buttons
        color_panel = QColor(30, 30, 30)     # Dark Gray for panels
        
        # Mapping
        dark_palette.setColor(QPalette.ColorRole.Window, color_bg)
        dark_palette.setColor(QPalette.ColorRole.WindowText, color_fg)
        dark_palette.setColor(QPalette.ColorRole.Base, color_panel) # Inputs background
        dark_palette.setColor(QPalette.ColorRole.AlternateBase, color_bg)
        dark_palette.setColor(QPalette.ColorRole.ToolTipBase, color_bg)
        dark_palette.setColor(QPalette.ColorRole.ToolTipText, color_fg)
        dark_palette.setColor(QPalette.ColorRole.Text, color_fg)
        dark_palette.setColor(QPalette.ColorRole.Button, color_panel)
        dark_palette.setColor(QPalette.ColorRole.ButtonText, color_fg)
        dark_palette.setColor(QPalette.ColorRole.BrightText, QColor(255, 255, 255))
        dark_palette.setColor(QPalette.ColorRole.Link, color_acc)
        dark_palette.setColor(QPalette.ColorRole.Highlight, color_acc)
        dark_palette.setColor(QPalette.ColorRole.HighlightedText, QColor(0, 0, 0))

        app.setPalette(dark_palette)
        
        # Additional Stylesheet for specific controls
        app.setStyleSheet("""
            QToolTip { 
                color: #00FF41; 
                background-color: #121212; 
                border: 1px solid #00FF41; 
            }
            QProgressBar {
                border: 2px solid #00FF41;
                border-radius: 5px;
                text-align: center;
                color: #000000;
            }
            QProgressBar::chunk {
                background-color: #00FF41;
                width: 10px; 
                margin: 0.5px;
            }
            QTableWidget {
                gridline-color: #00FF41;
                selection-background-color: #FF0055;
                color: #00FF41;
            }
            QHeaderView::section {
                background-color: #121212;
                color: #00FF41;
                border: 1px solid #00FF41;
            }
            QPushButton {
                background-color: #1e1e1e;
                border: 1px solid #00FF41;
                color: #00FF41;
                padding: 5px;
                border-radius: 3px;
            }
            QPushButton:hover {
                background-color: #00FF41;
                color: #000000;
            }
            QLineEdit {
                border: 1px solid #00FF41;
                background-color: #1e1e1e;
                color: #00FF41;
            }
        """)

THEMES = {
    "Standard": StandardTheme(),
    "Cyberpunk": CyberpunkTheme()
}
