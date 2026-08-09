class RuleStorage:
    """
    Placeholder helper class to manage JSON rule templates imports/exports.
    """
    @staticmethod
    def export_rule_to_json(rule) -> str:
        import json
        return json.dumps({
            "id_str": rule.id_str, "name": rule.name, "trigger_type": rule.trigger_type, "action": rule.action
        })
