from pathlib import Path
import pandas as pd
import json
from smolagents import Tool

class ShowOriginalCSVTool(Tool):
    name = "show_original_csv"
    description = (
        "Reads the original NBIM and Custody dividend CSVs and returns them as JSON. "
        "This lets the agent inspect the raw values before merging. "
        "The tool outputs a dict with two keys: 'NBIM' and 'CUSTODY'."
    )
    inputs = {}
    output_type = "object"

    def forward(self):
        try:
            nbim_path = Path("data/NBIM_Dividend_Bookings 1.csv")
            custody_path = Path("data/CUSTODY_Dividend_Bookings 1.csv")

            nbim_df = pd.read_csv(nbim_path)
            custody_df = pd.read_csv(custody_path)

            # Convert to JSON-friendly dicts (list of row dicts)
            nbim_json = nbim_df.fillna("").to_dict(orient="records")
            custody_json = custody_df.fillna("").to_dict(orient="records")

            return {
                "NBIM": nbim_json,
                "CUSTODY": custody_json
            }

        except Exception as e:
            return {"error": str(e)}