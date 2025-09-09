#!/usr/bin/env python3
"""
merge_and_transpose tool for smolagents (class-based)

This tool cleans + pairs NBIM & Custody dividend CSVs side-by-side
(NBIM1, CUSTODY1, NBIM2, CUSTODY2, ...), with ONLY the approved standardizations.
"""

import pandas as pd
from pathlib import Path
import re
from smolagents import Tool

# ---------- IO & Utilities ----------

def read_csv_safely(path: Path) -> pd.DataFrame:
    """Robust CSV reader: auto-detect delimiter, strip header whitespace/BOM, drop fully empty rows."""
    df = pd.read_csv(path, sep=None, engine="python")
    df.columns = [re.sub(r"^\ufeff", "", str(c)).strip() for c in df.columns]
    mask_nonempty = df.apply(lambda r: any(str(x).strip() != "" for x in r), axis=1)
    df = df[mask_nonempty].reset_index(drop=True)
    return df


def first_nonempty(series_like, *colnames):
    """Return the first non-empty value across provided columns for a given row-like object."""
    for c in colnames:
        if c in series_like and str(series_like[c]).strip() != "":
            return series_like[c]
    return ""


def normalize_key_value(x: str) -> str:
    """Normalize key parts (event_key, ISIN, bank) for pairing."""
    return re.sub(r"\s+", "", str(x)).lower()


def build_pair_key(row, is_nbim: bool) -> str:
    """Pair key = (event_key, ISIN, bank_account?)"""
    if is_nbim:
        event_key = first_nonempty(row, "COAC_EVENT_KEY", "EVENT_KEY")
    else:
        event_key = first_nonempty(row, "EVENT_KEY", "COAC_EVENT_KEY")

    isin = row.get("ISIN", "")
    bank = first_nonempty(row, "bank_account", "BANK_ACCOUNT", "BANK_ACCOUNTS")

    ek = normalize_key_value(event_key)
    isv = normalize_key_value(isin)
    b = normalize_key_value(bank)

    return f"{ek}|{isv}|{b}" if b else f"{ek}|{isv}"


# ---------- Approved Standardizations ----------

APPROVED_STANDARDIZATIONS = [
    ("settle_ccy",            ["SETTLEMENT_CURRENCY", "SETTLEMENT_CCY"]),
    ("payment_date",          ["PAY_DATE", "EVENT_PAYMENT_DATE"]),
    ("gross_amount_quote_ccy",["GROSS_AMOUNT_QUOTATION", "GROSS_AMOUNT"]),
    ("net_amount_quote_ccy",  ["NET_AMOUNT_QUOTATION", "NET_AMOUNT_QC"]),
    ("net_amount_settle_ccy", ["NET_AMOUNT_SETTLEMENT", "NET_AMOUNT_SC"]),
    ("bank_account",          ["BANK_ACCOUNT", "BANK_ACCOUNTS"]),
    ("custodian",             ["CUSTODIAN", "CUSTODIAN_NAME"]),
    ("security_name",         ["SECURITY_NAME", "NAME", "INSTRUMENT_DESCRIPTION"]),
]


def apply_standardizations(df: pd.DataFrame) -> pd.DataFrame:
    """Create ONLY the approved merged columns. Drop source cols afterwards."""
    df = df.copy()
    for new_name, sources in APPROVED_STANDARDIZATIONS:
        df[new_name] = df.apply(lambda r: first_nonempty(r, *sources), axis=1)
        for s in sources:
            if s in df.columns:
                del df[s]
    return df


# ---------- Pairing & Transpose ----------

def pair_instances(nbim_df: pd.DataFrame, cust_df: pd.DataFrame) -> pd.DataFrame:
    """Pair instances by (event_key, ISIN, bank_account?) and return a transposed matrix."""
    nbim_df = nbim_df.copy()
    cust_df = cust_df.copy()

    nbim_df["_pair_key"] = nbim_df.apply(lambda r: build_pair_key(r, True), axis=1)
    cust_df["_pair_key"] = cust_df.apply(lambda r: build_pair_key(r, False), axis=1)

    sort_cols_nbim = [c for c in ["COAC_EVENT_KEY", "EVENT_KEY", "ISIN", "bank_account"] if c in nbim_df.columns]
    sort_cols_cust = [c for c in ["EVENT_KEY", "COAC_EVENT_KEY", "ISIN", "bank_account"] if c in cust_df.columns]
    nbim_df = nbim_df.sort_values(by=["_pair_key"] + sort_cols_nbim, kind="mergesort").reset_index(drop=True)
    cust_df = cust_df.sort_values(by=["_pair_key"] + sort_cols_cust, kind="mergesort").reset_index(drop=True)

    nbim_groups = {k: g.drop(columns=["_pair_key"]) for k, g in nbim_df.groupby("_pair_key", dropna=False)}
    cust_groups = {k: g.drop(columns=["_pair_key"]) for k, g in cust_df.groupby("_pair_key", dropna=False)}
    all_keys = sorted(set(nbim_groups) | set(cust_groups))

    all_fields = []
    def add_fields(cols):
        for c in cols:
            if c not in all_fields:
                all_fields.append(c)

    for g in nbim_groups.values(): add_fields(list(g.columns))
    for g in cust_groups.values(): add_fields(list(g.columns))

    wide = pd.DataFrame(index=all_fields)
    pair_counter = 0

    for key in all_keys:
        n_df = nbim_groups.get(key, pd.DataFrame(columns=all_fields))
        c_df = cust_groups.get(key, pd.DataFrame(columns=all_fields))

        max_len = max(len(n_df), len(c_df))
        if max_len == 0:
            continue

        for i in range(max_len):
            pair_counter += 1
            nbim_col = f"NBIM#{pair_counter:03d}"
            cust_col = f"CUSTODY#{pair_counter:03d}"

            n_series = (n_df.iloc[i] if i < len(n_df) else pd.Series(dtype=object)).reindex(all_fields)
            c_series = (c_df.iloc[i] if i < len(c_df) else pd.Series(dtype=object)).reindex(all_fields)

            wide[nbim_col] = n_series
            wide[cust_col] = c_series

    wide.index.name = "Field"
    return wide.fillna("")


# ---------- Smolagents Tool (Class-based) ----------

class MergeAndTransposeTool(Tool):
    name = "merge_and_transpose"
    description = (
        "Clean + pair NBIM & Custody dividend CSVs side-by-side "
        "(NBIM1, CUSTODY1, ...), with ONLY the approved standardizations. "
        "Returns the path to the merged transposed CSV."
    )
    inputs = {
        "nbim_csv_path": {
            "type": "string",
            "description": "Path to the NBIM CSV file."
        },
        "custody_csv_path": {
            "type": "string",
            "description": "Path to the Custody CSV file."
        },
        "out_csv_path": {
            "type": "string",
            "description": "Where to save the merged/transposed CSV.",
            "nullable": True   # ✅ mark as nullable since it has a default
        },
    }
    output_type = "string"

    def forward(self, nbim_csv_path: str, custody_csv_path: str, out_csv_path: str = "paired_transposed_clean.csv") -> str:
        nbim_raw = read_csv_safely(Path(nbim_csv_path))
        cust_raw = read_csv_safely(Path(custody_csv_path))

        nbim_std = apply_standardizations(nbim_raw)
        cust_std = apply_standardizations(cust_raw)

        result = pair_instances(nbim_std, cust_std)
        result.to_csv(out_csv_path, index=True)
        print(f"[merge_and_transpose] Saved '{out_csv_path}' with shape {result.shape}.")
        return result
