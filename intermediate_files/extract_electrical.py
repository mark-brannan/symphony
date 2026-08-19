#!/usr/bin/env python3
"""Pull electrical/electronics line items only, from all three order
sources, for the diagramming intermediate CSV. Full detail preserved
from source rows (no truncation), plus a `source` column identifying
where it was bought.

Sources (read-only, in this directory):
  - amazon-orders-for-review.csv           (Amazon, personal account)
  - symphony_amazon_business_categorized.csv (Amazon, Dark Star Business,
    already category/subcategory-tagged by an earlier pass)
  - fisheries-line-items.csv               (Fisheries Supply)

Scope: electrical components only - wire, batteries, chargers, panels,
switches, breakers, fuses, connectors, NMEA2000/nav electronics, sensors,
lighting. Not plumbing/mechanical/hull, even where "boat" in general.
"""
import csv
import re

OUT = "electrical-components.csv"

# Always include, regardless of any other signal - unambiguous marine
# electrical/electronics brand or system terms. Low false-positive risk.
STRICT_RE = re.compile(
    r"\bvictron\b|\bxantrex\b|\brenogy\b|\bblue sea\b|\bancor\b|\bmarine "
    r"grade electrical\b|marine wire|tinned copper wire|duplex marine|"
    r"triplex marine|\bnmea ?2000\b|\bn2k\b|\bgarmin\b.*(airmar|transducer|"
    r"n2k)|\bnavico\b|\blowrance\b.*dst|\braymarine\b|\bfuruno\b|"
    r"triducer|rudder angle sen(der|sor)|marine.*bilge.*(switch|alarm|"
    r"sensor)|bilge.*pump.*switch|isolation transformer|class t fuse|"
    r"marine fuse|boat fuse|marine.*circuit breaker|circuit breaker.*"
    r"(boat|marine|trolling motor)|shore power|marine.*shore power|"
    r"battery isolator|voltage sensitive relay|\bvsr\b|battery "
    r"disconnect|master isolator|smartshunt|cerbo|multiplus|orion-tr|"
    r"batteryprotect|automatic charging relay|\bsi-acr\b"
)

# Broader electrical vocabulary - wire gauges, connectors, fuses, tools.
# Only trusted when a supporting signal says "probably boat" (see below);
# on its own it also matches generic car/RV/electronics accessories.
GENERAL_RE = re.compile(
    r"battery monitor|\bshunt\b|\bbms\b|lifepo4|\bmppt\b|solar charge "
    r"controller|dc-dc converter|dc to dc converter|\binverter\b|"
    r"\bcharger\b|marine battery|deep cycle battery|agm battery|"
    r"group 27|group 31|din rail|bus ?bar|battery switch|autopilot|"
    r"chartplotter|vhf radio|\bais\b(?!le)|radar dome|depth sounder|"
    r"\bawg\b|gauge wire|battery cable|wire lug|ferrule|heat shrink|"
    r"\bmultimeter\b|alligator clip|test lead|butt connector|wire "
    r"connector|inline fuse|fuse (holder|block|box|assortment|kit)|"
    r"\bfuse\b|cable gland|liquid tape|conformal coating|terminal block|"
    r"terminal (strip|fuse)|led strip|cob led|led diode|led bulb|"
    r"battery terminal|spade connector|electrical primary|"
    r"boost converter|buck converter|electrical connector|"
    r"4 prong connector|wire stripper|crimping tool"
)

# Excludes things that would false-positive on GENERAL_RE but are not
# boat-electrical: PEX plumbing tools ("crimp"/"expansion"), CNC/VFD gear,
# and generic phone/USB accessories.
EXCLUDE_RE = re.compile(
    r"variable frequency drive|\bvfd\b|\bcnc\b|spindle|router bit|"
    r"end mill|collet\b|\bpex\b|wireless charg|phone charg|usb.?c "
    r"(cable|cord|to usb)|type c to c|charging pad|charging cable"
)


def classify_electrical(text: str) -> str:
    """Returns 'strict', 'general', or '' (not electrical)."""
    t = text.lower()
    if EXCLUDE_RE.search(t):
        return ""
    if STRICT_RE.search(t):
        return "strict"
    if GENERAL_RE.search(t):
        return "general"
    return ""


FIELDS = ["source", "order_date", "item_name", "brand", "qty", "unit_price",
          "line_total", "asin_or_sku", "order_id", "url", "returned",
          "order_status", "match_tier", "prior_pass_category",
          "prior_pass_subcategory", "prior_pass_likely_boat", "notes"]


def from_personal():
    """Source already carries a partial human/earlier-pass judgment in
    likely_boat (strong/likely/unlikely/review) - kept as-is, used as the
    supporting signal for GENERAL_RE hits (a 'general' match only counts
    if likely_boat says probably-boat; STRICT_RE hits are kept either
    way, since a Victron/Blue Sea/marine-branded item is boat regardless
    of what the earlier pass guessed)."""
    with open("amazon-orders-for-review.csv", newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    out = []
    for r in rows:
        tier = classify_electrical(r["product_name"])
        if not tier:
            continue
        if tier == "general" and r["likely_boat"] not in ("strong", "likely"):
            continue
        out.append({
            "source": "Amazon (personal)",
            "order_date": r["order_date"],
            "item_name": r["product_name"],
            "brand": "",
            "qty": r["qty"],
            "unit_price": r["unit_price"],
            "line_total": r["total_amount"],
            "asin_or_sku": r["asin"],
            "order_id": r["order_id"],
            "url": f"https://www.amazon.com/dp/{r['asin']}" if r["asin"] else "",
            "returned": r["returned"],
            "order_status": r["status"],
            "match_tier": tier,
            "prior_pass_category": "",
            "prior_pass_subcategory": "",
            "prior_pass_likely_boat": r["likely_boat"],
            "notes": "",
        })
    return out


def from_business():
    """This source was already run through categorize.py, which sorts
    into Boat/Fabrication/Shared/AMBIGUOUS/Personal - kept and exposed
    here rather than re-derived, since it already encodes a judgment call
    (e.g. DIN rail/terminal blocks/LED strips flagged AMBIGUOUS: DC panel
    for the boat OR a CNC control cabinet for Dark Star). A STRICT_RE hit
    is kept regardless of that prior category. A GENERAL_RE hit is kept
    only if the prior pass didn't call it Fabrication or Personal."""
    with open("symphony_amazon_business_categorized.csv", newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    out = []
    for r in rows:
        if r["order_status"] == "Cancelled":
            continue
        tier = classify_electrical(r["full_title"])
        if not tier:
            continue
        if tier == "general" and r["category"] in ("Fabrication", "Personal"):
            continue
        note = ("possibly Dark Star (CNC/fab) rather than boat - flagged "
                "AMBIGUOUS by the business-account pass"
                if r["category"] == "AMBIGUOUS" else "")
        out.append({
            "source": "Amazon (Dark Star Business)",
            "order_date": r["order_date"],
            "item_name": r["full_title"],
            "brand": r["brand"],
            "qty": r["qty"],
            "unit_price": r["unit_price"],
            "line_total": r["line_total"],
            "asin_or_sku": r["asin"],
            "order_id": r["order_id"],
            "url": r["url"],
            "returned": "",  # not tracked in this source
            "order_status": r["order_status"],
            "match_tier": tier,
            "prior_pass_category": r["category"],
            "prior_pass_subcategory": r["subcategory"],
            "prior_pass_likely_boat": "",
            "notes": note,
        })
    return out


def from_fisheries():
    with open("fisheries-line-items.csv", newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    out = []
    for r in rows:
        tier = "strict" if r["Category"] == "Electrical" else classify_electrical(r["Description"])
        if not tier:
            continue
        out.append({
            "source": "Fisheries Supply",
            "order_date": r["Order Date"],
            "item_name": r["Description"],
            "brand": r["Vendor"],
            "qty": r["Qty"],
            "unit_price": r["Unit Price"],
            "line_total": r["Line Total"],
            "asin_or_sku": r["SKU"] or r["Item ID / Part #"],
            "order_id": r["Order #"],
            "url": "",
            "returned": "Y" if (r["Qty"] or "").strip().startswith("-") else "",
            "order_status": "",
            "match_tier": tier,
            "prior_pass_category": r["Category"],
            "prior_pass_subcategory": "",
            "prior_pass_likely_boat": "",
            "notes": "",
        })
    return out


def main():
    rows = from_personal() + from_business() + from_fisheries()
    rows.sort(key=lambda r: (r["order_date"], r["source"], r["item_name"]))

    with open(OUT, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(rows)

    from collections import Counter
    print(f"written: {OUT}\nrows: {len(rows)}\n")
    print("=== by source ===")
    for s, n in Counter(r["source"] for r in rows).most_common():
        print(f"{n:4d}  {s}")
    ret = sum(1 for r in rows if r["returned"] == "Y")
    print(f"\nreturned (kept in file, flagged): {ret}")


if __name__ == "__main__":
    main()
