import os
from PySide6.QtCore import Qt, Signal, Slot
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QTableWidget, QTableWidgetItem, QHeaderView, QGroupBox, QFrame,
    QTabWidget, QSplitter, QCheckBox
)
from PySide6.QtGui import QFont, QColor

from ui.console_panel import ConsolePanel
from ui.debug_panel import DebugPanel
from ui.template_manager import TemplateManager
from ui.settings import SettingsPage
from ui.workflow_editor import WorkflowEditor

class StatisticsPanel(QFrame):
    """
    Real-time Statistics Panel displaying rule and match KPI analytics.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(
            "QFrame { background-color: #1F2937; border: 1px solid #374151; border-radius: 10px; padding: 10px; }"
            "QLabel { color: #D1D5DB; font-family: 'Segoe UI'; }"
        )
        self.init_ui()

    def init_ui(self):
        layout = QHBoxLayout(self)
        self.rules_lbl = QLabel("<b>Rules:</b> 0")
        self.running_lbl = QLabel("<b>🟢 Running:</b> 0")
        self.paused_lbl = QLabel("<b>🟡 Paused:</b> 0")
        self.failed_lbl = QLabel("<b>🔴 Failed:</b> 0")
        self.clicks_lbl = QLabel("<b>Clicks Today:</b> 0")
        self.matches_lbl = QLabel("<b>Matches Today:</b> 0")
        self.success_lbl = QLabel("<b>Success Executions:</b> 0")

        for lbl in [self.rules_lbl, self.running_lbl, self.paused_lbl, self.failed_lbl, self.clicks_lbl, self.matches_lbl, self.success_lbl]:
            lbl.setFont(QFont("Segoe UI", 9))
            layout.addWidget(lbl)

    def update_statistics(self, rules_count, running_count, paused_count, failed_count, clicks, matches, success):
        self.rules_lbl.setText(f"<b>Rules:</b> {rules_count}")
        self.running_lbl.setText(f"<b>🟢 Running:</b> {running_count}")
        self.paused_lbl.setText(f"<b>🟡 Paused:</b> {paused_count}")
        self.failed_lbl.setText(f"<b>🔴 Failed:</b> {failed_count}")
        self.clicks_lbl.setText(f"<b>Clicks Today:</b> {clicks}")
        self.matches_lbl.setText(f"<b>Matches Today:</b> {matches}")
        self.success_lbl.setText(f"<b>Success:</b> {success}")


class NativeDashboard(QWidget):
    """
    Main Application Dashboard Layout for the Calibrated Automation Studio.
    Includes Top Toolbar, Statistics Panel, Advanced Rule Table, and a
    Right Column Tab Widget housing Console, Debugger, Templates, Settings, and Workflow pipeline.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Calibrated Native Automation Studio")
        self.resize(1100, 700)
        self.setStyleSheet(
            "QWidget { background-color: #111827; color: #F9FAFB; font-family: 'Segoe UI'; }"
            "QPushButton { background-color: #10B981; border: none; border-radius: 8px; color: white; padding: 8px 16px; font-weight: bold; }"
            "QPushButton:hover { background-color: #059669; }"
            "QPushButton:pressed { background-color: #047857; }"
            "QTableWidget { background-color: #1F2937; border: 1px solid #374151; border-radius: 8px; color: #F9FAFB; gridline-color: #374151; }"
            "QHeaderView::section { background-color: #111827; color: #D1D5DB; padding: 6px; font-weight: bold; border: 1px solid #374151; }"
            "QTabWidget::pane { border: 1px solid #374151; background: #111827; border-radius: 4px; }"
            "QTabBar::tab { background: #1F2937; color: #D1D5DB; padding: 8px 12px; border-top-left-radius: 4px; border-top-right-radius: 4px; margin-right: 2px; }"
            "QTabBar::tab:selected { background: #10B981; color: white; }"
        )
        self.init_ui()

    def init_ui(self):
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(15, 15, 15, 15)
        self.main_layout.setSpacing(12)

        # 1. Top Toolbar Layout
        self.toolbar_layout = QHBoxLayout()
        self.teach_btn = QPushButton("🎯 Teach Target (F10)")
        self.teach_btn.setStyleSheet("background-color: #3B82F6;") # Blue accent

        self.teach_cursor_btn = QPushButton("📍 Teach Cursor (F11)")
        self.teach_cursor_btn.setStyleSheet("background-color: #6366F1;")

        self.start_btn = QPushButton("▶ Start Monitor (F8)")
        self.start_btn.setStyleSheet("background-color: #10B981;") # Emerald accent

        self.stop_btn = QPushButton("⏸ Stop Monitor (F9)")
        self.stop_btn.setStyleSheet("background-color: #EF4444;") # Red accent

        self.calibrate_btn = QPushButton("⚙️ Calibrate")
        self.calibrate_btn.setStyleSheet("background-color: #4B5563;")

        self.move_only_chk = QCheckBox("Move Only (No Click) Debug Mode")
        self.move_only_chk.setToolTip("Moves the mouse cursor to targets and draws highlights for verification without clicking")
        self.move_only_chk.setStyleSheet("QCheckBox { font-weight: bold; color: #10B981; }")

        self.toolbar_layout.addWidget(self.teach_btn)
        self.toolbar_layout.addWidget(self.teach_cursor_btn)
        self.toolbar_layout.addWidget(self.start_btn)
        self.toolbar_layout.addWidget(self.stop_btn)
        self.toolbar_layout.addWidget(self.calibrate_btn)
        self.toolbar_layout.addWidget(self.move_only_chk)
        self.toolbar_layout.addStretch()
        self.main_layout.addLayout(self.toolbar_layout)

        # 2. Statistics Panel
        self.stats_panel = StatisticsPanel(self)
        self.main_layout.addWidget(self.stats_panel)

        # 3. Horizontal Splitter separating Rule Table and Right Tab Panels
        self.splitter = QSplitter(Qt.Horizontal, self)

        # Left widget: Rule Table
        self.left_container = QWidget()
        left_layout = QVBoxLayout(self.left_container)
        left_layout.setContentsMargins(0, 0, 0, 0)

        self.rules_table = QTableWidget()
        self.rules_table.setColumnCount(9)
        self.rules_table.setHorizontalHeaderLabels([
            "✓", "Rule Name", "Status", "Trigger", "Search Region", "Last Match", "Last Click", "Success Rate", "Actions"
        ])
        self.rules_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        left_layout.addWidget(self.rules_table)
        self.splitter.addWidget(self.left_container)

        # Right widget: Studio Tabs
        self.right_tabs = QTabWidget()

        # Tab 1: Colored Action Logger
        self.console_panel = ConsolePanel(self)
        self.right_tabs.addTab(self.console_panel, "📝 Console")

        # Expose legacy logging slot and clear button for backward-compatibility with main.Coordinator
        self.log_output = self.console_panel.log_text
        self.clear_logs_btn = self.console_panel.clear_btn

        # Tab 2: Live Bounding Box & Click Debugger
        self.debug_panel = DebugPanel(self)
        self.right_tabs.addTab(self.debug_panel, "🔍 Debugger")

        # Tab 3: Saved Templates Assets Manager
        self.template_manager = TemplateManager(self)
        self.right_tabs.addTab(self.template_manager, "📁 Templates")

        # Tab 4: Performance & Mouse Clicking Settings
        self.settings_page = SettingsPage(self)
        self.right_tabs.addTab(self.settings_page, "⚙️ Settings")

        # Tab 5: Workflow editor pipeline
        self.workflow_editor = WorkflowEditor(self)
        self.right_tabs.addTab(self.workflow_editor, "🛠️ Workflow")

        self.splitter.addWidget(self.right_tabs)
        self.splitter.setSizes([600, 500])
        self.main_layout.addWidget(self.splitter)

    def append_log(self, text: str):
        # Fallback helper logging slot
        self.console_panel.log_info(text)
