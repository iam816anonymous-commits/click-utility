import threading
from typing import List, Dict, Any, Optional

from automation_studio.database.sqlite_manager import SQLiteManager
from automation_studio.models.automation_rule import MacroRule

class RuleManager:
    """
    Central Manager for CRUD and persistence of visual macro rules.
    Acts as the service layer between Controllers/UI and the SQLite storage.
    Singleton Pattern: guarantees only one instance resides in memory.
    """
    _instance = None
    _lock = threading.Lock()

    @classmethod
    def get_instance(cls, db_manager: Optional[SQLiteManager] = None):
        with cls._lock:
            if cls._instance is None:
                if db_manager is None:
                    db_manager = SQLiteManager()
                cls._instance = cls(db_manager)
            return cls._instance

    def __init__(self, db_manager: SQLiteManager):
        if hasattr(self, "_initialized"):
            return
        self.db_manager = db_manager
        self.rules: List[MacroRule] = []
        self._lock = threading.Lock()
        self._initialized = True
        self.load_all_rules()

    def load_all_rules(self):
        """
        Loads all rules from the SQLite database at boot time.
        """
        with self._lock:
            self.rules.clear()
            rules_data = self.db_manager.get_all_rules()
            for d in rules_data:
                rule = MacroRule(
                    id_str=d["id_str"], name=d["name"], trigger_type=d["trigger_type"], action=d["action"],
                    cooldown=d["cooldown"], threshold=d["threshold"], template_path=d["template_path"],
                    click_steps=d["click_steps"], abs_x=d.get("abs_x"), abs_y=d.get("abs_y"),
                    window_title=d.get("window_title"), window_offset_x=d.get("window_offset_x"), window_offset_y=d.get("window_offset_y"),
                    search_region=d.get("search_region", "Entire Screen"), anchor_rule_id=d.get("anchor_rule_id"),
                    train_x=d.get("train_x"), train_y=d.get("train_y"), train_w=d.get("train_w"), train_h=d.get("train_h"),
                    click_offset_x=d.get("click_offset_x"), click_offset_y=d.get("click_offset_y")
                )
                rule.active = d.get("active", True)
                self.rules.append(rule)
            print(f"[RuleManager] Successfully loaded {len(self.rules)} rules from database.")

    def add_rule(self, rule: MacroRule) -> bool:
        """
        Registers a new rule and writes it cleanly to SQLite.
        """
        rule_data = {
            "id_str": rule.id_str, "name": rule.name, "trigger_type": rule.trigger_type, "action": rule.action,
            "cooldown": rule.cooldown, "threshold": rule.threshold, "template_path": rule.template_path,
            "click_steps": rule.click_steps, "abs_x": rule.abs_x, "abs_y": rule.abs_y, "window_title": rule.window_title,
            "window_offset_x": rule.window_offset_x, "window_offset_y": rule.window_offset_y,
            "search_region": rule.search_region, "anchor_rule_id": rule.anchor_rule_id, "train_x": rule.train_x,
            "train_y": rule.train_y, "train_w": rule.train_w, "train_h": rule.train_h,
            "click_offset_x": rule.click_offset_x, "click_offset_y": rule.click_offset_y, "active": rule.active
        }
        success = self.db_manager.add_rule(rule_data)
        if success:
            with self._lock:
                # Remove if existing duplicate ID
                self.rules = [r for r in self.rules if r.id_str != rule.id_str]
                self.rules.append(rule)
            print(f"[RuleManager] Successfully registered and persisted rule: '{rule.name}'")
        return success

    def delete_rule(self, rule_id: str) -> bool:
        """
        Removes a rule by its ID from the rules list and database.
        """
        success = self.db_manager.delete_rule(rule_id)
        if success:
            with self._lock:
                self.rules = [r for r in self.rules if r.id_str != rule_id]
            print(f"[RuleManager] Successfully deleted rule ID '{rule_id}' from database.")
        return success
