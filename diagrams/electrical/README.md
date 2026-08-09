# Electrical diagrams

Sample diagrams from the 2026-08 diagram-tool evaluation. Component specs
(bank capacity, charger models, fuse sizes) are illustrative placeholders,
not as-built values.

## Files

- `symphony-dc-overview.drawio` — editable source for the DC system
  overview. Open at [app.diagrams.net](https://app.diagrams.net), in the
  draw.io desktop app, or with the VS Code draw.io extension. Export to
  SVG/PNG/PDF from File → Export.
- `symphony-dc-overview.svg` — hand-authored SVG of the same system.
  Renders directly on GitHub and in any browser; editable as text.
- `voltplan/symphony.json` — system description for the VoltPlan API.
- `voltplan/symphony.png` — diagram generated from it.

## Regenerating the VoltPlan diagram

```bash
curl -s -X POST https://voltplan.app/api/diagram/generate \
  -H "Content-Type: application/json" -H "Accept: image/png" \
  -d @voltplan/symphony.json -o voltplan/symphony.png
```

Swap the Accept header to `image/svg+xml` for SVG. Rate limit 30 req/min,
no auth. VoltPlan models a single battery bank — it cannot represent the
starter/house split or the DC-DC charger topology.

## Victron symbol libraries

- [romx/vectron](https://github.com/romx/vectron) — SVG stencils of Victron
  products (MultiPlus, Orion, Lynx, MPPTs, monitoring) plus Visio `.vssx`
  files. The SVGs can be imported into draw.io as a custom shape library.
