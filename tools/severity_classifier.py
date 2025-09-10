# tools/severity_classifier_tool.py
import json
from pathlib import Path
from smolagents import Tool

class SeverityClassifierTool(Tool):
    name = "severity_classifier"
    description = (
        "Persist agent-generated severity insights as JSON. "
        "Input must be a JSON string representing a list of objects: "
        '[{"id":"#001","severity":"none|low|medium|high","explanation":"..."}]. '
        "Example input: "
        '[{"id":"#001","severity":"none","explanation":"No discrepancies."},'
        ' {"id":"#002","severity":"medium","explanation":"payment_date mismatch; net +6.6%."}]'
    )
    inputs = {
        "insights_json": {
            "type": "string",
            "description": "A JSON string: list of {id, severity, explanation}."
        }
    }
    output_type = "string"

    def forward(self, insights_json: str) -> str:
        out_path = Path("data/severity_results.json")

        try:
            data = json.loads(insights_json)
        except Exception as e:
            raise ValueError(f"Insights must be valid JSON. Parse error: {e}")

        if not isinstance(data, list):
            raise ValueError("Insights must be a JSON list.")

        allowed_sev = {"none", "low", "medium", "high"}
        seen_ids = set()
        for i, row in enumerate(data):
            if not isinstance(row, dict):
                raise ValueError(f"Item {i} must be an object.")
            missing = {"id","severity","explanation"} - set(row.keys())
            if missing:
                raise ValueError(f"Item {i} missing keys: {missing}")
            if not isinstance(row["id"], str) or not row["id"].startswith("#"):
                raise ValueError(f"Item {i} invalid id: {row['id']!r}")
            if row["severity"] not in allowed_sev:
                raise ValueError(f"Item {i} invalid severity: {row['severity']!r}")
            if not isinstance(row["explanation"], str):
                raise ValueError(f"Item {i} explanation must be string.")

            if row["id"] in seen_ids:
                raise ValueError(f"Duplicate id found: {row['id']}")
            seen_ids.add(row["id"])

        out_path.write_text(json.dumps(data, indent=2))
        print(f"[severity_classifier] Saved '{out_path}'")
        return str(out_path)
