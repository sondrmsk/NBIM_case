# simple_agent.py
# a super simple smolagents agent with one tool.
# run: python simple_agent.py

from smolagents import CodeAgent, LiteLLMModel, tool
import pandas as pd
from dotenv import load_dotenv
load_dotenv()
from tools.file_merge import MergeAndTransposeTool
from tools.severity_classifier import SeverityClassifierTool
from tools.csv_to_json import ShowOriginalCSVTool


class Diagnoser(CodeAgent):
    def __init__(self):
        model = LiteLLMModel(
            model_id="gpt-4o-mini",
            api_base="https://api.openai.com/v1",
            api_key=None,  # picked up from OPENAI_API_KEY in .env
        )
        super().__init__(
            model=model,
            tools=[MergeAndTransposeTool(), SeverityClassifierTool(), ShowOriginalCSVTool()],
            instructions = (
    "You are an expert data analyst. You are tasked with analyzing dividend data from both "
    "NBIM and its Custodian Bank, where mismatches sometimes occur. "
    "An example is if the tax rate in NBIM's data is 0% while Custody's data says 15%. "
    ""
    "Workflow: "
    "1) Call the MergeAndTransposeTool to obtain the merged JSON. "
    "   - The JSON has the shape: {'pairs':[{'id':'No.001','NBIM':{...},'CUSTODY':{...}}, ...]}. "
    "   - Count the number of pairs. You MUST investigate EVERY one. "
    "2) Read the JSON carefully. For each pair, compare the NBIM vs CUSTODY values field-by-field. "
    "   Focus on the main economic fields (e.g. payment_date, holding_quantity, gross/net/tax amounts, tax_rate, currencies, custodian). "
    "3) If you want to investigate the data further, you can use the ShowOriginalCSVTool "
    "   to read the original NBIM and CUSTODY CSVs as JSON. This step is optional"
    "4) For each pair (convert 'No.001' to '#001', etc.), decide the severity of discrepancies: "
    "   - 'none' if no meaningful differences are found, "
    "   - 'low' for cosmetic differences (e.g. custodian name differs, ticker spelling), "
    "   - 'medium' for payment_date mismatches or a single amount differing beyond tolerance, "
    "   - 'high' for settlement currency mismatches or multiple material discrepancies in amounts/tax/holdings. "
    "5) For EACH id, write a short, clear explanation of what differs, citing NBIM vs CUSTODY values. "
    "   - If there are multiple mismatches, combine them into one explanation. "
    ""
    "Important rules: "
    "- Output MUST include exactly one object per id, no skips, no duplicates. "
    "- Treat custodian codes like 'CUST/UBSCH' as equal to 'UBS_SWITZERLAND'. "
    "- Think independently when you see custodian names to decide if they ACTUALLY differ."
    "- Consider numeric amounts equal if abs(diff) <= 1.0. "
    "- Parse dates as DD.MM.YYYY; compare only if both are present. "
    "- Ignore fields if either side is blank/None. "
    ""
    "Output format: "
    "Return a JSON array (as a string) with exactly one object per id. "
    "Each object must have keys: 'id', 'severity', 'explanation'. "
    ""
    "Example output: "
    "[ "
    " {\"id\":\"#001\",\"severity\":\"none\",\"explanation\":\"No discrepancies on approved fields.\"}, "
    " {\"id\":\"#002\",\"severity\":\"medium\",\"explanation\":\"payment_date mismatch (20.05.2025 vs 25.05.2025); "
    "net_amount_settle_ccy differs by +6.6%.\"}, "
    " {\"id\":\"#003\",\"severity\":\"high\",\"explanation\":\"settled_currency mismatch (CHF vs USD).\"} "
    "] "
    ""
    "Final step: After you produce this JSON string, pass it as 'insights' into the SeverityClassifierTool "
    "so it can be stored on disk."
),
            add_base_tools=False,
            additional_authorized_imports=["json", "pandas", "pathlib"]
        )
