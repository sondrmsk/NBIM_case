from pathlib import Path
from smolagents import Tool

class JSONPrinterTool(Tool):
    name = "json_printer"
    description = "Prints the contents of data/severity_results.json to stdout."
    inputs = {}  # no inputs
    output_type = "string"

    def forward(self) -> str:
        data = Path("data/severity_results.json").read_text(encoding="utf-8")
        print(data)
        return data
