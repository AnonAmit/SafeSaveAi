from PyQt6.QtGui import QPalette, QColor, QFont
from PyQt6.QtWidgets import QApplication

class Theme:
    def __init__(self, name, colors):
        self.name = name
        self.c = colors

    def apply(self, app):
        app.setStyle("Fusion")
        
        # 1. Generate QPalette for basic controls that don't fully support QSS or for backup
        palette = QPalette()
        palette.setColor(QPalette.ColorRole.Window, QColor(self.c['bg']))
        palette.setColor(QPalette.ColorRole.WindowText, QColor(self.c['text']))
        palette.setColor(QPalette.ColorRole.Base, QColor(self.c['surface']))
        palette.setColor(QPalette.ColorRole.AlternateBase, QColor(self.c['bg']))
        palette.setColor(QPalette.ColorRole.ToolTipBase, QColor(self.c['surface']))
        palette.setColor(QPalette.ColorRole.ToolTipText, QColor(self.c['text']))
        palette.setColor(QPalette.ColorRole.Text, QColor(self.c['text']))
        palette.setColor(QPalette.ColorRole.Button, QColor(self.c['surface']))
        palette.setColor(QPalette.ColorRole.ButtonText, QColor(self.c['text']))
        palette.setColor(QPalette.ColorRole.Link, QColor(self.c['primary']))
        palette.setColor(QPalette.ColorRole.Highlight, QColor(self.c['primary']))
        palette.setColor(QPalette.ColorRole.HighlightedText, QColor("#FFFFFF"))
        
        app.setPalette(palette)
        
        # 2. Set Global Font
        font = QFont("Segoe UI", 10)
        app.setFont(font)

        # 3. Apply QSS
        qss = self.get_stylesheet()
        app.setStyleSheet(qss)

    def get_stylesheet(self):
        c = self.c
        return f"""
        /* GLOBAL */
        QWidget {{
            background-color: {c['bg']};
            color: {c['text']};
            selection-background-color: {c['primary']};
            selection-color: #FFFFFF;
        }}
        
        /* HEADERS */
        QLabel[cssClass="h1"] {{
            font-size: 24px;
            font-weight: bold;
            color: {c['text']};
        }}
        QLabel[cssClass="h2"] {{
            font-size: 18px;
            font-weight: 600;
            color: {c['text']};
            margin-bottom: 8px;
        }}
        QLabel[cssClass="subtitle"] {{
            font-size: 13px;
            color: {c['text_dim']};
        }}

        /* CARDS */
        QFrame[cssClass="card"] {{
            background-color: {c['surface']};
            border-radius: 8px;
            border: 1px solid {c['border']};
        }}
        QFrame[cssClass="card"]:hover {{
            border: 1px solid {c['primary']};
        }}
        
        /* TABS */
        QTabWidget::pane {{
            border: 1px solid {c['border_light']};
            background: {c['bg']};
            border-radius: 4px;
            top: -1px; 
        }}
        QTabBar::tab {{
            background: {c['bg']};
            color: {c['text_dim']};
            padding: 8px 20px;
            min-width: 80px;
            border-bottom: 2px solid transparent;
            font-weight: 500;
        }}
        QTabBar::tab:selected {{
            color: {c['primary']};
            border-bottom: 2px solid {c['primary']};
            font-weight: bold;
        }}
        QTabBar::tab:hover {{
            color: {c['text']};
            background: {c['surface']};
        }}

        /* BUTTONS */
        QPushButton {{
            background-color: {c['surface']};
            color: {c['text']};
            border: 1px solid {c['border']};
            border-radius: 6px;
            padding: 6px 16px;
            font-weight: 600;
        }}
        QPushButton:hover {{
            background-color: {c['border']};
            border-color: {c['text_dim']};
        }}
        QPushButton:pressed {{
            background-color: {c['primary']};
            color: #FFFFFF;
        }}
        
        /* Primary CTA */
        QPushButton[cssClass="primary"] {{
            background-color: {c['primary']};
            color: #FFFFFF;
            border: 1px solid {c['primary']};
        }}
        QPushButton[cssClass="primary"]:hover {{
            background-color: {c['primary_hover']};
            border-color: {c['primary_hover']};
        }}
        
        /* Dangerous Action */
        QPushButton[cssClass="danger"] {{
            background-color: {c['danger']};
            color: #FFFFFF;
            border: 1px solid {c['danger']};
        }}
        QPushButton[cssClass="danger"]:hover {{
            background-color: #CC0000;
        }}

        /* INPUTS */
        QLineEdit, QComboBox, QTextEdit {{
            background-color: {c['input_bg']};
            border: 1px solid {c['border']};
            border-radius: 6px;
            padding: 6px;
            color: {c['text']};
        }}
        QLineEdit:focus, QComboBox:focus, QTextEdit:focus {{
            border: 1px solid {c['primary']};
            background-color: {c['input_bg_focus']};
        }}
        
        /* TABLES */
        QTableWidget {{
            gridline-color: {c['border_light']};
            background-color: {c['bg']};
            border: 1px solid {c['border']};
            border-radius: 6px;
            outline: none;
        }}
        QHeaderView::section {{
            background-color: {c['surface']};
            color: {c['text']};
            padding: 6px;
            border: none;
            border-bottom: 2px solid {c['border']};
            font-weight: bold;
        }}
        QTableWidget::item {{
            padding: 4px;
        }}
        QTableWidget::item:selected {{
            background-color: {c['primary_dim']};
            color: {c['text']};
        }}

        /* PROGRESS BAR */
        QProgressBar {{
            border: 1px solid {c['border']};
            border-radius: 6px;
            background-color: {c['input_bg']};
            color: {c['text']};
            text-align: center;
        }}
        QProgressBar::chunk {{
            background-color: {c['primary']};
            border-radius: 5px;
        }}
        
        /* SCROLLBAR */
        QScrollBar:vertical {{
            border: none;
            background: {c['bg']};
            width: 10px;
            margin: 0px;
        }}
        QScrollBar::handle:vertical {{
            background: {c['border']};
            min-height: 20px;
            border-radius: 5px;
        }}
        
        /* PILLS / BADGES (Custom styling for table cells if needed via Delegate, but generic here) */
        """

# --- PALETTES ---

# Standard Pro Dark (Clean, Professional, Linear, Gray/Blue)
PALETTE_STANDARD = {
    'bg': '#121212',
    'surface': '#1E1E1E',
    'primary': '#3A86FF',         # Vivid Blue
    'primary_hover': '#2667CC',
    'primary_dim': '#1A3A66',     # For selection bg
    'text': '#E0E0E0',
    'text_dim': '#A0A0A0',
    'border': '#333333',
    'border_light': '#2A2A2A',
    'input_bg': '#181818',
    'input_bg_focus': '#222222',
    'danger': '#E63946',
    'success': '#06D6A0',
    'warning': '#FFD166'
}

# Cyberpunk Neon (High Contrast, Black/Neon Pink/Green/Cyan)
PALETTE_CYBERPUNK = {
    'bg': '#050505',
    'surface': '#131313',
    'primary': '#00FF41',         # Matrix Green / Neon Green #00E5FF (Cyan)
    'primary_hover': '#00CC33',
    'primary_dim': '#00330E',
    'text': '#E0E0E0',            # Keep text readable white
    'text_dim': '#008F11',        # Dim green matrix style
    'border': '#00FF41',          # Neon Borders
    'border_light': '#004411',
    'input_bg': '#000000',
    'input_bg_focus': '#001100',
    'danger': '#FF0055',          # Neon Pink
    'success': '#00FF41',
    'warning': '#F9F871'
}

THEMES = {
    "Standard": Theme("Standard", PALETTE_STANDARD),
    "Cyberpunk": Theme("Cyberpunk", PALETTE_CYBERPUNK)
}
