import sqlite3
import json
import threading
from typing import List, Dict, Any, Tuple, Optional

class SQLiteManager:
    """
    Centralized, thread-safe manager for the SQLite embedded storage database.
    Responsible for CRUD, Statistics tracking, Calibration configuration, and Rule/Workflow states.
    """
    def __init__(self, db_path: str = "automation.db"):
        self.db_path = db_path
        self._lock = threading.Lock()
        self.initialize_tables()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def initialize_tables(self):
        """
        Creates DB tables automatically on initialization if they do not exist.
        """
        with self._lock:
            conn = self._get_connection()
            cursor = conn.cursor()

            # 1. Rules table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS rules (
                    id_str TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    trigger_type TEXT NOT NULL,
                    action TEXT NOT NULL,
                    cooldown REAL DEFAULT 1.0,
                    threshold REAL DEFAULT 0.90,
                    template_path TEXT,
                    click_steps TEXT, -- JSON array of steps
                    abs_x INTEGER,
                    abs_y INTEGER,
                    window_title TEXT,
                    window_offset_x INTEGER,
                    window_offset_y INTEGER,
                    search_region TEXT DEFAULT 'Entire Screen',
                    anchor_rule_id TEXT,
                    train_x INTEGER,
                    train_y INTEGER,
                    train_w INTEGER,
                    train_h INTEGER,
                    click_offset_x INTEGER,
                    click_offset_y INTEGER,
                    active INTEGER DEFAULT 1
                )
            """)

            # 2. Calibration table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS calibration (
                    key TEXT PRIMARY KEY,
                    correction_x REAL DEFAULT 0.0,
                    correction_y REAL DEFAULT 0.0
                )
            """)

            # Insert default calibration
            cursor.execute("""
                INSERT OR IGNORE INTO calibration (key, correction_x, correction_y)
                VALUES ('primary', 0.0, 0.0)
            """)

            # 3. Executions / Statistics table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS executions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    rule_id TEXT NOT NULL,
                    status TEXT NOT NULL,
                    confidence REAL,
                    duration_ms INTEGER,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)

            conn.commit()
            conn.close()

    def add_rule(self, rule_data: Dict[str, Any]) -> bool:
        """
        Saves a new rule or overwrites an existing one (insert or replace).
        """
        with self._lock:
            try:
                conn = self._get_connection()
                cursor = conn.cursor()

                steps_json = json.dumps(rule_data.get("click_steps", []))

                cursor.execute("""
                    INSERT OR REPLACE INTO rules (
                        id_str, name, trigger_type, action, cooldown, threshold, template_path, click_steps,
                        abs_x, abs_y, window_title, window_offset_x, window_offset_y, search_region,
                        anchor_rule_id, train_x, train_y, train_w, train_h, click_offset_x, click_offset_y, active
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    rule_data["id_str"], rule_data["name"], rule_data["trigger_type"], rule_data["action"],
                    rule_data.get("cooldown", 1.0), rule_data.get("threshold", 0.90), rule_data.get("template_path", ""),
                    steps_json, rule_data.get("abs_x"), rule_data.get("abs_y"), rule_data.get("window_title", ""),
                    rule_data.get("window_offset_x"), rule_data.get("window_offset_y"), rule_data.get("search_region", "Entire Screen"),
                    rule_data.get("anchor_rule_id"), rule_data.get("train_x"), rule_data.get("train_y"),
                    rule_data.get("train_w"), rule_data.get("train_h"), rule_data.get("click_offset_x"),
                    rule_data.get("click_offset_y"), int(rule_data.get("active", True))
                ))

                conn.commit()
                conn.close()
                return True
            except Exception as e:
                print(f"[SQLite] Error saving rule: {e}")
                return False

    def get_all_rules(self) -> List[Dict[str, Any]]:
        """
        Fetches all registered rules from database.
        """
        with self._lock:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM rules")
            rows = cursor.fetchall()

            rules_list = []
            for row in rows:
                rule_dict = dict(row)
                rule_dict["click_steps"] = json.loads(rule_dict["click_steps"] or "[]")
                rule_dict["active"] = bool(rule_dict["active"])
                rules_list.append(rule_dict)

            conn.close()
            return rules_list

    def delete_rule(self, rule_id: str) -> bool:
        """
        Deletes a rule by its ID.
        """
        with self._lock:
            try:
                conn = self._get_connection()
                cursor = conn.cursor()
                cursor.execute("DELETE FROM rules WHERE id_str = ?", (rule_id,))
                conn.commit()
                conn.close()
                return True
            except Exception as e:
                print(f"[SQLite] Error deleting rule: {e}")
                return False

    def save_calibration(self, corr_x: float, corr_y: float) -> bool:
        """
        Saves the global interactive target calibration factor offsets.
        """
        with self._lock:
            try:
                conn = self._get_connection()
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT OR REPLACE INTO calibration (key, correction_x, correction_y)
                    VALUES ('primary', ?, ?)
                """, (corr_x, corr_y))
                conn.commit()
                conn.close()
                return True
            except Exception as e:
                print(f"[SQLite] Error saving calibration factors: {e}")
                return False

    def get_calibration(self) -> Tuple[float, float]:
        """
        Loads the pre-saved calibration corrections (fallback to 0.0, 0.0).
        """
        with self._lock:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT correction_x, correction_y FROM calibration WHERE key = 'primary'")
            row = cursor.fetchone()
            conn.close()
            if row:
                return float(row["correction_x"]), float(row["correction_y"])
            return 0.0, 0.0

    def log_execution(self, rule_id: str, status: str, conf: Optional[float] = None, duration_ms: int = 0):
        """
        Appends a detailed pipeline execution diagnostic to stats log.
        """
        with self._lock:
            try:
                conn = self._get_connection()
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO executions (rule_id, status, confidence, duration_ms)
                    VALUES (?, ?, ?, ?)
                """, (rule_id, status, conf, duration_ms))
                conn.commit()
                conn.close()
            except Exception as e:
                print(f"[SQLite] Error logging execution: {e}")
