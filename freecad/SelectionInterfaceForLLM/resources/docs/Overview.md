# Selection interface for LLM — overview

A FreeCAD addon that replays the **real computation order** of a PartDesign
document. It does not look at the tree in alphabetical or creation order: it sorts
the objects by their dependencies, then checks that order against each body's
`Tip` → `BaseFeature` chain, and reports any disagreement.

## What it gives you

* **The ordered list of building steps** (one row per feature, with its type and
  what it is built from), for the whole document, all bodies included.
* **A step browser**: `< step` / `step >`, a spin box, `reset`, `final`, or click a
  row. The 3D view shows the part as it was after that step: on every body, only the
  feature built last is drawn, datums appear as they are reached, and a mirrored or
  fused result absorbs the shapes it contains instead of drawing them twice.
* **The sketch that gives birth to the feature**, drawn as a thick orange line,
  visible even through the material it was padded or revolved into.
* **A display-style selector**: solid + edges, solid, edges only, transparent,
  points.
* **A GIF of the whole build**: the camera is fitted once on the final part and the
  viewing **angle** is preserved for every frame (the zoom and the centring may
  move); one PNG per step is written to
  `<Downloads>/FreeCAD_timelapse/<document>_<date>/frames/`, with a manifest holding
  the per-frame metrics and any warning. Frames that look identical because the
  change is interior are reported instead of being shipped silently.
* **An LLM handoff**: type a modification, pick a feature, press *copy to clipboard
  description for LLM*. The text names the source file (read-only, with its SHA256
  to compare), the copy to create, the selected feature (label, internal name, type,
  source sketch or pattern, parameters, volume at that step and at the end), the full
  computation order of the document, and what the result must satisfy. It is also
  written to `<Downloads>/FreeCAD_timelapse/llm_requests/` so an agent can be
  pointed at a file instead of a paste.

## What it never does

* It never saves the document. Every visibility, style, tip and camera change is
  snapshotted when the panel opens and restored when it closes, when you press
  *restore original*, at the end of a GIF run, and when the panel is closed.
* It adds nothing to the document tree: the thick profile line is drawn in the
  viewer's Coin scene graph, not as geometry.
* It has no network access and contacts no service. The LLM part is a text file or
  a clipboard entry; the addon never talks to a model.

## Install

Copy (or clone) this repository into the `Mod` folder of your FreeCAD user data,
so that `package.xml` ends up at
`<user>/Mod/Selection_interface_for_LLM/package.xml`, then restart FreeCAD. The
workbench **Selection interface** appears in the workbench selector, with the
commands *Building steps panel* and *GIF of the whole build*.

## Requirements

FreeCAD 1.1 or newer, Python 3.10+. Pillow and NumPy are used for the GIF and for
the frame metrics; both ship with FreeCAD's own Python, nothing has to be installed.

## Search words

build order, construction order, build timeline, timelapse, time-lapse, feature by
feature, step by step, animation, GIF, datum plane, driving sketch, LLM, PartDesign,
workbench, addon.
