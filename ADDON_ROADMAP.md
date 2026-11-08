# From this macro to an indexed FreeCAD addon

How `Selection_interface_for_LLM` can become an **official** FreeCAD addon, i.e. an
addon listed in the official Addon Index that the built-in **Addon Manager** shows
to every user (FreeCAD >= 1.0 reads `https://github.com/FreeCAD/Addons`,
`Data/Index.json`; FreeCAD < 1.0 used the legacy `FreeCAD/FreeCAD-addons`).

Everything below is checked against the current official documentation,
[Addon Academy](https://freecad.github.io/Addon-Academy/) (repository
`FreeCAD/Addon-Academy`, branch `main`), not against memory:

| question | source |
|---|---|
| what must an indexed addon satisfy | `Source/Topics/Addon-Index/Index/Qualities.md` |
| how to get into the index | `Source/Guides/Publishing/Indexed.md` |
| `package.xml` tags | `Source/Topics/Structuring/Manifest/index.md` |
| recommended directory layout | `Source/Topics/Structuring/index.md` |
| license choice and SPDX strings | `Source/Topics/Licensing/index.md` |
| a macro-shaped addon example | `Source/Demos/Macro/index.md` |
| scaffolding generator | https://github.com/FreeCAD/Addon-Template |

## 1. The shape to choose: workbench, not macro

The documentation distinguishes the content types `workbench`, `macro`,
`preferencepack`, `bundle`, `machine` and `other` (`Manifest#content`). A `macro`
content item is **one `.FCMacro` file**: on install the Addon Manager copies each
`<file>` entry of the item into the user's macro directory
(`Demos/Macro/index.md`), there is no library folder and no persistent UI.

This tool ships **two** parts — a launcher and a ~96 kB library — and it lives in a
dock, with a toolbar-less but persistent panel, a GIF engine and a Qt preview. So the
target is:

```xml
<content>
  <workbench>
    <classname>SelectionInterfaceWorkbench</classname>
    <icon>resources/icons/Logo.svg</icon>
  </workbench>
</content>
```

i.e. a **workbench addon with one command** that opens the dock. That also removes
the whole `.FCMacro` path-resolution dance (~70 lines of `_candidate_dirs()`), since
an installed workbench is importable as a normal Python package.

## 2. Target directory layout (modern, namespaced)

`Structuring/index.md` asks new addons for the namespaced layout, and the page is
explicit that the legacy `Init.py`/`InitGui.py` layout is "strongly discouraged":

```
Selection_interface_for_LLM/
├─ package.xml
├─ pyproject.toml
├─ README.md
├─ CHANGELOG.md
├─ LICENSE-Code                     (LGPL-2.1-or-later, see §4)
├─ LICENSE-Assets                   (CC-BY-SA-4.0 for the icon)
├─ freecad/
│  └─ SelectionInterfaceForLLM/
│     ├─ __init__.py
│     ├─ init_gui.py                workbench + command registration
│     ├─ interface.py               <- today's selection_interface_for_llm_lib.py
│     └─ resources/
│        ├─ icons/Logo.svg
│        └─ translations/
└─ tests/                           <- today's check_timelapse.py, report_order.py
```

Mapping of the present files:

| today | becomes | note |
|---|---|---|
| `selection_interface_for_llm_lib.py` | `freecad/SelectionInterfaceForLLM/interface.py` | one file, no code change needed for the move |
| `Selection_interface_for_LLM.FCMacro` | dropped | replaced by `init_gui.py` + command |
| `check_timelapse.py` | `tests/check_timelapse.py` | already dependency-free (Pillow + numpy) |
| `report_order.py` | `tests/report_order.py` | already headless (freecadcmd) |
| `README.md`, `task.md` | `README.md`, `freecad/SelectionInterfaceForLLM/resources/docs/Overview.md` | |

`init_gui.py` holds the two objects the manifest points at:

```python
class ShowPanelCommand:            # FreeCADGui.Command
    def Activated(self):
        from . import interface
        interface.open_panel()

class SelectionInterfaceWorkbench(FreeCADGui.Workbench):
    MenuText = "Selection interface"
    ToolTip = "Step through the computation order of the document"
    Icon = "resources/icons/Logo.svg"   # must match <classname> in package.xml
```

## 3. `package.xml` — draft, ready to fill in

Required tags per `Manifest/index.md`: `name`, `version`, `date`, `description`,
`maintainer`, `license`, `icon`, `content`. `<url type="repository">` is required and
its `branch` attribute **must match the branch the manifest lives on** (today the
repository is on `master`; renaming it to `main` or to a dedicated `release` branch
is recommended in `Qualities#Best Practices`).

```xml
<?xml version="1.0" encoding="UTF-8" standalone="no" ?>
<package format="1" xmlns="https://wiki.freecad.org/Package_Metadata">
  <name>Selection interface for LLM</name>
  <description>Shows the real computation order of a PartDesign document, displays
    any step (datum planes and driving sketches included) without touching the
    model, keeps the viewing angle, writes the build-up to a GIF, and copies a
    ready-to-use description of one feature to the clipboard for an LLM.</description>
  <version>2.0.0</version>
  <date>2026-11-08</date>
  <maintainer email="CHANGE_ME">CHANGE_ME</maintainer>
  <license file="LICENSE-Code">LGPL-2.1-or-later</license>
  <license file="LICENSE-Assets">CC-BY-SA-4.0</license>
  <url type="repository" branch="main">https://github.com/Tithanium/Selection_interface_for_LLM</url>
  <url type="readme">https://github.com/Tithanium/Selection_interface_for_LLM/raw/main/README.md</url>
  <url type="bugtracker">https://github.com/Tithanium/Selection_interface_for_LLM/issues</url>
  <freecadmin>1.1.0</freecadmin>
  <icon>freecad/SelectionInterfaceForLLM/resources/icons/Logo.svg</icon>
  <tag>PartDesign</tag>
  <tag>documentation</tag>
  <tag>animation</tag>
  <content>
    <workbench>
      <classname>SelectionInterfaceWorkbench</classname>
      <icon>resources/icons/Logo.svg</icon>
    </workbench>
  </content>
</package>
```

`<freecadmin>1.1.0</freecadmin>` is the honest value: everything in this repository
was measured on FreeCAD 1.1.4 only (`Qualities` forbids advertising more than the
addon actually does). Declaring `1.0.0` would require a test run on 1.0.x first.

## 4. License

`Licensing/index.md`: "If you have no other preferences, the majority of code in the
FreeCAD project is licensed `LGPL-2.1-or-later`", and using it "would make it easy to
incorporate your code into FreeCAD's core". Non-code assets (the icon) should get
`CC-BY-SA-4.0`, shipped as `LICENSE-Code` + `LICENSE-Assets`, both declared with
their own `<license file=...>` tag, plus an SPDX header on every source file:

```python
# SPDX-License-Identifier: LGPL-2.1-or-later
```

The page warns that a non-SPDX string such as `LGPL2` is normalised to the *most
restrictive* match (`LGPL-2.0`), so the exact SPDX identifier matters.

## 5. What this codebase must still change (the real work list)

| # | gap | why the index cares | size |
|---|---|---|---|
| 1 | no `package.xml`, no `pyproject.toml`, no license files, no icon | mandatory tags (`Manifest`) | S |
| 2 | flat layout + `.FCMacro` that manipulates `sys.path` | `Qualities#Best Practices`: namespaced `freecad/<ModName>/`, no `sys.path` games | M |
| 3 | **Windows-only calls**: `winreg` (guarded, falls back to `~/Downloads`), `os.startfile`, `subprocess.Popen(["explorer", ...])` | an indexed addon is offered on Linux and macOS too; `os.startfile` does not exist there | S |
| 4 | no workbench/command: the entry point is a macro | `content` type and `<classname>` | M |
| 5 | Pillow + numpy are imported unconditionally | both are **on** the allow list (`Data/Python/3.14/Allowed-Packages` contains `numpy` and `pillow`) and both ship with FreeCAD's Python (PIL 12.0.0, numpy 1.26.4 measured), so no `<depend>` is needed — but the import should degrade with a clear message if they ever go missing | S |
| 6 | `subprocess.Popen(["explorer", ...])` | the index scans addons with **Bandit** and publishes the reports at `freecad.github.io/Addon-Reports/`; shelling out to Explorer will be reported. Replace with a Qt `QDesktopServices.openUrl` call | S |
| 7 | English-only UI | translations are recommended, not required; `resources/translations/` + `update_translation.py` from the template | M |
| 8 | no user evidence | `Publishing/Indexed.md`: "An addon with no evidence of user testing ... is not yet suitable" | — |
| 9 | repository is brand new | `Qualities#Governance`: "The addon's repository and overall codebase must be at least **30 days old**" | wait |
| 10 | default branch `master`, no release branch | `Qualities#Best Practices`: publish from a stable branch and bump `<version>`/`<date>` per release | S |

What is **already** in good shape, unusually so for a macro:

* no network access at all, no telemetry, no data collection (GDPR clause);
* no work at import time — the panel, the timeline and the GIF engine only run when
  the user invokes the command (`Qualities#Codebase`);
* the document is never saved: every view change is snapshot and restored
  (`snapshot_state` / `restore_state`), which is the kind of side effect the review
  looks at;
* two independent test harnesses (`tests/check_timelapse.py` with `RESULT: PASS`,
  `tests/report_order.py` under `freecadcmd`) — that is the "basic functionality in
  working order" evidence the review asks for;
* commands do not touch FreeCAD's core UI: one dock in the right dock area, and every
  colour/visibility change is reverted.

## 6. Order of work, and how to submit

1. **Scaffold** from the template so the boilerplate matches the current standards:
   `cookiecutter https://github.com/FreeCAD/Addon-Template` (choose LGPL-2.1-or-later
   + CC-BY-SA-4.0, workbench content).
2. Move `selection_interface_for_llm_lib.py` into
   `freecad/SelectionInterfaceForLLM/interface.py`, write `init_gui.py` with the
   workbench and the single `ShowPanelCommand`, drop the `.FCMacro`.
3. Port the three Windows-only calls (§5 row 3 and 6) and re-run both test harnesses
   on Windows; ideally also on a Linux box or a Linux FreeCAD AppImage.
4. Write `package.xml`, the icon, the two license files, SPDX headers, `pyproject.toml`,
   `CHANGELOG.md`; bump `<version>`/`<date>` at each release.
5. Tag a release, keep the development work on a separate branch, and let the indexed
   branch be the stable one.
6. Ask for real users: FreeCAD forum "Addons" subforum, Discord, r/FreeCAD; the review
   explicitly wants evidence of use.
7. When the repository is at least 30 days old, compliant and tested, open an issue on
   `FreeCAD/Addons` (GitHub, type **`Addon - Addition`**) or on the Codeberg mirror,
   or post in the Addons subforum — `Publishing/Indexed.md` lists those three routes.
8. The team reviews, may ask for fixes, then asks for a tagged release; the addon
   appears in the Addon Manager about a day later. Indexed addons are expected to be
   maintained.

## 7. Verification of this document

Facts quoted above were read on 2026-11-08 from:

* `raw.githubusercontent.com/FreeCAD/Addon-Academy/main/Source/Topics/Addon-Index/Index/Qualities.md`
* `.../Source/Guides/Publishing/Indexed.md`
* `.../Source/Topics/Structuring/Manifest/index.md` (tag list, `<content>`, `<file>`,
  `<classname>`, `<url>`, `<freecadmin>`, worked examples)
* `.../Source/Topics/Structuring/index.md` (modern vs legacy layout)
* `.../Source/Topics/Licensing/index.md`
* `.../Source/Demos/Macro/index.md` (what a macro addon is)
* `gh api repos/FreeCAD/Addons` — "Addon index for FreeCAD >= 1.0.0", branch `main`
* `gh api repos/FreeCAD/Addons/contents/Data/Python/3.14/Allowed-Packages` — 114
  entries, `numpy` and `pillow` present
* `gh api repos/FreeCAD/Addon-Template` — "Minimal FreeCAD Addon Template"
