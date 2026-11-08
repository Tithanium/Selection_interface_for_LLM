# Task — progressive-build timelapse macro for FreeCAD

**Deliverable:** a FreeCAD macro (`Timelapse_Features`) installed in the user macro
folder that (a) recovers the exact computation order of a PartDesign document,
(b) lets the user walk that order step by step with `set_tip` + visibility so the
part is rebuilt progressively on screen, and (c) writes a GIF of that walk
(one PNG per step) into a fresh folder under `Downloads`.

**Check (the bar):** run the macro on a real document — the panel lists every
building step in computation order, stepping moves the body tip, and
`python check_timelapse.py <outdir>` prints `RESULT: PASS` after re-deriving the
frame count / per-frame change / GIF agreement from the PNG files, plus one
screenshot per required visible behaviour.

Restated in one line: **Deliverable:** the macro does the walk and the GIF.
**Check:** `check_timelapse.py` on a produced folder exits 0 with one frame per
tree step, and the frames themselves show the part growing.

## Pieces and their one-line checks

| # | piece | check |
|---|-------|-------|
| 1 | computation order (`timelapse_lib.timeline`) | `freecadcmd report_order.py <file>` prints `RESULT: PASS`; order equals the `Tip -> BaseFeature` chain of each body |
| 2 | step display (`apply_level`) | setting level k sets `Body.Tip` to the k-th step and the shown shape volume matches that feature's own `Shape.Volume` |
| 3 | panel (`open_panel`) | dock titled "Timelapse - building steps" appears, lists N rows, `< step` / `step >` / list click / reset / final all move the level; closing restores the original tips |
| 4 | GIF (`build_timelapse`) | `check_timelapse.py <outdir>` → `RESULT: PASS`, N frames, N = number of tree steps |
| 4b | `open GIF` button | one click shows the GIF playing in a FreeCAD window (`QMovie` frame count = N) and opens the run folder in Explorer with the file selected |
| 4c | LLM bridge (note box + `copy to clipboard description for LLM`) | copy the request for step 3 with `set holes diameter to 5mm`, paste it into a fresh `pi` session: the prompt names the folder, the file, the ban on modifying it and the new file name, the feature type and its sketch; the session delivers `<stem>_modified.FCStd` with the right dimension changed while the source SHA256 is unchanged |
| 4d | display of every listed entity (display list + `show also` boxes + `apply_level`) | on `02_piston_cardanV3` and `02_seringue_cardanV3`, walk all 66 / 68 levels: each datum is visible exactly at its level, exactly the last built feature of each body is drawn, the selected feature's sketch is shown highlighted while no other sketch is, and the `display` list switches the render (measured: `edges only` 40395 non-white px vs `solid + edges` 57179 at the final level). The three boxes are measured the same way: `datum objects` off 16 → 0 datum planes and 160141 → 143342 non-white px at level 50, `profile sketch` off 1 → 0 sketch (52863 pixels and the mean brightness change), `other bodies` off 6 → 1 body and 160141 → 88943 px |
| 4e | computation order of a piece made by several features | no step may consume a body that is still being built: on `02_seringue_cardanV3` the 4 mirrors/fusions land at steps 37/57/58/59 instead of 4/10/19/28, step count unchanged (68 and 66), 0 ordering warnings, GIF of both files re-made and `check_timelapse.py` PASS |
| 5 | accessibility | `Macro > Macros...` lists `Timelapse_Features.FCMacro` and it runs from there |
| 6 | evidence | every frame that goes into the GIF is inspected as an image; the GIF itself is never used as evidence, only its frame count is machine-checked |

## Ground rules kept

- the macro never saves the user's document; tips/visibility are snapshotted on
  open and restored on close, on "restore original", and at the end of a GIF run;
- the camera is fitted once on the **final** part and the user's angle is
  re-applied, then frozen for the whole sweep, so the part grows into a stable
  frame;
- a blank capture aborts the run (never ship a blank GIF);
- steps whose geometry is invisible from the current angle are reported
  (`flat_frames`), not silently dropped — they still appear as frames.
