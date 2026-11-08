# Changelog

All notable changes of this addon. The version number lives in
`freecad/SelectionInterfaceForLLM/version.py` and must match `<version>` in
`package.xml`; the Addon Manager compares `package.xml` only.

## 2.1.0 - 2026-11-08

Addon packaging round: the same tool, now a real FreeCAD addon.

- **Modern addon layout**: the code moved to `freecad/SelectionInterfaceForLLM/`
  (`__init__.py`, `init_gui.py`, `commands.py`, `workbench.py`, `interface.py`,
  `resources/`), so it no longer needs `sys.path` tricks and no longer pollutes the
  global module namespace.
- **A workbench instead of a macro**: "Selection interface" appears in the workbench
  selector with two commands, `Building steps panel` and `GIF of the whole build`.
  The `.FCMacro` is kept in `dev/` as a developer shim only.
- **`package.xml`, `pyproject.toml`, `LICENSE-Code` (LGPL-2.1-or-later),
  `LICENSE-Assets` (CC-BY-SA-4.0), SPDX headers and an SVG icon** for the Addon
  Index, with `<freecadmin>1.1.0</freecadmin>` (tested on 1.1.4 only).
- **Cross-platform file opening**: `os.startfile` and `explorer.exe /select` are
  replaced by `QDesktopServices.openUrl` with a per-platform fallback, so the addon
  is not Windows-only any more. `reveal_in_explorer` is now
  `reveal_in_file_manager`.
- **LLM handoff is now a file as well as the clipboard**: the request is written to
  `<Downloads>/FreeCAD_timelapse/llm_requests/` and its path is shown in the status
  line, and the request gained a section 0 explaining the tooling an agent should
  use (its own FreeCAD skill/MCP bridge, `freecadcmd` headless checks, asserting on
  printed values) while stating that the addon ships no skill and calls no service.
- Version number single-sourced in `version.py`.

## 2.0.0 - 2026-11-08

- Renamed from *Timelapse features* to *Selection interface for LLM*: folder,
  library module, macro file, dock title, Qt object names and the console prefix.
  Behaviour unchanged; the GIF is still written as `timelapse_<label>.gif` under
  `Downloads/FreeCAD_timelapse/` so existing run folders keep working.

## 1.7.0 - 2026-11-08

- The profile of the selected feature is drawn as a thick orange line: the driver
  clamps `LineWidth` (measured 709/850/1017/1219 orange pixels for width 1/3/6/10,
  `PointSize` ignored), so the sketch edges are rebuilt as small tubes in the Coin
  scene graph, wrapped in `SoAnnotation`, sized from the camera zoom
  (`PROFILE_LINE_PIXELS = 5.5`), never added to the document, and dropped by
  restore / close / document switch / GIF frames.

## 1.6.0 - 2026-11-08

- New "base / fused results" checkbox (unticked by default): a `PartDesign::FeatureBase`
  or a `Part::MultiFuse`/`Part::Fuse` is drawn only at its own step and the objects it
  absorbs are hidden from then on, which removes the coincident duplicate surfaces that
  looked like a mesh (measured: feature base, fusion and both halves are the same
  99563.843 mm3 solid, 100.00 % common volume).
- See-through now also applies to such a step, so what it swallows stays visible.

## 1.5.0 - 2026-11-08

- "show also" checkboxes (datum objects, profile sketch, other bodies), all ticked by
  default.
- Ordering fix: a mirror or a boolean that consumes a whole body is sorted after that
  body is completely built (on a 68-step assembly the mirrors moved from steps
  4/10/19/28 to 37/57/58/59, with the step count unchanged).

## 1.4.0 - 2026-11-08

- Display-style selector (solid + edges, solid, edges only, transparent, points),
  display of datum planes and of the driving sketch, per-level display contract built
  on `DisplayModeBody = 'Through'`.

## 1.3.0 - 2026-11-08

- Note box and "copy to clipboard description for LLM", with a feature-type-agnostic
  description of the selected feature and the document's full computation order.

## 1.0.0 - 2026-11-08

- First working version: computation order recovered from the dependencies and the
  tip chain, step-by-step panel, GIF export with blank-frame rejection and
  change metrics, two independent test harnesses.
