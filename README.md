# Timelapse_Features — progressive-build timelapse for FreeCAD 1.1

Watch a finished PartDesign part being built again, one feature at a time, and
export that walk as a GIF.

```
%APPDATA%\FreeCAD\v1-1\Macro\            ( = FreeCAD.getUserMacroDir(True) )
├── Timelapse_Features.FCMacro           <- the file Macro > Macros... runs
└── Timelapse_Features\                  <- this folder (library, not listed as a macro)
    ├── timelapse_lib.py                 logic + panel
    ├── report_order.py                  headless order check  (freecadcmd)
    ├── check_timelapse.py               output-folder verifier (plain python)
    ├── task.md                          what the tool must do, and how it is checked
    └── README.md
```

## Use

1. Open the part, `Macro > Macros... > Timelapse_Features.FCMacro > Execute`.
2. A dock named **Timelapse - building steps** appears on the right. It lists the
   recovered computation order: `#`, feature label, `type <- what it consumes`.
3. `step >` / `< step`, the spin box, or clicking a row moves the development
   level: the body `Tip` is moved to that feature and the 3D view shows the part
   as it was at that moment. `reset` = nothing built, `final` = the finished part.
4. **create GIF (all steps)** frames the final part from the current viewing
   angle, sweeps every step, writes
   `Downloads\FreeCAD_timelapse\<document>_<stamp>\` with
   `frames\NNN_<label>.png`, `timelapse_<doc>.gif`, `manifest.json`, `steps.txt`.
5. **open GIF** opens the run folder that holds it (file selected in Explorer)
   and plays the GIF right away in a small window inside FreeCAD
   (`7 frames | 1000x1006 px | 106 kB` + the full path), with `open folder` and
   `open with Windows viewer` buttons there as well. With no run in this session
   it picks the newest GIF under `Downloads\FreeCAD_timelapse\`, preferring one
   made from the active document.
6. `restore original` (or closing the panel) puts back the tips and visibility the
   document had before the macro touched it. The document is **never saved**.

## How the order is recovered

1. every object that produces a shape (sketches, datums, origins, bodies and
   containers are excluded) is topologically sorted on its real links
   (`OutList` within that set), ties broken by document order;
2. each `PartDesign::Body`'s `Tip -> BaseFeature -> ...` chain — the actual
   computation order of PartDesign — is walked and compared with the sorted
   result; a mismatch is reported in the panel/Report view and the tip chain wins.

Verified on `guide_percage26.FCStd` (7 steps, two `PartDesign::Mirrored` features)
and `toscin_5_26.FCStd` (9 steps, one `PartDesign::PolarPattern`); both agree.

## Checks that ship with it

```powershell
$fc = "$env:LOCALAPPDATA\Programs\FreeCAD 1.1\bin\freecadcmd.exe"
# 1. headless: does the recovered order match the tip chain? (read-only, exit 0/1)
& $fc report_order.py "C:\path\part.FCStd"

# 2. after a GIF run: re-derives every number from the PNGs (plain python + Pillow)
python check_timelapse.py "C:\Users\<you>\Downloads\FreeCAD_timelapse\<doc>_<stamp>"
```

`check_timelapse.py` exits 0 only when: one frame per recorded step in order, the
frame labels match the step labels, no frame is blank, all frames share one size,
the manifest's per-step change is reproduced from the images, and — for
integrity only — the GIF holds the same number of frames and each GIF frame
agrees with its PNG (mean difference < 6 %). It never judges the animation
visually: the frames are the evidence.

## Notes and traps handled

- `saveImage()` is verified with Pillow before a frame is accepted; a blank frame
  aborts the run instead of producing a blank GIF. A main-window grab cropped to
  the 3D subwindow is the fallback.
- The dock is hidden while the frames are captured, the viewport is allowed to
  settle, then the camera is fitted on the complete part and the user's viewing
  angle is re-applied (`fitAll` replaces the camera node and resets the
  orientation) and frozen — `AnimationDuration` is set to 0 for the run.
- A step whose change is invisible from the current angle is still exported as a
  frame and reported in `manifest.json` → `flat_frames`; that is a property of the
  model/angle, not a missing frame.
- PIL and numpy are used from FreeCAD's own bundled Python (Pillow 12 present),
  so the GIF needs no external tool.
