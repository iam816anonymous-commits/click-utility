import unittest
import os
from automation_studio.database.sqlite_manager import SQLiteManager

class TestSQLiteManager(unittest.TestCase):
    """
    Unit tests verifying SQLite database CRUD, schema, and calibration persistence.
    """
    def setUp(self):
        # Use an in-memory or temp sqlite file for testing
        self.db_path = "test_automation.db"
        self.manager = SQLiteManager(db_path=self.db_path)

    def tearDown(self):
        if os.path.exists(self.db_path):
            try:
                os.remove(self.db_path)
            except Exception:
                pass

    def test_initialize_tables_and_calibration_defaults(self):
        cx, cy = self.manager.get_calibration()
        self.assertEqual(cx, 0.0)
        self.assertEqual(cy, 0.0)

    def test_rule_crud_operations(self):
        rule_data = {
            "id_str": "rule_test_1",
            "name": "Click Analytics Button",
            "trigger_type": "Image Template Match",
            "action": "Left Click",
            "cooldown": 2.5,
            "threshold": 0.95,
            "template_path": "targets/analytics.png",
            "click_offset_x": 10,
            "click_offset_y": 15,
            "search_region": "Entire Screen",
            "active": True
        }

        # Add rule
        success = self.manager.add_rule(rule_data)
        self.assertTrue(success)

        # Retrieve all
        rules = self.manager.get_all_rules()
        self.assertEqual(len(rules), 1)
        self.assertEqual(rules[0]["id_str"], "rule_test_1")
        self.assertEqual(rules[0]["name"], "Click Analytics Button")
        self.assertEqual(rules[0]["cooldown"], 2.5)
        self.assertEqual(rules[0]["threshold"], 0.95)

        # Delete rule
        del_success = self.manager.delete_rule("rule_test_1")
        self.assertTrue(del_success)

        rules_after = self.manager.get_all_rules()
        self.assertEqual(len(rules_after), 0)

    def test_save_and_get_calibration(self):
        success = self.manager.save_calibration(5.5, -2.0)
        self.assertTrue(success)

        cx, cy = self.manager.get_calibration()
        self.assertEqual(cx, 5.5)
        self.assertEqual(cy, -2.0)
