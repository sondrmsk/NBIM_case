from smolagents import CodeAgent, LiteLLMModel
import json
from pathlib import Path
from tools.email_tool import EmailTool  # Assuming you have this custom tool for email
from tools.json_printer import JSONPrinterTool

class EmailAgent(CodeAgent):
    def __init__(self):
        model = LiteLLMModel(
            model_id="gpt-4o-mini",  # Example model ID; replace with the appropriate one
            api_base="https://api.openai.com/v1",
            api_key=None,  # Ensure your API key is correctly set (via .env or directly)
        )

        # Load the severity results from the JSON file
        severity_file_path = Path("data/severity_results.json")
        with open(severity_file_path, "r") as file:
            self.severity_results = json.load(file)

        super().__init__(
            model=model,
            tools=[EmailTool(), JSONPrinterTool()],  # Pass the email input as an argument to the tool
            instructions=(
                "You are tasked with identifying discrepancies with medium or higher severity, and using the email_tool to "
                "generate an email containing all discrepancies, and sending them "
                "to the appropriate recipient (bank's email). Remember that you have to list the exact issue, "
                "name of the organization in question and numerical value mismatch. "
                "First use the jsonprinter to read the issues, then the emailtool to write the email. "
                "You can basically just copy/paste the 'explanation' field from each JSON document, which you have stored as severity_results. "
            ),
            add_base_tools=False,
            additional_authorized_imports=["json", "pathlib"],
            verbosity_level=0,
            max_steps=6
        )