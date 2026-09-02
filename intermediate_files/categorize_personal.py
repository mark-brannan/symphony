#!/usr/bin/env python3
"""Categorize personal-Amazon order line items for SYMPHONY (boat) vs
Dark Star LLC (CNC/fab) vs Personal/household.

Input already carries a partial human/earlier-pass judgment in
`likely_boat` (strong/likely/unlikely/review) plus `mixed_order` and
`returned` flags. This pass:
  - keeps those columns as-is (doesn't overwrite prior judgment)
  - adds category/subcategory/confidence/rationale via regex rules,
    reused/extended from categorize.py (the Business-account script)
  - reconciles rule output with the existing likely_boat tag rather than
    contradicting it silently

Rough first pass, not a final inventory. Rows the rules don't catch stay
UNCLASSIFIED for manual review; that's expected and fine here.
"""
import csv
import re

SRC = "amazon-orders-for-review.csv"
OUT = "personal-amazon-categorized.csv"

# (regex, category, subcategory, confidence, rationale)
RULES = [
    # ---------- unambiguous BOAT: electrical/electronics ----------
    (r"\bvictron\b|\bxantrex\b|\brenogy\b|battery monitor|shunt|bms\b|lifepo4|"
     r"mppt|solar charge controller|dc-dc converter|battery isolator",
     "Boat", "Electrical - Charging & Batteries", "high", "House-battery/charging system component"),
    (r"marine battery|group 27|group 31|agm battery|deep cycle battery",
     "Boat", "Electrical - Charging & Batteries", "high", "Marine/deep-cycle battery"),
    (r"\binverter\b|shore power|30 ?amp.*shore|50 ?amp.*shore|dogbone adapter",
     "Boat", "Electrical - Shore Power & Inverters", "high", "Shore power / inverter hardware"),
    (r"blue sea|din rail circuit breaker|marine circuit breaker|bus bar|"
     r"terminal block.*marine|battery switch|adjustable bracket-mount ammeter",
     "Boat", "Electrical - Panel & Distribution", "high", "DC panel/distribution hardware"),
    (r"nmea|raymarine|garmin|furuno|lowrance|navico|triducer|multisensor|"
     r"autopilot|chartplotter|vhf radio|\bais\b|radar dome|depth sounder|"
     r"nautical chart",
     "Boat", "Electronics & Navigation", "high", "Marine navigation/comms electronics"),
    (r"bilge pump|bilge switch|bilge float switch|bilge blower|bilge alarm",
     "Boat", "Bilge & Pumps", "high", "Bilge-specific marine equipment"),
    (r"marine wire|tinned copper wire|duplex marine|marine grade adhesive lined",
     "Boat", "Electrical - Wire & Connectors", "high", "Marine-grade (tinned) wire"),
    (r"windlass|anchor chain|anchor rode|anchor windlass|snubber|chain hook",
     "Boat", "Ground Tackle", "high", "Anchoring gear"),
    (r"dock line|fender|cleat|mooring",
     "Boat", "Ground Tackle", "medium", "Docking/mooring gear"),

    # ---------- unambiguous BOAT: mechanical/systems ----------
    (r"thru.hull|thru hull|garboard|scupper|deck drain|vented loop|"
     r"rub strake|bow guard|keel guard",
     "Boat", "Hull, Deck & Fittings", "high", "Marine hull fitting, no non-boat use"),
    (r"\byanmar\b|yamalube|prop puller|\bpropeller\b|shaft zinc|cutless bearing|"
     r"engine anode|\banode\b",
     "Boat", "Engine & Drivetrain", "high", "Marine engine/drivetrain-specific"),
    (r"racor|fuel water separator|fuel line hose|primer bulb|fuel filter|"
     r"marine fuel line",
     "Boat", "Fuel System", "high", "Marine fuel system component"),
    (r"4200 marine|sikaflex|marine sealant|butyl sealant|marine adhesive|"
     r"boatlife|3m 5200|3m 4200",
     "Boat", "Sealants & Adhesives", "high", "Marine-grade sealant/adhesive"),
    (r"boat wash|hull cleaner|boat eraser|star brite|meguiar.?s m\d+",
     "Boat", "Cleaning & Consumables", "high", "Marine cleaning product"),
    (r"soft wood plug|emergency.*plug|life ?jacket|pfd\b|flare kit|epirb|"
     r"man overboard|jackline|tether\b",
     "Boat", "Safety", "high", "Safety/emergency gear"),
    (r"pex\b|sharkbite|john guest|speedfit|water pressure diaphragm|"
     r"marine toilet|holding tank|macerator|head pump|vented loop",
     "Boat", "Plumbing & Freshwater/Waste", "medium", "Onboard plumbing/head system"),
    (r"propane|marine stove|gimbal.*stove|alcohol stove",
     "Boat", "Galley", "medium", "Galley appliance/fuel"),
    (r"watermaker|freshwater pump|water heater.*marine",
     "Boat", "Plumbing & Freshwater/Waste", "high", "Onboard water system"),
    (r"cabin fan|marine fan|dorade|cowl vent|solar vent",
     "Boat", "Ventilation", "medium", "Cabin ventilation"),
    (r"trailer.*(wiring|connector|light)|boat trailer",
     "Boat", "Trailer", "medium", "Trailer wiring/hardware"),
    (r"12v refrigerat|12v freezer|marine refrigerat",
     "Boat", "Galley", "high", "12V marine refrigeration"),

    # ---------- shared shop / electrical tools ----------
    (r"crimp|wire stripper|ferrule|heat shrink|multimeter|alligator clip|"
     r"test lead|butt connector|wire connector|inline fuse|fuse holder|"
     r"fuse assortment|circuit breaker\b(?!.*marine)|cable gland|liquid tape|"
     r"conformal coating",
     "Shared", "Electrical Tools & Supplies", "medium", "Electrical work - could be boat or shop"),
    (r"caliper|hex bit|socket set|wrench\b|gear puller|oil filter wrench|"
     r"oil extractor|strap wrench|tool bag|heat gun|drill press|precision block",
     "Shared", "Tools", "medium", "General tool - not project-specific"),
    (r"screw set|bolt assortment|cap screw|washer\b|cotter pin|eye bolt|"
     r"eye nut|swivel\b|piano hinge|stainless steel.*fastener",
     "Shared", "Fasteners & Hardware", "medium", "Generic fastener stock"),
    (r"hose barb|\bnpt\b|barb fitting|compression tube fitting|brass tee|"
     r"pipe plug|check valve|ball valve|shut off valve|vinyl tubing|"
     r"silicone tubing|quick connect coupler",
     "Shared", "Fittings & Hose", "medium", "Generic fluid fittings"),

    # ---------- FAB: 3D printing / CNC (Dark Star) ----------
    (r"filament|creality|k2 plus|build plate|ptfe tube|orcaslicer|3d print",
     "Fabrication", "3D Printing", "high", "3D printer consumable/part"),
    (r"router bit|end mill|collet\b|spindle\b|cnc\b|variable frequency drive|\bvfd\b",
     "Fabrication", "CNC & Machining", "high", "CNC tooling"),
    (r"plexiglass|acrylic sheet|carbide.*bit|woodworking tape",
     "Fabrication", "Shop Materials", "medium", "Fab/shop material, not boat-specific"),

    # ---------- AMBIGUOUS ----------
    (r"epoxy resin|mould release|mold release|fiberglass|resin mixer",
     "AMBIGUOUS", "Composites & Molding", "low", "Fiberglass repair (boat) OR mold-making (business)"),
    (r"led strip|cob led|led diode|flicker led",
     "AMBIGUOUS", "Lighting", "low", "LED lighting - cabin OR shop/other use"),
    (r"submersible pump|fountain pump|aquarium pump",
     "AMBIGUOUS", "Pumps", "low", "Generic 12V/AC pump - unclear which use"),
    (r"electrical outlet box|surface mount backbox|leviton|newhouse",
     "AMBIGUOUS", "Electrical Rough-In", "low", "AC outlet boxes - boat/house AC or shop"),
    (r"din rail|terminal block|optocoupler|buck converter|breakout board|"
     r"esp32|arduino|power supply\b|switching power",
     "AMBIGUOUS", "Electronics & Controls", "low", "Controls - boat DC panel or other project"),

    # ---------- clearly PERSONAL / household ----------
    (r"biltong|jerky|grass fed|elderberry|fish oil|shampoo|conditioner|"
     r"nail clipper|reading glasses|loofah|sleeping bag|area rug|faux fur|"
     r"vitamin|supplement|snack|cereal|coffee pods?\b|paper towel|toilet paper|"
     r"dish soap|laundry|deodorant|toothpaste|razor blade cartridge",
     "Personal", "Groceries & Household", "high", "Food/household consumable"),
    (r"shorts for women|maxi skirt|skort|dress\b|leggings|sneakers|jeans\b|"
     r"jacket for men|jacket for women",
     "Personal", "Apparel", "high", "Clothing"),
    (r"controller dongle|video game|board game|dice game|action figure|"
     r"poi\b|hockey (tape|stick)",
     "Personal", "Recreation", "high", "Not project-related"),
    (r"waxed thread|beading|sewing thread|leather craft",
     "Personal", "Crafts & Hobby", "medium", "Craft supply, not boat/fab specific"),
]


def classify(name: str):
    hay = name.lower()
    for pat, cat, sub, conf, why in RULES:
        if re.search(pat, hay, re.I):
            return cat, sub, conf, why
    return "UNCLASSIFIED", "", "none", "No rule matched - needs manual review"


def reconcile(rule_cat: str, rule_conf: str, likely_boat: str):
    """Fold the earlier-pass likely_boat tag in as a second opinion.
    Doesn't silently overrule the regex hit; flags disagreement instead."""
    if likely_boat == "strong" and rule_cat not in ("Boat",):
        return "disagreement: earlier pass=strong-boat, rules=" + rule_cat
    if likely_boat == "unlikely" and rule_cat == "Boat":
        return "disagreement: earlier pass=unlikely, rules=Boat"
    if likely_boat in ("strong", "likely") and rule_cat == "UNCLASSIFIED":
        return "earlier pass flagged boat-likely; rules found nothing - manual check"
    return ""


def main():
    with open(SRC, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    out_rows = []
    for r in rows:
        cat, sub, conf, why = classify(r["product_name"])
        note = reconcile(cat, conf, r["likely_boat"])
        out_rows.append({
            "order_date": r["order_date"],
            "item_name": r["product_name"][:120],
            "unit_price": r["unit_price"],
            "qty": r["qty"],
            "line_total": r["total_amount"],
            "url": f"https://www.amazon.com/dp/{r['asin']}" if r["asin"] else "",
            "category": cat,
            "subcategory": sub,
            "confidence": conf,
            "rationale": why,
            "review_flag": "REVIEW" if conf in ("low", "none") or note else "",
            "prior_pass_likely_boat": r["likely_boat"],
            "prior_pass_note": note,
            "mixed_order": r["mixed_order"],
            "returned": r["returned"],
            "account": "Personal (Amazon.com)",
            "asin": r["asin"],
            "order_id": r["order_id"],
            "full_title": r["product_name"],
        })

    fields = list(out_rows[0].keys())
    with open(OUT, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(out_rows)

    # ---- console summary ----
    from collections import Counter, defaultdict
    cat_counts = Counter(r["category"] for r in out_rows)
    cat_spend = defaultdict(float)
    for r in out_rows:
        try:
            cat_spend[r["category"]] += float(r["line_total"] or 0)
        except ValueError:
            pass

    print(f"written: {OUT}\nrows: {len(out_rows)}\n")
    print("=== spend by category ===")
    for cat, n in cat_counts.most_common():
        print(f"{cat:15s} items={n:4d}  spend=${cat_spend[cat]:,.2f}")
    total = sum(cat_spend.values())
    print(f"\nTOTAL: ${total:,.2f}")

    review_n = sum(1 for r in out_rows if r["review_flag"] == "REVIEW")
    review_spend = sum(float(r["line_total"] or 0) for r in out_rows if r["review_flag"] == "REVIEW")
    print(f"\n=== needs review === {review_n} of {len(out_rows)} (${review_spend:,.2f})")

    disagree = [r for r in out_rows if r["prior_pass_note"]]
    print(f"\n=== disagreements w/ earlier pass === {len(disagree)}")
    for r in disagree[:20]:
        print(f"- [{r['prior_pass_likely_boat']} vs {r['category']}] {r['item_name'][:70]}  ({r['prior_pass_note']})")


if __name__ == "__main__":
    main()
