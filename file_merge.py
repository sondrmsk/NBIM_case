#!/usr/bin/env python3
"""
Clean + pair NBIM & Custody dividend CSVs side-by-side (NBIM1, CUSTODY1, NBIM2, CUSTODY2, ...),
with ONLY the approved standardizations/merges:

- settle_ccy            <= SETTLEMENT_CURRENCY | SETTLEMENT_CCY
- payment_date          <= PAY_DATE (preferred) | EVENT_PAYMENT_DATE
- gross_amount_quote_ccy<= GROSS_AMOUNT_QUOTATION | GROSS_AMOUNT   (assumes both are quotation ccys)
- net_amount_quote_ccy  <= NET_AMOUNT_QUOTATION | NET_AMOUNT_QC
- net_amount_settle_ccy <= NET_AMOUNT_SETTLEMENT | NET_AMOUNT_SC
- bank_account          <= BANK_ACCOUNT | BANK_ACCOUNTS
- custodian             <= CUSTODIAN | CUSTODIAN_NAME
- security_name         <= SECURITY_NAME | NAME | INSTRUMENT_DESCRIPTION

Notes:
- We DO NOT merge tax fields (e.g., TOTAL_TAX_RATE vs TAX_RATE) or FX fields.
- Instances are paired by a robust key: (event_key, ISIN, bank_account).
  * event_key is taken from COAC_EVENT_KEY (NBIM) or EVENT_KEY (Custody) when present.
  * If bank_account is missing on either side, we still pair by (event_key, ISIN).
- Output is a transposed matrix: rows are fields; columns alternate NBIM#001, CUSTODY#001, NBIM#002, CUSTODY#002, ...

Usage:
  - Place this script next to a `data/` folder containing:
        data/NBIM_Dividend_Bookings 1.csv
        data/CUSTODY_Dividend_Bookings 1.csv
  - Run:  python clean_pair_side_by_side.py
  - Output: paired_transposed_clean.csv
"""

import pandas as pd
from pathlib import Path
import re

DATA_DIR = Path("data")
NBIM_CSV = DATA_DIR / "NBIM_Dividend_Bookings 1.csv"
CUSTODY_CSV = DATA_DIR / "CUSTODY_Dividend_Bookings 1.csv"
OUT_CSV = DATA_DIR / "paired_transposed_clean.csv"


# ---------- IO & Utilities ----------

def read_csv_safely(path: Path) -> pd.DataFrame:
    """Robust CSV reader: auto-detect delimiter, strip header whitespace/BOM, drop fully empty rows."""
    df = pd.read_csv(path, sep=None, engine="python")
    df.columns = [re.sub(r"^\ufeff", "", str(c)).strip() for c in df.columns]
    # Drop rows that are entirely empty/whitespace
    mask_nonempty = df.apply(lambda r: any(str(x).strip() != "" for x in r), axis=1)
    df = df[mask_nonempty].reset_index(drop=True)
    return df


def first_nonempty(series_like, *colnames):
    """Return the first non-empty (non-blank string) value across provided columns for a given row-like object."""
    for c in colnames:
        if c in series_like and str(series_like[c]).strip() != "":
            return series_like[c]
    return ""


def normalize_key_value(x: str) -> str:
    """Normalize key parts (event_key, ISIN, bank) for pairing."""
    return re.sub(r"\s+", "", str(x)).lower()


def build_pair_key(row, is_nbim: bool) -> str:
    """
    Pair key = (event_key, ISIN, bank_account?) where:
      - event_key: NBIM.COAC_EVENT_KEY or Custody.EVENT_KEY (if present)
      - bank_account: standardized 'bank_account' if present, else raw BANK_ACCOUNT/BANK_ACCOUNTS
    """
    # event key
    event_key = ""
    if is_nbim:
        event_key = first_nonempty(row, "COAC_EVENT_KEY", "EVENT_KEY")
    else:
        event_key = first_nonempty(row, "EVENT_KEY", "COAC_EVENT_KEY")

    # ISIN
    isin = row.get("ISIN", "")

    # bank account (prefer standardized if exists)
    bank = first_nonempty(row,
                          "bank_account",
                          "BANK_ACCOUNT",
                          "BANK_ACCOUNTS")

    ek = normalize_key_value(event_key)
    isv = normalize_key_value(isin)
    b  = normalize_key_value(bank)

    # Prefer triple; if bank missing, pair by (event_key, ISIN) only.
    return f"{ek}|{isv}|{b}" if b else f"{ek}|{isv}"


# ---------- Approved Standardizations (ONLY these) ----------

APPROVED_STANDARDIZATIONS = [
    # (new_name, [source columns...], preference order already encoded by order in list)
    ("settle_ccy",            ["SETTLEMENT_CURRENCY", "SETTLEMENT_CCY"]),
    ("payment_date",          ["PAY_DATE", "EVENT_PAYMENT_DATE"]),
    ("gross_amount_quote_ccy",["GROSS_AMOUNT_QUOTATION", "GROSS_AMOUNT"]),  # assumption: both are QC
    ("net_amount_quote_ccy",  ["NET_AMOUNT_QUOTATION", "NET_AMOUNT_QC"]),
    ("net_amount_settle_ccy", ["NET_AMOUNT_SETTLEMENT", "NET_AMOUNT_SC"]),
    ("bank_account",          ["BANK_ACCOUNT", "BANK_ACCOUNTS"]),
    ("custodian",             ["CUSTODIAN", "CUSTODIAN_NAME"]),
    ("security_name",         ["SECURITY_NAME", "NAME", "INSTRUMENT_DESCRIPTION"]),
]

# For pairing only (do not drop originals unless they’re part of the approved merges)
PAIRING_HELPERS = {
    "event_key_nbim": ["COAC_EVENT_KEY", "EVENT_KEY"],   # read-only for pairing
    "event_key_cust": ["EVENT_KEY", "COAC_EVENT_KEY"],
    "isin": ["ISIN"],
}


def apply_standardizations(df: pd.DataFrame) -> pd.DataFrame:
    """
    Create ONLY the approved merged columns. After creating each, drop the source columns used.
    Leave all other columns intact (including tax/FX etc.).
    """
    df = df.copy()
    for new_name, sources in APPROVED_STANDARDIZATIONS:
        # Build the new column as the first non-empty among sources
        df[new_name] = df.apply(lambda r: first_nonempty(r, *sources), axis=1)
        # Drop the sources we just merged (dispose the rest of the labels)
        for s in sources:
            if s in df.columns:
                del df[s]
    return df


# ---------- Pairing & Transpose ----------

def pair_instances(nbim_df: pd.DataFrame, cust_df: pd.DataFrame):
    """
    Pair instances by (event_key, ISIN, bank_account?) and return a transposed matrix:
      rows = union of all fields (post-standardization)
      cols = NBIM#001, CUSTODY#001, NBIM#002, CUSTODY#002, ...
    For keys with multiple lines, we pair in row order (1-to-1 by index within the key);
    extra rows on one side become unmatched in their pair column.
    """
    # Build buckets by key
    nbim_df = nbim_df.copy()
    cust_df = cust_df.copy()

    nbim_df["_pair_key"] = nbim_df.apply(lambda r: build_pair_key(r, is_nbim=True), axis=1)
    cust_df["_pair_key"] = cust_df.apply(lambda r: build_pair_key(r, is_nbim=False), axis=1)

    # Sort for deterministic ordering inside each key
    sort_cols_nbim = [c for c in ["COAC_EVENT_KEY", "EVENT_KEY", "ISIN", "bank_account"] if c in nbim_df.columns]
    sort_cols_cust = [c for c in ["EVENT_KEY", "COAC_EVENT_KEY", "ISIN", "bank_account"] if c in cust_df.columns]
    nbim_df = nbim_df.sort_values(by=["_pair_key"] + sort_cols_nbim, kind="mergesort").reset_index(drop=True)
    cust_df = cust_df.sort_values(by=["_pair_key"] + sort_cols_cust, kind="mergesort").reset_index(drop=True)

    # Group by key
    nbim_groups = {k: g.drop(columns=["_pair_key"]) for k, g in nbim_df.groupby("_pair_key", dropna=False)}
    cust_groups = {k: g.drop(columns=["_pair_key"]) for k, g in cust_df.groupby("_pair_key", dropna=False)}

    all_keys = sorted(set(nbim_groups) | set(cust_groups))

    # Union of fields after standardization
    all_fields = []
    def add_fields(cols):
        nonlocal all_fields
        for c in cols:
            if c not in all_fields:
                all_fields.append(c)

    for g in nbim_groups.values():
        add_fields(list(g.columns))
    for g in cust_groups.values():
        add_fields(list(g.columns))

    # We'll avoid carrying helper-only columns in the transposed output
    EXCLUDE_FROM_OUTPUT = set([
        # if any survived standardization stage (shouldn't for approved merges, but just in case)
    ])

    all_fields = [f for f in all_fields if f not in EXCLUDE_FROM_OUTPUT]

    # Build transposed wide result
    wide = pd.DataFrame(index=all_fields)
    pair_counter = 0

    for key in all_keys:
        n_df = nbim_groups.get(key, pd.DataFrame(columns=all_fields))
        c_df = cust_groups.get(key, pd.DataFrame(columns=all_fields))

        # Align counts by simple 1:1 pairing across row order
        max_len = max(len(n_df), len(c_df))
        if max_len == 0:
            continue

        n_rows = [n_df.iloc[i] if i < len(n_df) else pd.Series(dtype=object) for i in range(max_len)]
        c_rows = [c_df.iloc[i] if i < len(c_df) else pd.Series(dtype=object) for i in range(max_len)]

        for i in range(max_len):
            pair_counter += 1
            nbim_col = f"NBIM#{pair_counter:03d}"
            cust_col = f"CUSTODY#{pair_counter:03d}"

            # Reindex onto all_fields to ensure all rows have same index
            n_series = n_rows[i].reindex(all_fields)
            c_series = c_rows[i].reindex(all_fields)

            wide[nbim_col] = n_series
            wide[cust_col] = c_series

    wide.index.name = "Field"
    # Replace NaN with blank string for neatness (keeps numeric-looking strings as-is)
    wide = wide.fillna("")
    return wide


def main():
    # 1) Read
    nbim_raw = read_csv_safely(NBIM_CSV)
    custody_raw = read_csv_safely(CUSTODY_CSV)

    # 2) Apply ONLY the approved standardizations to each side
    nbim_std = apply_standardizations(nbim_raw)
    cust_std = apply_standardizations(custody_raw)

    # 3) Build the side-by-side, transposed matrix
    result = pair_instances(nbim_std, cust_std)

    # 4) Save
    result.to_csv(OUT_CSV, index=True)
    print(f"Saved '{OUT_CSV}' with shape {result.shape}.")
    print("Columns alternate NBIM#xxx, CUSTODY#xxx for each matched pair key.")
    print("Only approved fields were merged; tax/FX fields remain separate.")
    print("Pair key = (event_key from COAC_EVENT_KEY/EVENT_KEY, ISIN, optional bank_account).")


if __name__ == "__main__":
    main()