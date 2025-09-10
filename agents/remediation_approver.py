from smolagents import CodeAgent, LiteLLMModel
import json
from pathlib import Path
from tools.remediation_tool import RemediationTool  # Assuming the tool is correctly imported
from tools.csv_updater_tool import CSVUpdaterTool

class RemediationApprovalAgent(CodeAgent):
    def __init__(self, approved_remediations_path: str):
        model = LiteLLMModel(
            model_id="gpt-4o-mini",  # Example; replace with your model ID
            api_base="https://api.openai.com/v1",
            api_key=None,  # Make sure your API key is set correctly (usually in .env)
        )
        super().__init__(
            model=model,
            tools=[RemediationTool(), CSVUpdaterTool()],  # Ensure the tool is passed to the agent
            instructions=(
                "You are tasked with processing an accepted remediation, converting it into the correct "
                "format for the knowledge base, and appending it to the approved remediations file." \
                "Then you will update the paired_transposed_cleaned.csv file based on the approved remediation details, "
                "using the csv_updater tool."
            ),
            add_base_tools=False,
            additional_authorized_imports=["json", "pandas", "pathlib"],
            verbosity_level = 0,
            max_steps=6
        )

