import json
from pathlib import Path
from smolagents import Tool

class RemediationTool(Tool):
    name = "remediation_tool"
    description = (
        "Takes three inputs: 'type', 'pattern', and 'remediation', converts them into a JSON object, "
        "and appends the object to the approved_remediations.json file."
    )
    inputs = {
        "type": {
            "type": "string",
            "description": "The type of the mismatch (e.g., 'TAX_RATE mismatch')."
        },
        "pattern": {
            "type": "string",
            "description": "The pattern related to the mismatch (e.g., 'tax differs')."
        },
        "remediation": {
            "type": "string",
            "description": "The remediation action to resolve the mismatch."
        }
    }
    output_type = "string"

    def forward(self, type: str, pattern: str, remediation: str) -> str:
        """
        Converts the inputs into a JSON object and appends it to the approved_remediations.json file.
        """
        # Create the remediation entry
        entry = {
            "type": type,
            "pattern": [pattern],  # Ensure pattern is always a list
            "remediation": remediation.strip()
        }

        # Path to the approved remediations file
        approved_remediations_path = Path("data/approved_remediations.json")

        # Ensure the file exists, if not, initialize it as an empty list
        if not approved_remediations_path.exists():
            with open(approved_remediations_path, "w") as f:
                json.dump([], f)

        # Read existing remediations from the file
        with open(approved_remediations_path, "r") as f:
            remediations = json.load(f)

        # Append the new remediation entry
        remediations.append(entry)

        # Write the updated list back to the file
        with open(approved_remediations_path, "w") as f:
            json.dump(remediations, f, indent=2)

        print(f"[remediation_tool] Remediation successfully added to '{approved_remediations_path}'")
        return str(approved_remediations_path)
