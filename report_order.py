# -*- coding: utf-8 -*-
"""report_order.py -- headless check of the recovered computation order.

    freecadcmd.exe report_order.py <file.FCStd> [json=<out.json>]

Prints the step list, the tip chain of every body, and whether the dependency
order agreed with the tip chain. Read-only, never saves.
Exit code 1 when the order is inconsistent or empty.
"""

import json
import os
import sys

import FreeCAD

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import selection_interface_for_llm_lib as tl  # noqa: E402


def main():
    args = [a for a in sys.argv[1:]]
    paths = [a for a in args if a.lower().endswith(".fcstd")]
    options = dict(a.split("=", 1) for a in args if "=" in a and not a.endswith(".fcstd"))
    if not paths:
        print("usage: freecadcmd.exe report_order.py <file.FCStd> [json=out.json]")
        return 2
    doc = FreeCAD.openDocument(paths[0])
    doc.recompute()
    timeline = tl.timeline(doc)
    print("document : %s" % doc.Label)
    print("steps    : %d" % len(timeline["steps"]))
    for body, chain in timeline["bodies"].items():
        print("tip chain: %s -> %s" % (body, " -> ".join(chain)))
    print("")
    for step in timeline["steps"]:
        print("%2d/%d  %-18s %-26s %-20s %s"
              % (step["index"], len(timeline["steps"]), step["label"],
                 step["type"], step["profile"] or "", step["detail"]))
    for warning in timeline["warnings"]:
        print("WARNING: %s" % warning)
    for note in timeline.get("notes") or []:
        print("note: %s" % note)
    if options.get("json"):
        payload = {
            "document": doc.Name,
            "steps": [{k: v for k, v in s.items() if not k.startswith("_")}
                      for s in timeline["steps"]],
            "bodies": timeline["bodies"],
            "warnings": timeline["warnings"],
        }
        with open(options["json"], "w", encoding="utf-8") as fh:
            json.dump(payload, fh, indent=2)
        print("json     : %s" % options["json"])
    sys.stdout.flush()
    ok = bool(timeline["steps"]) and not any("!= tip chain" in w
                                             for w in timeline["warnings"])
    print("RESULT: %s" % ("PASS" if ok else "FAIL"))
    sys.stdout.flush()          # freecadcmd drops whatever is still buffered at exit
    return 0 if ok else 1


sys.exit(main())
