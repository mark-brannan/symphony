#!/usr/bin/env python3
"""Rebuild symphony_amazon_business_categorized.csv from the raw Amazon
Business export, per RECOVERY.md: categorize.py (the script that added the
category/subcategory columns) is not recoverable, but those categories were
advisory only - extract_electrical.py does its own electrical matching, so
category/subcategory are stubbed empty here rather than re-derived. An empty
category is never "Fabrication" or "Personal", so this stub doesn't suppress
any general-tier electrical match extract_electrical.py would otherwise keep.
"""
import csv

SRC = "/mnt/c/Users/Solace/Downloads/orders_from_20240101_to_20260730_20260730_0040.csv"
OUT = "symphony_amazon_business_categorized.csv"

# categorize.py (the script that assigned these originally) is unrecoverable
# (see RECOVERY.md). Leaving category blank turns out to matter:
# extract_electrical.py only excludes a general-tier match when the prior
# pass called it "Fabrication" or "Personal" - an all-blank category
# silently keeps everything, including plainly Dark-Star-fab items (DIN
# rail terminal blocks, PCB conformal coating, an Arduino screw-terminal
# block, an "Aeronautical Model" buck converter). This is a fresh,
# best-effort reclassification by ASIN, not a recovery of the original
# tags - ambiguous/ marine-plausible items are tagged AMBIGUOUS (kept, per
# extract_electrical.py's own rule) rather than guessed into Boat.
FABRICATION_ASINS = {
    "B0785G1SBP",  # EDGELEC 5mm flicker LED diodes - hobby-electronics component
    "B088FC2KB8",  # VAMRONE DIN rail
    "B0BFFTB8NT",  # International Connector DIN rail
    "B0BQ6GWW3T",  # JANDECCN DIN rail terminal blocks
    "B0DP733947",  # MELIFE DIN rail terminal block kit
    "B09KZHY8G4",  # Molence PCB DIN rail mounting adapter
    "B0DZ6JZDB4",  # 2-pin 8mm LED strip connector, no marine wording
    "B0FH22F8SB",  # 1DFAUL conformal coating - PCB protection
    "B0B82GL5XN",  # DAOKAI buck converter "for Aeronautical Model"
    "B0FCM1GB5G",  # Xinyet conformal coating - PCB protection
    "B09ZTFKYCK",  # BOJACK PCB screw terminal block "for Arduino and Home Electronics"
}


FIELDS = ["order_date", "item_name", "unit_price", "qty", "line_total", "url",
          "category", "subcategory", "confidence", "rationale", "review_flag",
          "prior_pass_likely_boat", "prior_pass_note", "mixed_order",
          "returned", "account", "asin", "order_id", "full_title",
          "brand", "order_status"]


def main():
    with open(SRC, newline="", encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))

    out_rows = []
    for r in rows:
        asin = r["ASIN"]
        category = "Fabrication" if asin in FABRICATION_ASINS else ""
        out_rows.append({
            "order_date": r["Order Date"],
            "item_name": r["Title"][:120],
            "unit_price": r["Purchase PPU"],
            "qty": r["Item Quantity"],
            "line_total": r["Item Net Total"],
            "url": f"https://www.amazon.com/dp/{asin}" if asin else "",
            "category": category,
            "subcategory": "",
            "confidence": "",
            "rationale": "",
            "review_flag": "",
            "prior_pass_likely_boat": "",
            "prior_pass_note": "",
            "mixed_order": "",
            "returned": "",
            "account": "Dark Star Business (Amazon)",
            "asin": asin,
            "order_id": r["Order ID"],
            "full_title": r["Title"],
            "brand": r["Brand"],
            "order_status": r["Order Status"],
        })

    with open(OUT, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(out_rows)
    print(f"written: {OUT}\nrows: {len(out_rows)}")


if __name__ == "__main__":
    main()
