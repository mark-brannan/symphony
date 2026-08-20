#!/usr/bin/env python3
"""Rebuild amazon-orders-for-review.csv from the raw personal-Amazon export.

RECOVERY.md's crux: the original file's `likely_boat` column was a per-item
human/LLM judgment call (is this actually for Symphony, vs. household, vs.
Dark Star LLC fab?) - not derivable from the raw export by any deterministic
rule. That judgment is NOT recoverable byte-for-byte. What follows is a
FRESH reconstruction of that judgment, informed by:
  - Symphony was acquired 2024-07-23 (maintenance/log.md) - nothing before
    that date can be a boat purchase, so it's dropped outright.
  - order-level context: what else shipped in the same order (marine
    brands/parts, boat manuals, boat-plumbing/safety items => strong signal;
    smart-home/Tuya/Zigbee, Arduino/ESP32/breadboard hobby-electronics,
    apparel, generic phone/USB accessories with no boat co-item => excluded).
  - date-clustering with the confirmed Feb-May 2025 DC-electrical-refit
    purchase pattern for otherwise-standalone wire/terminal/fuse hardware.

Every general-tier row here is a judgment call, not a recovered fact - see
the conversation this was built in before treating this file as ground
truth. `returned` and everything else (dates, prices, ASINs, order IDs) IS
mechanically exact, cross-referenced against "Your Returns & Refunds/Returns
Status.csv" (order-level: any item in an order with a return record on file
is flagged).
"""
import csv

SRC_ORDERS = "Order History.csv"          # from Your Orders.zip / Your Amazon Orders/
SRC_RETURNS = "Returns Status.csv"        # from Your Orders.zip / Your Returns & Refunds/
OUT = "amazon-orders-for-review.csv"

ACQUIRED = "2024-07-23"  # maintenance/log.md - earliest logged Symphony work

# (order_id, asin) -> likely_boat ("strong" | "likely" | "" for excluded)
# Only entries needed are for rows that pass classify_electrical() in
# extract_electrical.py; everything else is irrelevant to the rebuild.
JUDGMENT = {
    # 2024-08-01: marine CO alarm, deck plate key, propane alarm in same order
    ("112-2308650-1425824", "B0CHW73MCS"): "strong",
    ("112-2308650-1425824", "B0CHW3XP9X"): "strong",
    ("112-9242778-9600227", "B0BCPJJXK7"): "strong",
    ("112-4816312-3715429", "B00C0KL1OM"): "likely",
    ("112-4816312-3715429", "B094WC1GRM"): "strong",
    ("112-6563954-4977847", "B0BHQ7SJH5"): "strong",
    ("111-5478146-6685035", "B0DC35C7RB"): "likely",
    ("112-3333873-8477002", "B0C6PM9KGY"): "",  # Dupont/JST kit - hobby-electronics headers, not boat DC wiring
    ("112-8658431-7022642", "B0CZKMHGBD"): "strong",
    ("112-5048258-4948218", "B0C3H63W94"): "likely",  # dome-light bulb, refit pattern, weak/standalone signal
    ("112-4830903-1294611", "B09ZTTHQRG"): "",  # HDMI repair connector - unrelated hobby-electronics item riding along a boat order
    ("113-6392425-7712259", "B0CWG4XNL4"): "strong",
    ("113-4693954-5232217", "B086Z3H4X8"): "strong",
    ("112-1785065-2505059", "B07L1PMQ58"): "likely",  # MILAPEAK terminal block strip, same order as marine wire/fuse box
    ("112-1785065-2505059", "B0B2MLNV87"): "strong",
    ("112-1785065-2505059", "B0B9BM2X3F"): "strong",
    ("112-8500998-7007449", "B0CHG11J1R"): "likely",
    ("112-8500998-7007449", "B0C9CJYRHJ"): "strong",
    ("112-8500998-7007449", "B08GCJL8PC"): "likely",  # 73pcs terminal block set
    ("112-8500998-7007449", "B08YY9B3KD"): "strong",
    ("112-8500998-7007449", "B0D8L9HJXN"): "likely",
    ("112-8500998-7007449", "B0B45BNHPQ"): "strong",
    ("112-6053190-5016260", "B0DMW75PLW"): "",  # FCOB 10mm connector kit - smart-home/Tuya order, not boat
    ("112-6053190-5016260", "B0C8D4JNJK"): "",  # FCOB CCT strip "Bedroom Home Decor"
    ("112-6053190-5016260", "B0CL6HDTQ3"): "",  # RF remote controller
    ("113-3616503-7032246", "B0BNQ5JNWZ"): "likely",
    ("113-5183215-0954633", "B0D21LDM9R"): "",  # BSIDE multimeter, standalone, no boat signal
    ("113-5183215-0954633", "B0CKXCQKMG"): "",  # DT-830D multimeter, standalone
    ("113-2842144-9185819", "B07YZ4QGPC"): "likely",  # Qibaok crimper, same order as Ancor marine heat gun
    ("112-5599667-6876243", "B0BF8ZW6PW"): "likely",  # HKS fork connector (Blue)
    ("112-7426061-4846625", "B0BF8P9915"): "likely",  # HKS fork connector (Red), same order as boat-plumbing PVC fitting
    ("112-5465118-7644236", "B0BRZT6R7H"): "strong",  # 6AWG battery cable, same order as "Boatowners" manual
    ("112-5082001-4964211", "B07WNVSMPN"): "likely",  # iCrimp ring terminal crimper, same order as marine circuit breaker
    ("112-3258369-1771411", "B00BC39YFQ"): "likely",  # Klein wire stripper
    ("112-3258369-1771411", "B08BL4S5YJ"): "strong",  # Recoil terminal covers
    ("112-3258369-1771411", "B094FWYT3V"): "strong",  # TKDMR marine-grade ring lugs
    ("112-3258369-1771411", "B0D9N8JXN6"): "strong",  # RED WOLF bus bar
    ("114-8562031-7065040", "B0BLYM1RLN"): "likely",  # Joinfworld MRBF fuse block "Boat Truck RV"
    ("114-0067633-9897831", "B0D1V7X9BL"): "likely",  # DaierTek ANL fuse block, same order as Blue Sea SI-ACR
    ("112-0658120-9713825", "B0D7VTMTBH"): "likely",  # APIELE terminal block, refit-window date cluster
    ("112-8764107-6446619", "B07DM1HQ75"): "likely",  # uxcell terminal block, refit-window date cluster
    ("112-5416621-6626637", "B0BLYM1RLN"): "likely",  # Joinfworld MRBF fuse block
    ("112-4392606-2917001", "B0BN62LSBJ"): "likely",  # wire ferrules kit
    ("112-4392606-2917001", "B071SL6PQS"): "likely",  # multimeter test probe
    ("112-1842048-2169838", "B092ZN6TGP"): "likely",  # ring terminal lugs, battery cable
    ("112-0797475-1634649", "B00E1UUVT0"): "likely",  # TEMCo hammer lug crimper
    ("112-0797475-1634649", "B0006M6Y5M"): "likely",  # Klein crimping tool
    ("112-0797475-1634649", "B0CRDH4W7B"): "likely",  # Preciva ferrule crimper
    ("112-0428324-7498629", "B0CXJH6K55"): "likely",  # RJ45 crimp tool, same order as bilge pump switch panel
    ("112-8592989-7647420", "B09W9Q5HMH"): "likely",  # cable gland kit
    ("112-8592989-7647420", "B0CXN5KQG3"): "strong",  # YETLEBOX watertight junction box
    ("112-3527227-0373836", "B0CPX2C2J3"): "",  # nylon spade connector kit - weak/no boat signal
    ("112-2727699-0607460", "B0D5L9421T"): "likely",  # heat shrink spade connector kit
    ("112-3646206-1839414", "B0BNQ5JNWZ"): "likely",  # DC-DC USB-C buck converter, same product line
    ("112-1707496-7085828", "B01H9XALY0"): "likely",  # blade fuses
    ("112-1707496-7085828", "B011CO8806"): "likely",  # battery terminal cover
    ("112-0322049-8183474", "B0CD2512JV"): "",  # Freenove ESP32 breakout board - ham-radio/hobby order, not boat DC
    ("112-8965906-0825003", "B0CJY4413M"): "strong",  # ECO-WORTHY 280Ah LiFePO4 house battery
    ("112-7394883-9013819", "B0CPSXZQ4F"): "strong",  # ECO-WORTHY 2AWG battery cable, same-day pairing
    ("112-7697118-1697035", "B0DNS61WPR"): "",  # EBL Group 48R automotive starting battery, not house bank
    ("112-7873356-5942647", "B0CJY4413M"): "strong",  # second ECO-WORTHY 280Ah LiFePO4 battery
    ("112-4727950-4092200", "B0CY4FP6GP"): "likely",  # ANL fuse holder, same order as boat-plumbing tubing
    ("112-3972519-5565818", "B0BV39296T"): "likely",  # battery terminal connectors
    ("112-7547463-4337803", "B0D31GT2TX"): "likely",  # copper bus bar stock
    ("112-6875463-1017806", "B0CFXRG8M6"): "strong",  # copper bus bar stock, same order as RV/boat freshwater pump
    ("112-5217289-0387429", "B082RYMKRN"): "strong",  # END GAME "Marine Grade" battery cables
    ("112-4351057-2051417", "B0DT48T7CB"): "",  # Freenove ESP32/Arduino breakout board, standalone hobby item
    ("112-4654506-7246627", "B0D87747HV"): "strong",  # "Marine Grade" heat shrink tubing
    ("112-2371802-2153802", "B0CY4FP6GP"): "likely",  # ANL fuse holder "Trucks Boats"
    ("112-6500575-9934638", "B07M6PLJWF"): "strong",  # blade fuse box "Automotive Car Boat Marine Trike"
    ("112-5850329-7738605", "B0C4VC1HW5"): "strong",  # 2AWG battery cable "Marine Boat RV"
    ("112-4314546-9833029", "B084GWYX42"): "strong",  # Wirefy heat shrink kit, same order as Wirefy wire-lug kit
    ("112-1352300-6313828", "B0BV21S2VL"): "likely",  # HKS crimping tool
    ("112-1352300-6313828", "B097ZNCKMZ"): "likely",  # mankk wire ferrules kit
    ("112-9246656-8916248", "B0C6P6PWMX"): "likely",  # irhapsody ANL fuse holder kit
    ("112-8032615-5154632", "B0B27X5T7S"): "strong",  # Teansic fork connector, same order as 10AWG Triplex marine wire
    ("112-8032615-5154632", "B0B28BXBRR"): "strong",  # XALXMAW lever wire connector
    ("112-3479659-7093035", "B0C3LBWSTZ"): "likely",  # lever wire connector splicing kit
    ("112-5314130-1683440", "B09XQN3J6N"): "likely",  # wire ferrules kit
    ("112-4898569-8385036", "B0DPC1HV71"): "",  # GXILEE COB strip "Cabinet, Bedroom, Kitchen, Closet" - household decor
    ("112-4898569-8385036", "B0CPSXZQ4F"): "likely",  # ECO-WORTHY 2AWG battery cable, same order as boat hose mender
    ("112-2616490-8528223", "B08QMLSMC6"): "",  # splicing wire connector kit - apparel/personal order
    ("112-2634621-3006649", "B0851CG97T"): "",  # DC barrel pigtail cable - generic CCTV/camera accessory
    ("112-7684093-9767435", "B0FM873RCT"): "",  # USB-C splitter charger cable - generic phone accessory
    ("112-0904016-1387426", "B0DCBB5MM2"): "",  # 10AWG extension cord w/ welder plug - shop power, not boat DC
    ("112-8238227-7727435", "B0BF9LNCDK"): "likely",  # HKS fork connector (Yellow), same product line
    ("112-8761524-6478663", "B0728H6KPV"): "",  # Nintendo Switch charger - personal
    ("112-0145622-4494663", "B0C8HHV9DK"): "",  # Anker iPhone charger - personal
    ("111-3580742-7917035", "B09QW1NPZD"): "",  # USB-C splitter charger - personal
    ("112-6264827-0750647", "B0B3WVG2V9"): "",  # DROK AC multimeter - shop/Dark Star, no boat signal
    ("112-7936570-9067432", "B078SQ3F68"): "",  # COB LED angel-eyes DRL fog light - car parts, not boat
    ("112-3766025-1050637", "B0C4SKT7CV"): "",  # GIDEALED COB strip "Under Cabinet Ambiance Lighting" - household
    ("112-7966425-0101821", "B0CBV62FJK"): "",  # BTF-lighting connector - apparel/personal order
    ("112-7966425-0101821", "B0FWQXCMGZ"): "",  # BTF-lighting connector
    ("112-6871422-7237802", "B0D6QVB9CR"): "",  # BTF-lighting DC barrel connector cable
    ("112-6871422-7237802", "B0D9GRZYFN"): "",  # DC power splitter cable
    ("112-4783048-9528238", "B0DSVS2KYF"): "likely",  # Waziaqoc bus bar terminal block
    ("112-4783048-9528238", "B097GTBKS3"): "likely",  # DC-DC step-up voltage regulator
    ("112-3764105-6190638", "B07D33HVQW"): "likely",  # WMYCONGCONG blade fuse holder
    ("112-8457468-0238655", "B0FP4H9LKG"): "",  # DC barrel terminal cable "for CCTV" - generic camera accessory
    ("114-2846914-9751440", "B01EOY7LTA"): "likely",  # Klein electronics screwdriver "Ideal for Terminal Blocks"
}


def load_returned_order_ids():
    with open(SRC_RETURNS, newline="", encoding="utf-8-sig") as f:
        return {r["Order ID"] for r in csv.DictReader(f)}


def main():
    returned_ids = load_returned_order_ids()
    with open(SRC_ORDERS, newline="", encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))

    out = []
    unmatched = []
    for r in rows:
        date = r["Order Date"][:10]
        if date < ACQUIRED:
            continue  # can't be a boat purchase - predates Symphony
        key = (r["Order ID"], r["ASIN"])
        likely_boat = JUDGMENT.get(key)
        if likely_boat is None:
            # not one of the electrical-tier candidates we pre-classified;
            # irrelevant rows (extract_electrical.py re-filters by product
            # name) get an empty judgment, which is fine since they won't
            # pass classify_electrical() anyway.
            likely_boat = ""
        out.append({
            "product_name": r["Product Name"],
            "order_date": date,
            "qty": r["Original Quantity"],
            "unit_price": r["Unit Price"],
            "total_amount": r["Total Amount"],
            "asin": r["ASIN"],
            "order_id": r["Order ID"],
            "returned": "Y" if r["Order ID"] in returned_ids else "",
            "status": r["Order Status"],
            "likely_boat": likely_boat,
            "mixed_order": "",
        })

    fields = ["product_name", "order_date", "qty", "unit_price", "total_amount",
              "asin", "order_id", "returned", "status", "likely_boat", "mixed_order"]
    with open(OUT, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(out)
    print(f"written: {OUT}\nrows: {len(out)} (from {len(rows)} raw, {ACQUIRED} cutoff)")


if __name__ == "__main__":
    main()
