import os
import time
from PySide6.QtCore import QObject, Qt, Slot
from PySide6.QtWidgets import QTableWidgetItem, QCheckBox, QPushButton

from automation_studio.models.automation_rule import MacroRule
from automation_studio.workers.stress_test_worker import StressTestWorker

class RuleController(QObject):
    """
    Stage-based Rule Controller.
    Manages Macro Rules lists, database-like snapshot states, Rules UI tables rendering,
    rule editing/replaces, deletions, and triggering background Stress Tests.
    """
    def __init__(self, dashboard, rules: list, lock, click_engine, capture_engine, save_rules_cb=None):
        super().__init__()
        self.dashboard = dashboard
        self.rules = rules
        self.lock = lock
        self.click_engine = click_engine
        self.capture_engine = capture_engine
        self.save_rules_cb = save_rules_cb

        # State tracker for replace actions
        self.replacing_rule_id = None
        self.stress_worker = None

    def refresh_rules_table(self):
        rules_snapshot = []
        with self.lock:
            rules_snapshot = list(self.rules)

        rules_count = len(rules_snapshot)
        running_count = sum(1 for r in rules_snapshot if r.active)
        paused_count = sum(1 for r in rules_snapshot if not r.active)
        failed_count = sum(1 for r in rules_snapshot if r.failures_count > 0)
        clicks_today = sum(r.clicks_count for r in rules_snapshot)
        matches_today = sum(r.matches_count for r in rules_snapshot)

        self.dashboard.stats_panel.update_statistics(
            rules_count, running_count, paused_count, failed_count, clicks_today, matches_today, clicks_today
        )

        self.dashboard.rules_table.setRowCount(len(rules_snapshot))
        for row, rule in enumerate(rules_snapshot):
            chk = QCheckBox()
            chk.setChecked(rule.active)

            def make_active_updater(target_rule):
                def updater(state):
                    target_rule.active = (state == Qt.Checked)
                    print(f"[RuleController] Updating Rule active status: {target_rule.name} -> {target_rule.active}")
                    if self.save_rules_cb:
                        self.save_rules_cb()
                    self.refresh_rules_table()
                return updater

            chk.stateChanged.connect(make_active_updater(rule))
            self.dashboard.rules_table.setCellWidget(row, 0, chk)

            self.dashboard.rules_table.setItem(row, 1, QTableWidgetItem(rule.name))

            status_str = "🟢 Running" if rule.active else "🟡 Paused"
            if rule.failures_count > 0:
                status_str = "🔴 Error"
            self.dashboard.rules_table.setItem(row, 2, QTableWidgetItem(status_str))
            self.dashboard.rules_table.setItem(row, 3, QTableWidgetItem(rule.trigger_type))
            self.dashboard.rules_table.setItem(row, 4, QTableWidgetItem(rule.search_region))

            last_match_str = f"{rule.matches_count} matches" if rule.matches_count > 0 else "Never"
            self.dashboard.rules_table.setItem(row, 5, QTableWidgetItem(last_match_str))

            last_click_str = f"{rule.clicks_count} clicks" if rule.clicks_count > 0 else "Never"
            self.dashboard.rules_table.setItem(row, 6, QTableWidgetItem(last_click_str))

            success_pct = "100.0%"
            if rule.failures_count + rule.clicks_count > 0:
                rate = (rule.clicks_count / (rule.clicks_count + rule.failures_count)) * 100.0
                success_pct = f"{rate:.1f}%"
            self.dashboard.rules_table.setItem(row, 7, QTableWidgetItem(success_pct))

            del_btn = QPushButton("🗑️ Delete")
            def make_rule_deleter(target_rule_id):
                return lambda: self.delete_rule(target_rule_id)
            del_btn.clicked.connect(make_rule_deleter(rule.id_str))
            self.dashboard.rules_table.setCellWidget(row, 8, del_btn)

        print("[Dashboard] Rules table refreshed.")

    def delete_rule(self, rule_id: str):
        with self.lock:
            rule_to_remove = None
            for r in self.rules:
                if r.id_str == rule_id or (r.template_path and os.path.basename(r.template_path) == rule_id):
                    rule_to_remove = r
                    break
            if rule_to_remove:
                self.rules.remove(rule_to_remove)
                try:
                    if os.path.exists(rule_to_remove.template_path):
                        os.remove(rule_to_remove.template_path)
                except Exception:
                    pass
                self.dashboard.append_log(f"[-] [RuleController] Deleted rule: '{rule_to_remove.name}'")
        if self.save_rules_cb:
            self.save_rules_cb()
        self.refresh_rules_table()
        self.dashboard.template_manager.refresh_templates()

    def handle_manager_replace(self, trigger_teach_cb):
        item = self.dashboard.template_manager.list_widget.currentItem()
        if item:
            filename = item.text()
            target_rule = None
            with self.lock:
                for rule in self.rules:
                    if rule.template_path and os.path.basename(rule.template_path) == filename:
                        target_rule = rule
                        break
            if target_rule:
                self.dashboard.append_log(f"[*] [RuleController] Re-triggering Teach Mode to replace asset for rule '{target_rule.name}'...")
                self.replacing_rule_id = target_rule.id_str
                trigger_teach_cb()
            else:
                self.dashboard.append_log("[!] Warning: No matching rule found for this template asset.")

    def trigger_stress_test(self):
        row = self.dashboard.rules_table.currentRow()
        if row >= 0:
            with self.lock:
                rule = self.rules[row]

            # Prevent overlapping stress tests
            if self.stress_worker and self.stress_worker.isRunning():
                self.dashboard.append_log("[⚠️] Stress test already running. Please wait.")
                return

            self.stress_worker = StressTestWorker(rule, self.capture_engine)
            self.stress_worker.log_signal.connect(self.dashboard.append_log)
            self.stress_worker.finished_signal.connect(self.dashboard.append_log)
            self.stress_worker.start()
        else:
            self.dashboard.append_log("[!] Please select a rule in the table first before running the Stress Test.")
