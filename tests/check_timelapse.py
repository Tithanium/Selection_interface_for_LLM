# -*- coding: utf-8 -*-
"""check_timelapse.py -- independent verification of one timelapse output folder.

    python check_timelapse.py <outdir> [strict=1]

Runs OUTSIDE FreeCAD (plain Pillow + numpy): it re-derives every number from the
PNG files instead of trusting manifest.json, then reports whether the frame set
matches the recorded computation order and whether the GIF really contains those
frames (frame count / size / per-frame agreement -- no visual judgement of the
animation itself).

Exit code 0 = PASS, 1 = FAIL, 2 = usage.
"""

import json
import os
import sys

import numpy as np
from PIL import Image

TOL_BLANK = 0.0005          # a frame with <0.05% non-white pixels is suspicious
TOL_CHANGE = 0.0015         # manifest vs recomputed step change
TOL_FLAT = 0.0005           # below this the picture did not change
TOL_GIF = 0.06              # mean |gif frame - png frame| / 255


def load_gray(path):
    with Image.open(path) as im:
        return np.asarray(im.convert("RGB"), dtype=np.int16)


def load_scene(path, raw_height=None):
    """The 3D area of a frame: the overlay bar at the bottom is cut away."""
    arr = load_gray(path)
    if raw_height and 0 < raw_height <= arr.shape[0]:
        return arr[:raw_height, :, :]
    keep = int(round(arr.shape[0] * 0.9))
    return arr[:keep, :, :]


def main(argv):
    if len(argv) < 2:
        print("usage: python check_timelapse.py <outdir> [strict=1]")
        return 2
    out = os.path.abspath(argv[1])
    strict = len(argv) > 2 and argv[2].endswith("=1")
    failures, notes = [], []
    man_path = os.path.join(out, "manifest.json")
    if not os.path.isfile(man_path):
        print("FAIL: no manifest.json in %s" % out)
        return 1
    with open(man_path, encoding="utf-8") as fh:
        man = json.load(fh)
    order = man.get("order") or []
    frames = man.get("frame_list") or []
    print("output folder : %s" % out)
    print("document      : %s" % man.get("doc"))
    print("steps         : %d" % len(order))
    print("frames listed : %d" % len(frames))
    print("")

    if not order:
        failures.append("manifest lists no step")
    if len(frames) != len(order):
        failures.append("manifest lists %d frames for %d steps"
                        % (len(frames), len(order)))
    if [f["index"] for f in frames] != list(range(1, len(frames) + 1)):
        failures.append("frame indices are not 1..N in order")

    # 1. one frame per step, present, ordered, non blank, same size
    previous, previous_volumes, sizes = None, None, set()
    print("%-3s %-18s %-10s %-9s %-12s %s"
          % ("#", "label", "nonwhite", "change", "volume", "file"))
    for frame in frames:
        path = os.path.join(out, "frames", frame["file"])
        if not os.path.isfile(path):
            failures.append("missing frame file %s" % frame["file"])
            continue
        arr = load_scene(path, (frame.get("pixels") or {}).get("h"))
        h, w = arr.shape[:2]
        sizes.add((w, h))
        nonwhite = int((arr.min(axis=2) < 245).sum())
        if nonwhite < TOL_BLANK * w * h:
            failures.append("frame %s is blank (%d non-white px)"
                            % (frame["file"], nonwhite))
        if frame["index"] <= len(order):
            expected = order[frame["index"] - 1]["label"]
            if frame["label"] != expected:
                failures.append("frame %d label %r != step label %r"
                                % (frame["index"], frame["label"], expected))
        volumes = frame.get("volumes") or {}
        volume = sum(volumes.values()) if volumes else None
        change = None
        if previous is not None:
            if previous.shape != arr.shape:
                failures.append("frame %d has a different size than its predecessor"
                                % frame["index"])
            else:
                change = round(float(np.abs(arr - previous).mean()) / 255.0, 5)
                recorded = frame.get("change_vs_previous")
                if recorded is not None and abs(change - recorded) > TOL_CHANGE:
                    notes.append("frame %d: manifest change %.5f, recomputed %.5f"
                                 % (frame["index"], recorded, change))
            if frame.get("changed") is False:
                failures.append("frame %d changed neither the pixels nor the volume: "
                                "set_tip did nothing" % frame["index"])
            if (change is not None and change < TOL_FLAT
                    and previous_volumes is not None and volumes != previous_volumes):
                notes.append("frame %d looks identical but the volume changed: "
                             "the step is interior from this angle" % frame["index"])
        previous, previous_volumes = arr, volumes
        print("%-3d %-18s %-10d %-9s %-12s %s"
              % (frame["index"], frame["label"], nonwhite,
                 "-" if change is None else "%.5f" % change,
                 "-" if volume is None else "%.1f" % volume,
                 frame["file"]))
    if len(sizes) > 1:
        failures.append("frames do not all share one size: %s" % sorted(sizes))
    print("")

    # 2. the animation file really holds those frames
    gif = man.get("gif")
    if gif and os.path.isfile(gif):
        with Image.open(gif) as anim:
            n = getattr(anim, "n_frames", 1)
            gsize = anim.size
            print("gif           : %s" % os.path.basename(gif))
            print("gif frames    : %d (steps: %d)  size %s  bytes %d"
                  % (n, len(frames), gsize, os.path.getsize(gif)))
            if n != len(frames):
                failures.append("gif holds %d frames, %d steps" % (n, len(frames)))
            worst = 0.0
            for i in range(min(n, len(frames))):
                anim.seek(i)
                g = np.asarray(anim.convert("RGB"), dtype=np.int16)
                p = load_gray(os.path.join(out, "frames", frames[i]["file"]))
                diff = float(np.abs(g - p).mean()) / 255.0
                worst = max(worst, diff)
            print("gif vs frames : worst mean difference %.4f (limit %.3f)"
                  % (worst, TOL_GIF))
            if worst > TOL_GIF:
                failures.append("a gif frame does not match its PNG (%.4f)" % worst)
    elif gif:
        failures.append("gif missing: %s" % gif)
    print("")

    recorded_flat = set(man.get("flat_frames") or [])
    print("flat frames reported by the macro: %s"
          % (sorted(recorded_flat) if recorded_flat else "none"))
    for note in notes:
        print("note: %s" % note)
    for failure in failures:
        print("FAILURE: %s" % failure)
    ok = not failures
    if strict and not ok:
        ok = False
    print("")
    print("RESULT: %s (%d frames, %d steps%s)"
          % ("PASS" if ok else "FAIL", len(frames), len(order),
             "" if not recorded_flat else ", %d flat frame(s)" % len(recorded_flat)))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
