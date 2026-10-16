#!/usr/bin/env python3
"""Apply the card's SignalK plugin-config overrides, idempotently. Runs ON the card.

  python3 - <plugin-config-data dir> "<plugins to disable>" <venus host> < halos_card_overrides.py

Sets "enabled": false in each named plugin's config and the Venus MQTT host.
Writes a file only when its value differs, so a second run changes nothing.
Last line: "changed: N" (0 means no SignalK restart is needed).
"""
import json
import sys

d, names, venus = sys.argv[1], sys.argv[2].split(), sys.argv[3]
changed = 0


def edit(path, mutate):
    global changed
    c = json.load(open(path))
    before = json.dumps(c, sort_keys=True)
    mutate(c)
    if json.dumps(c, sort_keys=True) != before:
        json.dump(c, open(path, "w"), indent=2)
        changed += 1
        print(f"set   {path}")
    else:
        print(f"ok    {path}")


for n in names:
    edit(f"{d}/{n}.json", lambda c: c.__setitem__("enabled", False))
edit(f"{d}/venus.json", lambda c: c["configuration"]["MQTT"].__setitem__("host", venus))
print(f"changed: {changed}")
