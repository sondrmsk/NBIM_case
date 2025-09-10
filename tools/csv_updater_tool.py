import re
import pandas as pd
from pathlib import Path
from smolagents import Tool
import difflib

class CSVUpdaterTool(Tool):
    name = "csv_updater"
    description = (
        "Updates data/paired_transposed_clean.csv where IDs are COLUMNS (e.g., NBIM#001, CUSTODY#001) "
        "and fields are ROWS (e.g., TAX_RATE). Applies approved remediation to both NBIM and CUSTODY columns."
    )

    inputs = {
        "id": {
            "type": "string",
            "description": (
                "The ID for the pair. Accepts '001', '#001', 'NBIM#001', or 'CUSTODY#001'. "
                "Columns will be resolved to NBIM#<id> and CUSTODY#<id>."
            )
        },
        "remediation_row": {
            "type": "string",
            "description": (
                "The ROW (field name) to update. Eligible rows include: "
                "'COAC_EVENT_KEY', 'ISIN', 'SEDOL', 'TICKER', 'ORGANISATION_NAME', 'DIVIDENDS_PER_SHARE', "
                "'EX_DATE', 'PAYMENT_DATE', 'QUOTATION_CURRENCY', 'SETTLED_CURRENCY', "
                "'IS_CROSS_CURRENCY_REVERSAL', 'HOLDING_QUANTITY', 'GROSS_AMOUNT_QUOTATION', "
                "'NET_AMOUNT_QUOTATION', 'NET_AMOUNT_SETTLEMENT', 'TAX_RATE', 'TAX', 'BANK_ACCOUNT', 'CUSTODIAN'. "
                "The tool will try to match similar names."
            )
        },
        "value": {
            "type": "string",
            "description": "The value to insert at [remediation_row, NBIM#<id>] and [remediation_row, CUSTODY#<id>]."
        }
    }
    output_type = "string"

    def _normalize(self, s: str) -> str:
        return str(s).strip().upper().replace(" ", "_")

    def _clean_id(self, id_str: str) -> str:
        """
        Accept '001', '#001', 'NBIM#001', 'CUSTODY#001', etc. -> return '001' (preserving leading zeros).
        """
        s = str(id_str).strip().upper()
        # Strip known prefixes once
        for prefix in ("NBIM#", "CUSTODY#", "CUST#"):
            if s.startswith(prefix):
                s = s[len(prefix):]
                break
        s = s.lstrip("#")
        m = re.search(r"(\d+)$", s)
        if not m:
            raise ValueError(f"Unrecognized id format: {id_str!r}. Expected like '001', '#001', 'NBIM#001'.")
        # Preserve width with zeros (3+ digits supported)
        digits = m.group(1)
        return digits if len(digits) >= 3 else digits.zfill(3)

    def _resolve_row_name(self, candidate_row: str, eligible_rows: list, df_index: pd.Index) -> str:
        """Resolve the intended row name using eligibility list + fuzzy matching against dataframe index."""
        target_norm = self._normalize(candidate_row)

        # 1) map against eligible list
        elig_norm_map = {self._normalize(r): r for r in eligible_rows}
        chosen = elig_norm_map.get(target_norm)
        if chosen is None:
            close = difflib.get_close_matches(target_norm, list(elig_norm_map.keys()), n=1, cutoff=0.6)
            chosen = elig_norm_map[close[0]] if close else candidate_row

        # 2) ensure it exists in df index (case-insensitive / fuzzy)
        if chosen in df_index:
            return chosen

        idx_norm_map = {self._normalize(ix): ix for ix in df_index}
        norm_chosen = self._normalize(chosen)
        if norm_chosen in idx_norm_map:
            return idx_norm_map[norm_chosen]

        close2 = difflib.get_close_matches(norm_chosen, list(idx_norm_map.keys()), n=1, cutoff=0.6)
        if close2:
            return idx_norm_map[close2[0]]

        return chosen  # final fallback; will error later if not present

    def forward(self, id: str, remediation_row: str, value: str) -> str:
        """
        Updates the paired_transposed_clean.csv where IDs are columns and fields are rows.
        Applies the value to both NBIM#<id> and CUSTODY#<id> in the specified row.
        """
        csv_path = Path("data/paired_transposed_clean.csv")
        if not csv_path.exists():
            return f"CSV not found at {csv_path}"

        # Read all as strings to avoid dtype surprises
        df = pd.read_csv(csv_path, dtype=str)

        # Use the first column as the row index (expected to be 'FIELD')
        if df.empty or len(df.columns) == 0:
            return "CSV appears empty or malformed."

        first_col = df.columns[0]
        df.set_index(first_col, inplace=True)

        # Define eligible rows
        eligible_rows = [
            'COAC_EVENT_KEY', 'ISIN', 'SEDOL', 'TICKER', 'ORGANISATION_NAME', 'DIVIDENDS_PER_SHARE', 'EX_DATE',
            'PAYMENT_DATE', 'QUOTATION_CURRENCY', 'SETTLED_CURRENCY', 'IS_CROSS_CURRENCY_REVERSAL', 'HOLDING_QUANTITY',
            'GROSS_AMOUNT_QUOTATION', 'NET_AMOUNT_QUOTATION', 'NET_AMOUNT_SETTLEMENT', 'TAX_RATE', 'TAX',
            'BANK_ACCOUNT', 'CUSTODIAN'
        ]

        # Resolve row name robustly
        resolved_row = self._resolve_row_name(remediation_row, eligible_rows, df.index)
        if resolved_row not in df.index:
            return (
                f"Row '{remediation_row}' not found (resolved to '{resolved_row}'). "
                f"Available sample rows: {list(df.index[:10])} ..."
            )

        # Clean and build column names for the given id
        try:
            clean_id = self._clean_id(id)
        except ValueError as e:
            return str(e)

        # Case-insensitive column resolution
        col_norm_map = {self._normalize(c): c for c in df.columns}
        nbim_key = self._normalize(f"NBIM#{clean_id}")
        custody_key = self._normalize(f"CUSTODY#{clean_id}")
        nbim_col = col_norm_map.get(nbim_key)
        custody_col = col_norm_map.get(custody_key)

        missing = []
        if nbim_col is None:
            missing.append(f"NBIM#{clean_id}")
        if custody_col is None:
            missing.append(f"CUSTODY#{clean_id}")
        if missing:
            return (
                f"Column(s) not found: {missing}. "
                f"Sample columns: {list(df.columns[:10])} ..."
            )

        # Update both NBIM and CUSTODY columns at the specified row
        value_str = str(value)
        try:
            df.loc[resolved_row, nbim_col] = value_str
            df.loc[resolved_row, custody_col] = value_str
        except Exception as e:
            return f"[csv_updater] Error updating row '{resolved_row}' and columns [{nbim_col}, {custody_col}]: {e}"

        # Save (simple and robust)
        df.reset_index(inplace=True)
        df.to_csv(csv_path, index=False)

        return f"Updated {csv_path} at row '{resolved_row}' for IDs {nbim_col} and {custody_col}."
