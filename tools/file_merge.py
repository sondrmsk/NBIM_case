import pandas as pd
from pathlib import Path
import re
from itertools import zip_longest
from smolagents import Tool

def _read_csv(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path, sep=None, engine="python")
    # normalize column names: strip BOM/whitespace; keep original case in values
    df.columns = [re.sub(r"^\ufeff", "", str(c)).strip() for c in df.columns]
    # drop fully empty rows
    mask = df.apply(lambda r: any(str(x).strip() != "" for x in r), axis=1)
    return df[mask].reset_index(drop=True)

def _first(row, *names):
    for n in names:
        if n in row and str(row[n]).strip() != "":
            return row[n]
    return ""

def _num(x):
    try:
        # allow strings like "1,234.56"
        return float(str(x).replace(",", "").strip())
    except:
        return None

def _is_multi_ccy(s: str) -> bool:
    if not s: return False
    txt = str(s)
    # multi if it contains a space-separated list or " + "
    return (" " in txt.strip() and len(txt.strip().split()) > 1) or ("+" in txt)

def _merge_nbim_row(row: dict) -> dict:
    # NBIM unified view
    q_ccy = _first(row, "QUOTATION_CURRENCY")
    s_ccy = _first(row, "SETTLEMENT_CURRENCY", "SETTLED_CURRENCY")

    # join with a SPACE if different
    quotation_currency = q_ccy
    if s_ccy and q_ccy and str(q_ccy).strip() != str(s_ccy).strip():
        quotation_currency = f"{q_ccy} {s_ccy}"

    gross_q = _first(row, "GROSS_AMOUNT_QUOTATION", "GROSS_AMOUNT")
    net_q   = _first(row, "NET_AMOUNT_QUOTATION", "NET_AMOUNT_QC", "NET_AMOUNT_QUOTATION_CC")
    net_sc  = _first(row, "NET_AMOUNT_SETTLEMENT", "NET_AMOUNT_SC")

    tax_rate = _first(row, "TOTAL_TAX_RATE", "WTHTAX_RATE")

    tax = _first(row, "TAX")
    g = _num(gross_q); n = _num(net_q)
    if g is not None and n is not None:
        tax = g - n

    holding = _first(row, "NOMINAL_BASIS", "HOLDING_QUANTITY")

    return {
        "COAC_EVENT_KEY": _first(row, "COAC_EVENT_KEY", "EVENT_KEY"),
        "ISIN": _first(row, "ISIN"),
        "SEDOL": _first(row, "SEDOL"),
        "TICKER": _first(row, "TICKER"),
        "ORGANISATION_NAME": _first(row, "ORGANISATION_NAME"),
        "DIVIDENDS_PER_SHARE": _first(row, "DIVIDENDS_PER_SHARE", "DIV_RATE"),
        "EX_DATE": _first(row, "EXDATE", "EX_DATE"),
        "PAYMENT_DATE": _first(row, "PAYMENT_DATE"),
        "QUOTATION_CURRENCY": quotation_currency,
        "SETTLED_CURRENCY": s_ccy,
        "IS_CROSS_CURRENCY_REVERSAL": _is_multi_ccy(quotation_currency),
        "HOLDING_QUANTITY": holding,
        "GROSS_AMOUNT_QUOTATION": gross_q,
        "NET_AMOUNT_QUOTATION": net_q,
        "NET_AMOUNT_SETTLEMENT": net_sc,
        "TAX_RATE": tax_rate,
        "TAX": tax,
        "BANK_ACCOUNT": _first(row, "BANK_ACCOUNT", "BANK_ACCOUNTS"),
        "CUSTODIAN": _first(row, "CUSTODIAN", "CUSTODIAN_NAME"),
    }


def _merge_cust_row(row: dict) -> dict:
    # CUSTODY unified view
    quotation_currency = _first(row, "CURRENCIES")
    s_ccy = _first(row, "SETTLED_CURRENCY", "SETTLEMENT_CURRENCY")

    gross_q = _first(row, "GROSS_AMOUNT_QUOTATION", "GROSS_AMOUNT")
    net_q   = _first(row, "NET_AMOUNT_QUOTATION", "NET_AMOUNT_QC", "NET_AMOUNT_QUOTATION_CC")
    net_sc  = _first(row, "NET_AMOUNT_SETTLEMENT", "NET_AMOUNT_SC")

    # TAX: compute if possible, else use provided
    tax = _first(row, "TAX")
    g = _num(gross_q); n = _num(net_q)
    if g is not None and n is not None:
        tax = g - n if tax in ("", None) else (_num(tax) if _num(tax) is not None else g - n)

    # HOLDING = holding_quantity + loan_quantity (missing -> 0)
    h = _num(_first(row, "HOLDING_QUANTITY", "NOMINAL_BASIS")) or 0.0
    l = _num(_first(row, "LOAN_QUANTITY")) or 0.0
    holding = h + l

    return {
        "COAC_EVENT_KEY": _first(row, "COAC_EVENT_KEY", "EVENT_KEY"),
        "ISIN": _first(row, "ISIN"),
        "SEDOL": _first(row, "SEDOL"),
        "TICKER": _first(row, "TICKER"),  # will backfill from NBIM if empty
        "ORGANISATION_NAME": _first(row, "ORGANISATION_NAME"),  # backfill from NBIM if empty
        "DIVIDENDS_PER_SHARE": _first(row, "DIV_RATE", "DIVIDENDS_PER_SHARE"),
        "EX_DATE": _first(row, "EX_DATE", "EXDATE"),
        "PAYMENT_DATE": _first(row, "EVENT_PAYMENT_DATE", "PAYMENT_DATE"),
        "QUOTATION_CURRENCY": quotation_currency,  # typically already like "KRW USD"
        "SETTLED_CURRENCY": s_ccy,
        "IS_CROSS_CURRENCY_REVERSAL": _is_multi_ccy(quotation_currency),
        "HOLDING_QUANTITY": holding,
        "GROSS_AMOUNT_QUOTATION": gross_q,
        "NET_AMOUNT_QUOTATION": net_q,
        "NET_AMOUNT_SETTLEMENT": net_sc,
        "TAX_RATE": _first(row, "TAX_RATE"),
        "TAX": tax,
        "BANK_ACCOUNT": _first(row, "BANK_ACCOUNT", "BANK_ACCOUNTS"),
        "CUSTODIAN": _first(row, "CUSTODIAN", "CUSTODIAN_NAME"),
    }


class MergeAndTransposeTool(Tool):
    name = "merge_and_transpose"
    description = (
        "Pair NBIM & Custody by row order, hard-merge overlapping fields, "
        "compute key metrics (tax, currencies, holdings), "
        "and write CSV + JSON with explicit ids No.NNN."
    )
    inputs = {}
    output_type = "object"

    def forward(self):
        nbim_path = Path("data/NBIM_Dividend_Bookings 1.csv")
        cust_path = Path("data/CUSTODY_Dividend_Bookings 1.csv")
        out_csv   = Path("data/paired_transposed_clean.csv")
        out_json  = Path("data/paired.json")

        nbim_df = _read_csv(nbim_path)
        cust_df = _read_csv(cust_path)

        pairs = []
        # pair strictly by position
        for i, (nbim_row, cust_row) in enumerate(zip_longest(nbim_df.to_dict("records"),
                                                            cust_df.to_dict("records"),
                                                            fillvalue={} ), start=1):
            nbim_u = _merge_nbim_row(nbim_row)
            cust_u = _merge_cust_row(cust_row)

            # Backfill informative things from NBIM into Custody if blank
            if not str(cust_u.get("TICKER", "")).strip():
                cust_u["TICKER"] = nbim_u.get("TICKER", "")
            if not str(cust_u.get("ORGANISATION_NAME", "")).strip():
                cust_u["ORGANISATION_NAME"] = nbim_u.get("ORGANISATION_NAME", "")

            pairs.append({
                "id": f"No.{i:03d}",
                "NBIM": nbim_u,
                "CUSTODY": cust_u
            })

        # ---------- write CSV in your preferred “transposed” style ----------
        # rows = fields; columns = NBIM#001, CUSTODY#001, …
        fields = list(pairs[0]["NBIM"].keys()) if pairs else []
        wide = pd.DataFrame(index=fields)
        for i, p in enumerate(pairs, start=1):
            wide[f"NBIM#{i:03d}"] = pd.Series(p["NBIM"])
            wide[f"CUSTODY#{i:03d}"] = pd.Series(p["CUSTODY"])
        wide.index.name = "FIELD"
        wide.to_csv(out_csv)

        # ---------- write JSON ----------
        import json
        json_out = {"pairs": pairs}
        with open(out_json, "w") as f:
            json.dump(json_out, f, indent=2)

        print(f"[merge_and_transpose] Saved '{out_csv}' and '{out_json}'")
        return json_out
