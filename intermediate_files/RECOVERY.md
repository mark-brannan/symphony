# Recovering electrical-components.csv

`intermediate_files/` was wiped between 2026-08-15 and 2026-08-18 (never
committed to git). Recovery state as of 2026-08-18:

## Recovered byte-exact from session transcripts (`~/.claude/projects/-home-solace-symphony/*.jsonl`)

- `extract_electrical.py` (9,038 bytes) — builds `electrical-components.csv`
  from the three sources below. Reconstructed from its Write + 2 Edits in
  session `2fbf748d`.
- `fisheries-line-items.csv` (8,675 bytes) — recovered from a full Read in
  session `1b69ad2f`.
- `categorize_personal.py` (11,444 bytes) — categorizes the personal Amazon
  export; from session `2fbf748d`.
- `electrical-components.head40-excerpt.txt` — first 40 lines of the lost
  output, for validating a rebuild.

## Still missing (both regenerable from Mark's Windows Downloads)

- `amazon-orders-for-review.csv` (was 307,439 bytes) — personal Amazon
  export. Raw source: `/mnt/c/Users/Solace/Downloads/Your Orders.zip`
  (Amazon "Your Orders" data export, 2026-07-30). Regenerate with
  `categorize_personal.py` or adapt `extract_electrical.py`'s reader to the
  raw `Retail.OrderHistory` CSV inside the zip.
- `symphony_amazon_business_categorized.csv` — Dark Star Business orders
  with category tags. Raw source:
  `/mnt/c/Users/Solace/Downloads/orders_from_20240101_to_20260730_20260730_0040.csv`
  (Amazon Business export, 290 lines). The script that added the category
  column (`categorize.py`, 2026-07-30, 11,814 bytes) predates all surviving
  transcripts and is NOT recoverable — but the categories were advisory
  enrichment; `extract_electrical.py` does its own matching, so a rebuild
  can proceed with an uncategorized business file (drop or stub the
  prior-category column).
- `/mnt/c/Users/Solace/Downloads/fisheries-orders.csv` (22 lines) also
  survives, order-level rather than line-item — not needed now that
  `fisheries-line-items.csv` is recovered.

## Validation targets for the rebuilt CSV

174 rows; ~$5,650 total excluding returns; 32 rows flagged returned;
header and first 39 data rows must match the excerpt file.
