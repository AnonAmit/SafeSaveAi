import sys
import os
import threading
from PyQt6.QtGui import QPainter, QColor, QBrush, QPen, QIcon
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QPushButton, QLabel, QTableWidget, QTableWidgetItem, QTabWidget,
    QHeaderView, QMessageBox, QTextEdit, QComboBox, QLineEdit, QProgressBar,
    QCheckBox, QFrame, QGridLayout
)
import shutil
from PyQt6.QtCore import Qt, QThread, pyqtSignal

from scanner import scan_installed_apps, scan_folders
from rules import classify_item
from mover import move_item, rollback_move, MoverError
from storage import storage
from config import cfg
from ai_client import ai_client
from models import AppItem, FolderItem, ClassifiedItem
from logger import get_logger
from themes import THEMES

log = get_logger("UI")

# Workers for heavy tasks
class ScanWorker(QThread):
    finished = pyqtSignal(list)

    def run(self):
        log.info("Starting ScanWorker")
        apps = scan_installed_apps()
        folders = scan_folders()
        
        results = []
        for x in apps + folders:
            c = classify_item(x)
            results.append(c)
        
        log.info(f"Scan finished. Found {len(results)} items.")
        self.finished.emit(results)

class MoveWorker(QThread):
    progress = pyqtSignal(str)
    progress_percent = pyqtSignal(int)
    finished = pyqtSignal(bool, str)

    def __init__(self, items, target_root):
        super().__init__()
        self.items = items
        self.target_root = target_root

    def run(self):
        log.info(f"Starting MoveWorker for {len(self.items)} items")
        errors = []
        total = len(self.items)
        
        for i, c_item in enumerate(self.items):
            # Emit percent at start of item
            pct = int((i / total) * 100)
            self.progress_percent.emit(pct)
            
            self.progress.emit(f"Moving {c_item.item.name}...")
            try:
                move_item(c_item.item, self.target_root)
                log.info(f"Moved {c_item.item.name} OK")
                self.progress.emit(f"Moved {c_item.item.name} OK.")
            except Exception as e:
                log.error(f"Failed to move {c_item.item.name}: {e}")
                errors.append(f"{c_item.item.name}: {str(e)}")
                self.progress.emit(f"Failed {c_item.item.name}: {e}")
        
        # Done
        self.progress_percent.emit(100)
        
        if errors:
            self.finished.emit(False, "\n".join(errors))
        else:
            self.finished.emit(True, "All moves completed successfully.")

class AIWorker(QThread):
    finished = pyqtSignal(str)

    def __init__(self, items):
        super().__init__()
        self.items = items

    def run(self):
        resp = ai_client.suggest_optimization(self.items)
        self.finished.emit(resp)

class NumericSortItem(QTableWidgetItem):
    def __lt__(self, other):
        # Sort by the data stored in UserRole (the raw float size)
        try:
            return (self.data(Qt.ItemDataRole.UserRole) or 0) < (other.data(Qt.ItemDataRole.UserRole) or 0)
        except:
            return super().__lt__(other)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        log.info("MainWindow __init__ started")
        self.setWindowTitle("SafeMove AI")
        self.setWindowIcon(QIcon("logo.png"))
        self.resize(1000, 700)
        
        self.classified_items = []
        
        # Apply Theme
        self.apply_theme()


        
        # Main Layout
        main_wid = QWidget()
        self.setCentralWidget(main_wid)
        layout = QVBoxLayout()
        main_wid.setLayout(layout)
        
        # Tabs
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)
        
        log.info("Setting up Scan Tab")
        self.setup_scan_tab()
        log.info("Setting up Plan Tab")
        self.setup_plan_tab()
        log.info("Setting up History Tab")
        self.setup_history_tab()
        log.info("Setting up AI Tab")
        self.setup_ai_tab()
        log.info("Setting up Settings Tab")
        self.setup_settings_tab()
        
        # Load logic
        log.info("Loading Config")
        self.load_config_to_ui()
        log.info("MainWindow __init__ finished")

    def format_size(self, size_gb):
        unit = cfg.size_unit
        if unit == "MB":
            return f"{size_gb * 1024:.2f} MB"
        return f"{size_gb:.2f} GB"

    def apply_theme(self):
        t_name = cfg.theme
        if t_name in THEMES:
            THEMES[t_name].apply(QApplication.instance())
            log.info(f"Applied theme: {t_name}")

    def setup_dashboard(self, layout):
        # Disk Usage Dashboard
        self.dash_frame = QFrame()
        self.dash_frame.setStyleSheet("background-color: palette(alternateqbase); border-radius: 8px; padding: 10px;")
        
        # Horizontal Layout for cards
        h_layout = QHBoxLayout()
        self.dash_frame.setLayout(h_layout)
        
        # We need references to update them later
        self.lbl_total_val = QLabel("...")
        self.lbl_used_val = QLabel("...")
        self.lbl_free_val = QLabel("...")
        
        # Styling helper
        def style_val(lbl):
            lbl.setStyleSheet("font-size: 18px; font-weight: bold; color: palette(highlight);")
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)

        style_val(self.lbl_total_val)
        style_val(self.lbl_used_val)
        style_val(self.lbl_free_val)
        
        def add_card(title, lbl):
            card_layout = QVBoxLayout()
            t = QLabel(title)
            t.setStyleSheet("font-weight: bold; font-size: 14px; color: palette(text);")
            t.setAlignment(Qt.AlignmentFlag.AlignCenter)
            
            card_layout.addWidget(t)
            card_layout.addWidget(lbl)
            
            # Container for the card
            container = QWidget()
            container.setLayout(card_layout)
            h_layout.addWidget(container)

        add_card("Total Space", self.lbl_total_val)
        add_card("Used Space", self.lbl_used_val)
        add_card("Free Space", self.lbl_free_val)
        
        layout.addWidget(self.dash_frame)
        
        # Initial Update
        self.update_dashboard()

    def update_dashboard(self):
        try:
            total, used, free = shutil.disk_usage(cfg.target_root if os.path.exists(cfg.target_root) else "C:\\")
            
            # Update Text
            u = cfg.size_unit
            div = 1024**3 if u == "GB" else 1024**2
            
            self.lbl_total_val.setText(f"{total/div:.2f} {u}")
            self.lbl_used_val.setText(f"{used/div:.2f} {u}")
            self.lbl_free_val.setText(f"{free/div:.2f} {u}")
            
        except Exception as e:
            log.error(f"Dashboard update failed: {e}")

    def setup_scan_tab(self):
        tab = QWidget()
        layout = QVBoxLayout()
        tab.setLayout(layout)
        
        self.setup_dashboard(layout)
        
        btn_scan = QPushButton("Scan C: Drive")
        btn_scan.clicked.connect(self.start_scan)
        layout.addWidget(btn_scan)
        
        # Search Bar
        hbox_search = QHBoxLayout()
        hbox_search.addWidget(QLabel("Search:"))
        self.search_bar = QLineEdit()
        self.search_bar.setPlaceholderText("Filter by name...")
        self.search_bar.textChanged.connect(self.filter_scan_table)
        hbox_search.addWidget(self.search_bar)
        layout.addLayout(hbox_search)

        self.scan_table = QTableWidget()
        self.scan_table.setColumnCount(5)
        self.scan_table.setHorizontalHeaderLabels(["Name", "Size (GB)", "Type", "Category", "Reason"])
        self.scan_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.scan_table)
        
        # Unit Toggle
        hbox = QHBoxLayout()
        hbox.addWidget(QLabel("Display Units:"))
        self.combo_unit = QComboBox()
        self.combo_unit.addItems(["GB", "MB"])
        self.combo_unit.setCurrentText(cfg.size_unit)
        self.combo_unit.currentTextChanged.connect(self.on_unit_changed)
        hbox.addWidget(self.combo_unit)
        hbox.addStretch()
        layout.addLayout(hbox)
        
        self.tabs.addTab(tab, "Scanner")

    def setup_plan_tab(self):
        tab = QWidget()
        layout = QVBoxLayout()
        tab.setLayout(layout)
        
        layout.addWidget(QLabel("Select SAFE items to move:"))
        
        self.plan_table = QTableWidget()
        self.plan_table.setColumnCount(4)
        self.plan_table.setHorizontalHeaderLabels(["Select", "Name", "Size (GB)", "Path"])
        self.plan_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.plan_table)
        
        self.lbl_target = QLabel(f"Target: {cfg.target_root}")
        layout.addWidget(self.lbl_target)
        
        btn_move = QPushButton("Execute Move Plan")
        btn_move.setStyleSheet("background-color: #d9534f; color: white; font-weight: bold;")
        btn_move.clicked.connect(self.execute_moves)
        layout.addWidget(btn_move)
        
        self.move_progress = QProgressBar()
        self.move_progress.setValue(0)
        self.move_progress.setTextVisible(True)
        layout.addWidget(self.move_progress)
        
        self.tabs.addTab(tab, "Plan & Move")

    def setup_history_tab(self):
        tab = QWidget()
        layout = QVBoxLayout()
        tab.setLayout(layout)
        
        btn_refresh = QPushButton("Refresh History")
        btn_refresh.clicked.connect(self.load_history)
        layout.addWidget(btn_refresh)
        
        self.history_table = QTableWidget()
        self.history_table.setColumnCount(5)
        self.history_table.setHorizontalHeaderLabels(["ID", "Source", "Target", "Status", "Action"])
        self.history_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.history_table)
        
        self.tabs.addTab(tab, "History & Rollback")

    def setup_ai_tab(self):
        tab = QWidget()
        layout = QVBoxLayout()
        tab.setLayout(layout)
        
        self.chat_area = QTextEdit()
        self.chat_area.setReadOnly(True)
        layout.addWidget(self.chat_area)
        
        btn_analyze = QPushButton("Ask AI: Verify My Scan")
        btn_analyze.clicked.connect(self.ask_ai_scan)
        layout.addWidget(btn_analyze)
        
        self.tabs.addTab(tab, "AI Assistant")

    def setup_settings_tab(self):
        tab = QWidget()
        layout = QVBoxLayout()
        tab.setLayout(layout)
        
        # Target Root
        layout.addWidget(QLabel("Target Drive Root:"))
        self.entry_root = QLineEdit()
        layout.addWidget(self.entry_root)
        
        # LLM Mode
        layout.addWidget(QLabel("LLM Mode:"))
        self.combo_mode = QComboBox()
        self.combo_mode.addItems(["none", "cloud", "local"])
        layout.addWidget(self.combo_mode)
        
        # Cloud Key
        layout.addWidget(QLabel("Cloud API Key:"))
        self.entry_key = QLineEdit()
        self.entry_key.setEchoMode(QLineEdit.EchoMode.Password)
        layout.addWidget(self.entry_key)
        
        # Local URL
        layout.addWidget(QLabel("Local URL:"))
        self.entry_url = QLineEdit()
        layout.addWidget(self.entry_url)
        
        # Theme Selector
        layout.addWidget(QLabel("Theme:"))
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(list(THEMES.keys()))
        self.theme_combo.setCurrentText(cfg.theme)
        self.theme_combo.currentTextChanged.connect(self.on_theme_changed)
        layout.addWidget(self.theme_combo)
        
        btn_save = QPushButton("Save Settings")
        btn_save.clicked.connect(self.save_config)
        layout.addWidget(btn_save)
        
        self.tabs.addTab(tab, "Settings")

    # --- Logic ---
    
    def start_scan(self):
        self.setEnabled(False)
        self.scan_worker = ScanWorker()
        self.scan_worker.finished.connect(self.on_scan_finished)
        self.scan_worker.start()

    def on_scan_finished(self, results):
        self.setEnabled(True)
        self.classified_items = results
        self.refresh_scan_table()
        self.refresh_plan_table()
        QMessageBox.information(self, "Scan Complete", f"Found {len(results)} items.")

    def on_unit_changed(self, text):
        cfg.size_unit = text
        self.refresh_scan_table()
        self.refresh_plan_table()
        self.update_dashboard()

    def refresh_scan_table(self):
        self.scan_table.setSortingEnabled(False) # Disable during update
        self.scan_table.setRowCount(len(self.classified_items))
        self.scan_table.setHorizontalHeaderLabels(["Name", f"Size ({cfg.size_unit})", "Type", "Category", "Reason"])
        for i, c in enumerate(self.classified_items):
            self.scan_table.setItem(i, 0, QTableWidgetItem(c.item.name))
            
            # Size Column - Use Custom Item
            size_item = NumericSortItem(self.format_size(c.item.size_gb))
            size_item.setData(Qt.ItemDataRole.UserRole, c.item.size_gb)
            self.scan_table.setItem(i, 1, size_item)
            
            self.scan_table.setItem(i, 2, QTableWidgetItem(c.item.type))
            
            item_cat = QTableWidgetItem(c.category)
            if c.category == "FORBIDDEN":
                item_cat.setBackground(Qt.GlobalColor.red)
            elif c.category == "SAFE":
                item_cat.setBackground(Qt.GlobalColor.green)
            elif c.category == "MOVED":
                item_cat.setBackground(Qt.GlobalColor.lightGray)
            else:
                item_cat.setBackground(Qt.GlobalColor.yellow)
            
            self.scan_table.setItem(i, 3, item_cat)
            self.scan_table.setItem(i, 4, QTableWidgetItem(c.reason))
        self.scan_table.setSortingEnabled(True)

    def refresh_plan_table(self):
        self.plan_table.setSortingEnabled(False)
        safe_items = [c for c in self.classified_items if c.category == "SAFE"]
        self.plan_table.setRowCount(len(safe_items))
        self.plan_table.setHorizontalHeaderLabels(["Select", "Name", f"Size ({cfg.size_unit})", "Path"])
        for i, c in enumerate(safe_items):
            chk = QTableWidgetItem()
            chk.setFlags(Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled)
            chk.setCheckState(Qt.CheckState.Unchecked)
            # Store object reference in data
            chk.setData(Qt.ItemDataRole.UserRole, c)
            
            self.plan_table.setItem(i, 0, chk)
            self.plan_table.setItem(i, 1, QTableWidgetItem(c.item.name))
            
            # Size Column
            size_item = NumericSortItem(self.format_size(c.item.size_gb))
            size_item.setData(Qt.ItemDataRole.UserRole, c.item.size_gb)
            self.plan_table.setItem(i, 2, size_item)
            
            self.plan_table.setItem(i, 3, QTableWidgetItem(c.item.path))
        self.plan_table.setSortingEnabled(True)

    def filter_scan_table(self, text):
        search = text.lower()
        for i in range(self.scan_table.rowCount()):
            item = self.scan_table.item(i, 0) # Name column
            if not item: continue
            name = item.text().lower()
            if search in name:
                self.scan_table.setRowHidden(i, False)
            else:
                self.scan_table.setRowHidden(i, True)

    def execute_moves(self):
        items_to_move = []
        for row in range(self.plan_table.rowCount()):
            item = self.plan_table.item(row, 0)
            if item.checkState() == Qt.CheckState.Checked:
                items_to_move.append(item.data(Qt.ItemDataRole.UserRole))
        
        if not items_to_move:
            QMessageBox.warning(self, "No Selection", "Please select SAFE items to move.")
            return

        confirm = QMessageBox.question(
            self, "Confirm Move", 
            f"Are you sure you want to move {len(items_to_move)} items to {cfg.target_root}?\n"
            "This will use junctions. Do not unplug the target drive."
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return

        self.setEnabled(False)
        self.move_progress.setValue(0)
        
        self.move_worker = MoveWorker(items_to_move, cfg.target_root)
        self.move_worker.progress.connect(lambda s: self.chat_area.append(s))
        self.move_worker.progress_percent.connect(self.move_progress.setValue)
        self.move_worker.finished.connect(self.on_move_finished)
        self.move_worker.start()

    def on_move_finished(self, success, msg):
        self.setEnabled(True)
        if success:
            QMessageBox.information(self, "Success", msg)
        else:
            QMessageBox.critical(self, "Errors Occurred", msg)
        self.load_history()

    def load_history(self):
        moves = storage.get_history()
        self.history_table.setRowCount(len(moves))
        for i, row in enumerate(moves):
            # moves schema: id, src, tgt, time, status, cat
            mid, src, tgt, time, status, cat = row
            self.history_table.setItem(i, 0, QTableWidgetItem(str(mid)))
            self.history_table.setItem(i, 1, QTableWidgetItem(src))
            self.history_table.setItem(i, 2, QTableWidgetItem(tgt))
            self.history_table.setItem(i, 3, QTableWidgetItem(status))
            
            if status == "OK":
                btn_rb = QPushButton("Rollback")
                btn_rb.clicked.connect(lambda checked, m=mid: self.do_rollback(m))
                self.history_table.setCellWidget(i, 4, btn_rb)
            else:
                self.history_table.setItem(i, 4, QTableWidgetItem("-"))

    def do_rollback(self, move_id):
        try:
            rollback_move(move_id)
            QMessageBox.information(self, "Rollback", "Rollback successful.")
            self.load_history()
        except Exception as e:
            QMessageBox.critical(self, "Rollback Failed", str(e))

    def ask_ai_scan(self):
        if not self.classified_items:
            QMessageBox.warning(self, "Empty", "Please Scan first.")
            return
            
        self.chat_area.append("Asking AI for advice, please wait...")
        self.setEnabled(False)
        self.ai_worker = AIWorker(self.classified_items)
        self.ai_worker.finished.connect(self.on_ai_finished)
        self.ai_worker.start()

    def on_ai_finished(self, response):
        self.setEnabled(True)
        self.chat_area.append("\nAI Suggestion:\n")
        self.chat_area.append(response)
        self.chat_area.append("\n---\n")

    def on_theme_changed(self, text):
        cfg.theme = text
        self.apply_theme()

    def load_config_to_ui(self):
        self.entry_root.setText(cfg.target_root)
        self.entry_key.setText(cfg.cloud_config.get("api_key", ""))
        self.entry_url.setText(cfg.local_config.get("base_url", ""))
        
        mode = cfg.llm_mode
        idx = self.combo_mode.findText(mode)
        if idx >= 0:
            self.combo_mode.setCurrentIndex(idx)

    def save_config(self):
        cfg.target_root = self.entry_root.text()
        cfg.llm_mode = self.combo_mode.currentText()
        cfg.theme = self.theme_combo.currentText()
        cfg.set("cloud", {
            **cfg.cloud_config,
            "api_key": self.entry_key.text()
        })
        cfg.set("local", {
            **cfg.local_config,
            "base_url": self.entry_url.text()
        })
        self.lbl_target.setText(f"Target: {cfg.target_root}")
        QMessageBox.information(self, "Saved", "Configuration saved.")
