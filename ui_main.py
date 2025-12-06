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
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QSize

from scanner import scan_installed_apps, scan_folders
from rules import classify_item
from mover import move_item, rollback_move, MoverError
from storage import storage
from config import cfg
from ai_client import ai_client
from models import AppItem, FolderItem, ClassifiedItem
from logger import get_logger
from themes import THEMES
from cleaner import NvidiaCleaner

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

class CleanWorker(QThread):
    progress = pyqtSignal(str)
    finished = pyqtSignal(int, int, int) # deleted, failed, freed_bytes

    def __init__(self, items):
        super().__init__()
        self.items = items
        self.cleaner = NvidiaCleaner()

    def run(self):
        log.info("Starting CleanWorker")
        deleted, failed, freed = self.cleaner.clean(self.items, self.progress.emit)
        self.finished.emit(deleted, failed, freed)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        log.info("MainWindow __init__ started")
        self.setWindowTitle("SafeMove AI v2.0.0")
        self.setWindowIcon(QIcon("logo.png"))
        self.resize(1100, 750)
        
        self.classified_items = []
        
        # Apply Base Styling
        self.apply_theme()
        
        # Main Layout
        main_wid = QWidget()
        self.setCentralWidget(main_wid)
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0) # Edge to edge
        layout.setSpacing(0)
        main_wid.setLayout(layout)
        
        # Header / Tab Bar Area
        self.tabs = QTabWidget()
        self.tabs.setIconSize(QSize(20, 20))
        layout.addWidget(self.tabs)
        
        # --- TAB 1: SCANNER ---
        self.setup_scan_tab()
        
        # --- TAB 2: PLAN ---
        self.setup_plan_tab()
        
        # --- TAB 3: HISTORY ---
        self.setup_history_tab()
        
        # --- TAB 4: AI ASSISTANT ---
        self.setup_ai_tab()
        
        # --- TAB 5: CLEANER ---
        self.setup_cleaner_tab()
        
        # --- TAB 6: SETTINGS ---
        self.setup_settings_tab()
        
        # Load logic
        self.load_config_to_ui()
        log.info("MainWindow UI setup complete")

    def apply_theme(self):
        t_name = cfg.theme
        if t_name in THEMES:
            THEMES[t_name].apply(QApplication.instance())

    # --- HELPER: CARD CREATOR ---
    def create_metric_card(self, title, obj_name):
        card = QFrame()
        card.setProperty("cssClass", "card")
        vbox = QVBoxLayout()
        vbox.setContentsMargins(20, 15, 20, 15)
        card.setLayout(vbox)
        
        lbl_title = QLabel(title.upper())
        lbl_title.setProperty("cssClass", "subtitle")
        
        lbl_val = QLabel("...")
        lbl_val.setProperty("cssClass", "h1")
        lbl_val.setStyleSheet("color: palette(link);") # Use primary color
        
        # Store ref
        setattr(self, obj_name, lbl_val)
        
        vbox.addWidget(lbl_title)
        vbox.addWidget(lbl_val)
        return card

    # --- TAB 1: SCANNER ---
    def setup_scan_tab(self):
        tab = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)
        tab.setLayout(layout)
        
        # 1. Dashboard Cards
        dash_layout = QHBoxLayout()
        dash_layout.addWidget(self.create_metric_card("Total Space", "lbl_total"))
        dash_layout.addWidget(self.create_metric_card("Used Space", "lbl_used"))
        dash_layout.addWidget(self.create_metric_card("Free Space", "lbl_free"))
        layout.addLayout(dash_layout)
        
        # 2. Controls (Search + Scan)
        controls_layout = QHBoxLayout()
        
        self.search_bar = QLineEdit()
        self.search_bar.setPlaceholderText("Filter items by name...")
        self.search_bar.textChanged.connect(self.filter_scan_table)
        self.search_bar.setMinimumWidth(300)
        controls_layout.addWidget(self.search_bar)
        
        controls_layout.addStretch()
        
        self.combo_unit = QComboBox()
        self.combo_unit.addItems(["GB", "MB"])
        self.combo_unit.setCurrentText(cfg.size_unit)
        self.combo_unit.currentTextChanged.connect(self.on_unit_changed)
        controls_layout.addWidget(QLabel("Units:"))
        controls_layout.addWidget(self.combo_unit)

        btn_scan = QPushButton("SCAN C: DRIVE")
        btn_scan.setProperty("cssClass", "primary")
        btn_scan.setMinimumHeight(36)
        btn_scan.clicked.connect(self.start_scan)
        controls_layout.addWidget(btn_scan)
        
        layout.addLayout(controls_layout)
        
        # 3. Table
        self.scan_table = QTableWidget()
        self.scan_table.setColumnCount(5)
        self.scan_table.setHorizontalHeaderLabels(["Name", "Size", "Type", "Category", "Reason"])
        self.scan_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.scan_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.scan_table.verticalHeader().setVisible(False)
        self.scan_table.setShowGrid(False)
        self.scan_table.setAlternatingRowColors(True)
        layout.addWidget(self.scan_table)
        
        # Initial Dashboard
        self.update_dashboard()
        
        self.tabs.addTab(tab, "  Scanner")

    # --- TAB 2: PLAN ---
    def setup_plan_tab(self):
        tab = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        tab.setLayout(layout)
        
        # Header
        head = QLabel("Select Items to Move")
        head.setProperty("cssClass", "h2")
        layout.addWidget(head)
        
        sub = QLabel("Only items marked as SAFE are shown below. Please verify your selection.")
        sub.setProperty("cssClass", "subtitle")
        layout.addWidget(sub)
        
        # Target Selector
        target_box = QHBoxLayout()
        target_box.addWidget(QLabel("Target Root:"))
        self.entry_root_display = QLineEdit(cfg.target_root)
        self.entry_root_display.setReadOnly(True)
        target_box.addWidget(self.entry_root_display)
        # Browse button could go here
        layout.addLayout(target_box)
        
        # Table
        self.plan_table = QTableWidget()
        self.plan_table.setColumnCount(4)
        self.plan_table.setHorizontalHeaderLabels(["Select", "Name", "Size", "Path"])
        self.plan_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self.plan_table.verticalHeader().setVisible(False)
        self.plan_table.setAlternatingRowColors(True)
        layout.addWidget(self.plan_table)
        
        # Footer Actions
        footer = QHBoxLayout()
        self.move_progress = QProgressBar()
        self.move_progress.setTextVisible(False)
        self.move_progress.setRange(0, 100)
        self.move_progress.setValue(0)
        footer.addWidget(self.move_progress)
        
        btn_exec = QPushButton("EXECUTE MOVE PLAN")
        btn_exec.setProperty("cssClass", "primary")
        btn_exec.setMinimumHeight(40)
        btn_exec.setMinimumWidth(200)
        btn_exec.clicked.connect(self.execute_moves)
        footer.addWidget(btn_exec)
        
        layout.addLayout(footer)
        self.tabs.addTab(tab, "  Plan & Move")

    # --- TAB 3: HISTORY ---
    def setup_history_tab(self):
        tab = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        tab.setLayout(layout)
        
        # Controls
        h_ctrl = QHBoxLayout()
        h_ctrl.addWidget(QLabel("Move History Log"))
        h_ctrl.addStretch()
        btn_ref = QPushButton("Refresh")
        btn_ref.clicked.connect(self.load_history)
        h_ctrl.addWidget(btn_ref)
        layout.addLayout(h_ctrl)
        
        self.history_table = QTableWidget()
        self.history_table.setColumnCount(5)
        self.history_table.setHorizontalHeaderLabels(["ID", "Source", "Target", "Status", "Action"])
        self.history_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.history_table.verticalHeader().setVisible(False)
        self.history_table.setAlternatingRowColors(True)
        layout.addWidget(self.history_table)
        
        self.tabs.addTab(tab, "  History")

    # --- TAB 4: AI ---
    def setup_ai_tab(self):
        tab = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        tab.setLayout(layout)
        
        # Chat Area
        self.chat_area = QTextEdit()
        self.chat_area.setReadOnly(True)
        self.chat_area.setPlaceholderText("AI analysis will appear here...")
        
        # Empty State Background (if exists)
        if os.path.exists("ai_bg.png"):
            # We can't easily set bg image on QTextEdit without CSS conflict, 
            # so we just append a welcome message or handle it logic side.
            pass
            
        layout.addWidget(self.chat_area)
        
        # Actions
        actions = QHBoxLayout()
        btn_ask = QPushButton("✨ Ask AI: Analyze Threats & Risks")
        btn_ask.setProperty("cssClass", "primary")
        btn_ask.setMinimumHeight(40)
        btn_ask.clicked.connect(self.ask_ai_scan)
        actions.addWidget(btn_ask)
        
        layout.addLayout(actions)
        self.tabs.addTab(tab, "  AI Assistant")

    # --- TAB 5: CLEANER ---
    def setup_cleaner_tab(self):
        tab = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        tab.setLayout(layout)
        
        # Banner
        banner = QFrame()
        banner.setStyleSheet("background-color: #331100; border: 1px solid #FF5500; border-radius: 6px;")
        bloc = QHBoxLayout()
        lbl_warn = QLabel("⚠️  NVIDIA Junk Cleaner: Removes old driver installers and cache files.")
        lbl_warn.setStyleSheet("color: #FF8800; font-weight: bold; border: none;")
        bloc.addWidget(lbl_warn)
        banner.setLayout(bloc)
        layout.addWidget(banner)
        
        # Controls
        ctrl = QHBoxLayout()
        self.lbl_clean_summary = QLabel("Ready to scan.")
        self.lbl_clean_summary.setProperty("cssClass", "subtitle")
        ctrl.addWidget(self.lbl_clean_summary)
        ctrl.addStretch()
        
        btn_scan = QPushButton("Scan Junk")
        btn_scan.clicked.connect(self.scan_nvidia_junk)
        ctrl.addWidget(btn_scan)
        layout.addLayout(ctrl)
        
        # List
        self.clean_list = QTableWidget()
        self.clean_list.setColumnCount(3)
        self.clean_list.setHorizontalHeaderLabels(["Path", "Size", "Status"])
        self.clean_list.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.clean_list)
        
        # Action
        act_box = QHBoxLayout()
        self.clean_progress = QProgressBar()
        act_box.addWidget(self.clean_progress)
        
        btn_clean = QPushButton("CLEAN ALL")
        btn_clean.setProperty("cssClass", "danger")
        btn_clean.clicked.connect(self.clean_nvidia_junk)
        act_box.addWidget(btn_clean)
        
        layout.addLayout(act_box)
        self.tabs.addTab(tab, "  Cleaner")

    # --- TAB 6: SETTINGS ---
    def setup_settings_tab(self):
        tab = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)
        tab.setLayout(layout)
        
        # Group: Storage
        grp_store = QWidget()
        l_store = QVBoxLayout()
        l_store.setContentsMargins(0,0,0,0)
        grp_store.setLayout(l_store)
        
        l_store.addWidget(QLabel("Target Drive Root"))
        self.entry_root = QLineEdit()
        l_store.addWidget(self.entry_root)
        layout.addWidget(grp_store)
        
        # Group: AI
        layout.addWidget(QLabel("AI Configuration"))
        self.combo_mode = QComboBox()
        self.combo_mode.addItems(["none", "cloud", "local"])
        layout.addWidget(self.combo_mode)
        
        grid = QGridLayout()
        grid.addWidget(QLabel("Cloud API Key:"), 0, 0)
        self.entry_key = QLineEdit()
        self.entry_key.setEchoMode(QLineEdit.EchoMode.Password)
        grid.addWidget(self.entry_key, 0, 1)
        
        grid.addWidget(QLabel("Local URL:"), 1, 0)
        self.entry_url = QLineEdit()
        grid.addWidget(self.entry_url, 1, 1)
        layout.addLayout(grid)
        
        # Group: Appearance
        layout.addWidget(QLabel("Appearance"))
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(list(THEMES.keys()))
        self.theme_combo.setCurrentText(cfg.theme)
        self.theme_combo.currentTextChanged.connect(self.on_theme_changed)
        layout.addWidget(self.theme_combo)
        
        layout.addStretch()
        
        btn_save = QPushButton("Save Settings")
        btn_save.setProperty("cssClass", "primary")
        btn_save.clicked.connect(self.save_config)
        layout.addWidget(btn_save)
        
        self.tabs.addTab(tab, "  Settings")

    # --- LOGIC METHODS (Mostly unchanged, just linked to new UI elements) ---
    def update_dashboard(self):
        try:
            total, used, free = shutil.disk_usage(cfg.target_root if os.path.exists(cfg.target_root) else "C:\\")
            u = cfg.size_unit
            div = 1024**3 if u == "GB" else 1024**2
            
            self.lbl_total.setText(f"{total/div:.1f} {u}")
            self.lbl_used.setText(f"{used/div:.1f} {u}")
            self.lbl_free.setText(f"{free/div:.1f} {u}")
        except Exception as e:
            log.error(f"Dash Error: {e}")

    def start_scan(self):
        self.setEnabled(False)
        self.scan_table.setRowCount(0)
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
        self.scan_table.setSortingEnabled(False)
        self.scan_table.setRowCount(len(self.classified_items))
        for i, c in enumerate(self.classified_items):
            # Name
            self.scan_table.setItem(i, 0, QTableWidgetItem(c.item.name))
            
            # Size
            size_item = NumericSortItem(self.format_size(c.item.size_gb))
            size_item.setData(Qt.ItemDataRole.UserRole, c.item.size_gb)
            self.scan_table.setItem(i, 1, size_item)
            
            # Type
            self.scan_table.setItem(i, 2, QTableWidgetItem(c.item.type))
            
            # Category (Pill)
            cat_item = QTableWidgetItem(c.category)
            # Simple colorizing for now (Advanced pill needs Delegate)
            if c.category == "SAFE":
                cat_item.setForeground(QColor("#06D6A0")) # Green
            elif c.category == "FORBIDDEN":
                cat_item.setForeground(QColor("#E63946")) # Red
            self.scan_table.setItem(i, 3, cat_item)
            
            # Reason
            self.scan_table.setItem(i, 4, QTableWidgetItem(c.reason))
        self.scan_table.setSortingEnabled(True)

    def refresh_plan_table(self):
        self.plan_table.setSortingEnabled(False)
        safe = [c for c in self.classified_items if c.category == "SAFE"]
        self.plan_table.setRowCount(len(safe))
        for i, c in enumerate(safe):
            chk = QTableWidgetItem()
            chk.setFlags(Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled)
            chk.setCheckState(Qt.CheckState.Unchecked)
            chk.setData(Qt.ItemDataRole.UserRole, c)
            self.plan_table.setItem(i, 0, chk)
            self.plan_table.setItem(i, 1, QTableWidgetItem(c.item.name))
            self.plan_table.setItem(i, 2, QTableWidgetItem(self.format_size(c.item.size_gb)))
            self.plan_table.setItem(i, 3, QTableWidgetItem(c.item.path))
        self.plan_table.setSortingEnabled(True)
    
    # ... Kept filtering/execution logic same ...
    def filter_scan_table(self, text):
        search = text.lower()
        for i in range(self.scan_table.rowCount()):
            item = self.scan_table.item(i, 0)
            if item and search in item.text().lower():
                self.scan_table.setRowHidden(i, False)
            else:
                self.scan_table.setRowHidden(i, True)

    def execute_moves(self):
        items = []
        for i in range(self.plan_table.rowCount()):
            it = self.plan_table.item(i, 0)
            if it.checkState() == Qt.CheckState.Checked:
                items.append(it.data(Qt.ItemDataRole.UserRole))
        
        if not items:
            QMessageBox.warning(self, "No Selection", "Select items to move.")
            return

        if QMessageBox.question(self, "Confirm", f"Move {len(items)} items?") != QMessageBox.StandardButton.Yes:
            return

        self.setEnabled(False)
        self.move_progress.setValue(0)
        self.move_worker = MoveWorker(items, cfg.target_root)
        self.move_worker.progress_percent.connect(self.move_progress.setValue)
        self.move_worker.finished.connect(self.on_move_finished)
        self.move_worker.start()

    def on_move_finished(self, success, msg):
        self.setEnabled(True)
        if success: QMessageBox.information(self, "Done", msg)
        else: QMessageBox.critical(self, "Error", msg)
        self.load_history()

    def load_history(self):
        moves = storage.get_history()
        self.history_table.setRowCount(len(moves))
        for i, row in enumerate(moves):
            # mid, src, tgt, time, status, cat
            self.history_table.setItem(i, 0, QTableWidgetItem(str(row[0])))
            self.history_table.setItem(i, 1, QTableWidgetItem(row[1]))
            self.history_table.setItem(i, 2, QTableWidgetItem(row[2]))
            
            stat = row[4]
            # status item styling
            s_item = QTableWidgetItem(stat)
            if stat == "OK": s_item.setForeground(QColor("#06D6A0"))
            else: s_item.setForeground(QColor("#E63946"))
            self.history_table.setItem(i, 3, s_item)

            if stat == "OK":
                btn = QPushButton("Rollback")
                btn.setFlat(True)
                btn.setStyleSheet("color: #E63946; font-weight: bold; text-decoration: underline;")
                btn.clicked.connect(lambda _, m=row[0]: self.do_rollback(m))
                self.history_table.setCellWidget(i, 4, btn)
            else:
                self.history_table.setItem(i, 4, QTableWidgetItem("-"))

    def do_rollback(self, mid):
        try:
            rollback_move(mid)
            QMessageBox.information(self, "Success", "Rollback complete.")
            self.load_history()
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    def ask_ai_scan(self):
        if not self.classified_items:
            QMessageBox.warning(self, "Empty", "Scan first.")
            return
        self.chat_area.append("🤖 Asking AI...")
        self.setEnabled(False)
        self.ai_worker = AIWorker(self.classified_items)
        self.ai_worker.finished.connect(self.on_ai_finished)
        self.ai_worker.start()

    def on_ai_finished(self, resp):
        self.setEnabled(True)
        self.chat_area.append(f"\n{resp}\n")

    def scan_nvidia_junk(self):
        cleaner = NvidiaCleaner()
        self.nvidia_junk_items, size = cleaner.scan()
        self.clean_list.setRowCount(len(self.nvidia_junk_items))
        for i, it in enumerate(self.nvidia_junk_items):
            self.clean_list.setItem(i, 0, QTableWidgetItem(it["path"]))
            self.clean_list.setItem(i, 1, QTableWidgetItem(self.format_size(it["size"]/(1024**3))))
            self.clean_list.setItem(i, 2, QTableWidgetItem("Found"))
        self.lbl_clean_summary.setText(f"Found {len(self.nvidia_junk_items)} items ({self.format_size(size/(1024**3))}).")

    def clean_nvidia_junk(self):
        if not self.nvidia_junk_items: return
        self.setEnabled(False)
        self.clean_progress.setRange(0, 0)
        self.clean_worker = CleanWorker(self.nvidia_junk_items)
        self.clean_worker.finished.connect(self.on_clean_finished)
        self.clean_worker.start()

    def on_clean_finished(self, d, f, b):
        self.setEnabled(True)
        self.clean_progress.setRange(0, 100)
        self.clean_progress.setValue(100)
        QMessageBox.information(self, "Cleaned", f"Deleted {d}, Failed {f}")
        self.scan_nvidia_junk()

    def on_theme_changed(self, t):
        cfg.theme = t
        self.apply_theme()

    def load_config_to_ui(self):
        self.entry_root.setText(cfg.target_root)
        self.entry_key.setText(cfg.cloud_config.get("api_key", ""))
        self.entry_url.setText(cfg.local_config.get("base_url", ""))
        idx = self.combo_mode.findText(cfg.llm_mode)
        if idx >= 0: self.combo_mode.setCurrentIndex(idx)

    def save_config(self):
        cfg.target_root = self.entry_root.text()
        cfg.llm_mode = self.combo_mode.currentText()
        cfg.theme = self.theme_combo.currentText()
        cfg.set("cloud", {**cfg.cloud_config, "api_key": self.entry_key.text()})
        cfg.set("local", {**cfg.local_config, "base_url": self.entry_url.text()})
        QMessageBox.information(self, "Saved", "Settings saved.")

    def format_size(self, size_gb):
        if cfg.size_unit == "MB": return f"{size_gb*1024:.1f} MB"
        return f"{size_gb:.2f} GB"
