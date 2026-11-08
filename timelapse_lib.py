# -*- coding: utf-8 -*-
"""timelapse_lib.py -- progressive-build timelapse for FreeCAD 1.1.x.

Purpose
-------
Walk a finished PartDesign document *backwards and forwards in time*: the
library recovers the exact computation order of the tree (tip of computation
moving from the first feature to the final one), can display the part as it was
after step k, and can render a GIF of that progression.

Two entry points, both used by the panel:
  * apply_level(doc, tl, k)  -- put the document in its state after step k
  * build_timelapse(doc)     -- frame the final part, sweep every step,
                               capture one PNG per step, assemble a GIF

Design rules that this file obeys (each one is a trap measured on 1.1.4):
  * no save() of the user's document, ever; the pre-run state is snapshotted and
    restored at the end of a run;
  * ordering comes from a topological sort of the real dependencies, then each
    body's Tip -> BaseFeature chain is walked and compared: a mismatch is
    reported, not silently accepted;
  * the camera is fitted ONCE on the final part, the user's viewing angle is
    re-applied afterwards and frozen for the whole sweep: only the zoom and the
    centering of the image may move (measured on 1.1.4: 0.000000 deg of angle
    change on every frame, even with a rotation injected right after fitAll);
  * Coin values returned by field.getValue() are LIVE proxies, not copies, so the
    camera snapshot stores plain tuples -- otherwise "restore" silently no-ops;
  * saveImage() is verified with PIL (blank images have been observed on this
    box), and a blank capture aborts the run instead of writing a blank GIF;
  * every change is followed by a GUI pump before anything is read back.

ASCII only on purpose: the pi `edit` tool re-encodes non-ASCII source files.
"""

import json
import math
import os
import sys
import time
import traceback

import FreeCAD

try:  # headless freecadcmd imports FreeCADGui as an inert stub
    import FreeCADGui
    from PySide import QtCore, QtGui, QtWidgets
    GUI = hasattr(FreeCADGui, "getMainWindow")
except Exception:  # pragma: no cover - headless
    FreeCADGui = None
    GUI = False

VERSION = "1.2.0"
LIB_NAME = "Timelapse_Features"
DOCK_NAME = "Timelapse_Features_Dock"
PANEL_NAME = "Timelapse_Features_Panel"
GIF_PREVIEW_NAME = "Timelapse_GifPreview"

# object types that are never a "building step" of the shape
SKIP_TYPES = {
    "PartDesign::Body",
    "PartDesign::Plane",
    "PartDesign::Line",
    "PartDesign::Point",
    "PartDesign::CoordinateSystem",
    "App::Origin",
    "App::Line",
    "App::Plane",
    "App::Point",
    "App::Part",
    "App::DocumentObjectGroup",
    "App::FeaturePython",
    "App::Link",
    "Part::Datum",
}
SKIP_PREFIXES = ("Sketcher::", "TechDraw::", "Spreadsheet::", "Fem::", "Mesh::")


# --------------------------------------------------------------------------
# small helpers
# --------------------------------------------------------------------------
def log(msg):
    FreeCAD.Console.PrintMessage("[timelapse] %s\n" % msg)


def warn(msg):
    FreeCAD.Console.PrintWarning("[timelapse] %s\n" % msg)


def short_type(type_id):
    for pref in ("PartDesign::", "Part::", "App::", "Sketcher::"):
        if type_id.startswith(pref):
            return type_id[len(pref):]
    return type_id


def _deref(value):
    """Turn the many shapes a FreeCAD link can take into one object or None."""
    if value is None:
        return None
    if isinstance(value, (list, tuple)):
        for item in value:
            got = _deref(item)
            if got is not None:
                return got
        return None
    if hasattr(value, "Name") and hasattr(value, "TypeId"):
        return value
    return None


def _link_label(owner, attr):
    try:
        target = _deref(getattr(owner, attr, None))
    except Exception:
        return None
    return target.Label if target is not None else None


def active_document():
    """Resolve the document to work on, explicitly, never by guessing."""
    doc = FreeCAD.ActiveDocument
    if doc is None and GUI:
        gdoc = FreeCADGui.activeDocument()
        if gdoc is not None:
            doc = gdoc.Document
    if doc is None:
        raise RuntimeError("No active document: open a part first.")
    return doc


def body_objects(doc):
    return [o for o in doc.Objects if o.TypeId == "PartDesign::Body"]


def tip_chain(body):
    """The authoritative computation order of one body: tip -> BaseFeature -> ..."""
    chain, guard, cur = [], 0, _deref(getattr(body, "Tip", None))
    while cur is not None and guard < 500:
        if cur in chain:
            warn("cycle in the BaseFeature chain of %s at %s" % (body.Name, cur.Name))
            break
        chain.append(cur)
        guard += 1
        cur = _deref(getattr(cur, "BaseFeature", None))
    chain.reverse()
    return chain


def is_build_object(obj):
    if obj.TypeId in SKIP_TYPES:
        return False
    if obj.TypeId.startswith(SKIP_PREFIXES):
        return False
    shape = getattr(obj, "Shape", None)
    if shape is None:
        return False
    try:
        if shape.isNull():
            return False
        return len(shape.Faces) > 0 or len(shape.Solids) > 0
    except Exception:
        return False


# --------------------------------------------------------------------------
# the timeline: exact computation order
# --------------------------------------------------------------------------
def timeline(doc):
    """Return {'steps': [...], 'warnings': [...], 'bodies': {...}}.

    Each step is a dict: index (1-based), name, label, type, short, body,
    profile (driving sketch when there is one), detail.
    """
    warnings = []
    index_of = {o.Name: i for i, o in enumerate(doc.Objects)}
    build = [o for o in doc.Objects if is_build_object(o)]
    names = {o.Name for o in build}

    # dependencies restricted to build objects, straight from the real links
    deps = {}
    for o in build:
        deps[o.Name] = [d for d in o.OutList if d.Name in names and d.Name != o.Name]

    # Kahn's algorithm; ties broken by document (creation) order
    ordered, done, remaining = [], set(), list(build)
    while remaining:
        ready = [o for o in remaining if all(d.Name in done for d in deps[o.Name])]
        if not ready:
            warnings.append("dependency cycle among %s -- falling back to document order"
                            % ", ".join(sorted(o.Name for o in remaining)))
            ready = [sorted(remaining, key=lambda o: index_of[o.Name])[0]]
        ready.sort(key=lambda o: index_of[o.Name])
        for o in ready:
            ordered.append(o)
            done.add(o.Name)
            remaining.remove(o)

    # verify against the PartDesign tip chain, which is the real computation order
    bodies = {}
    for body in body_objects(doc):
        chain = tip_chain(body)
        pos = [i for i, o in enumerate(ordered) if o in chain]
        seen = [ordered[i] for i in pos]
        if seen != chain:
            warnings.append(
                "%s: dependency order %s != tip chain %s -- tip chain wins"
                % (body.Name, [o.Name for o in seen], [o.Name for o in chain]))
            for slot, obj in zip(sorted(pos), chain):
                ordered[slot] = obj
        bodies[body.Name] = [o.Name for o in chain]

    steps = []
    for i, obj in enumerate(ordered, start=1):
        owner = None
        for body in body_objects(doc):
            if obj in list(body.Group):
                owner = body.Name
                break
        profile = _step_source(obj)
        steps.append({
            "index": i,
            "name": obj.Name,
            "label": obj.Label,
            "type": obj.TypeId,
            "short": short_type(obj.TypeId),
            "body": owner,
            "profile": profile,
            "detail": _detail_string(obj),
            "_obj": obj,
        })
    if not steps:
        warnings.append("no build object found (no PartDesign feature outside a sketch)")
    return {"doc": doc.Name, "steps": steps, "warnings": warnings, "bodies": bodies}


def _step_source(obj):
    """What the step consumes: a sketch, a set of originals, or a base feature."""
    sketch = _link_label(obj, "Profile") or _link_label(obj, "Sketch")
    if sketch:
        return sketch
    originals = getattr(obj, "Originals", None)
    if originals is not None and not isinstance(originals, bool):
        try:
            names = [o.Label for o in originals if hasattr(o, "Label")]
            if names:
                return "of " + ", ".join(names)
        except Exception:
            pass
    for attr in ("Base", "BaseFeature"):
        got = _link_label(obj, attr)
        if got:
            return "base: " + got
    return None


def _detail_string(obj):
    """One human line describing what the step does."""
    bits = []
    for attr in ("Length", "Type", "Occurrences", "Angle", "Offset", "Size",
                 "Radius", "Diameter", "ThroughAll"):
        if hasattr(obj, attr) and attr not in ("Type",):
            try:
                value = getattr(obj, attr)
            except Exception:
                continue
            if isinstance(value, bool):
                if value:
                    bits.append("%s" % attr)
                continue
            text = str(value)
            if text.strip():
                bits.append("%s=%s" % (attr, text))
    if obj.TypeId in ("PartDesign::Pad", "PartDesign::Pocket") and hasattr(obj, "Type"):
        try:
            bits.insert(0, "Type=%s" % obj.Type)
        except Exception:
            pass
    return "  ".join(bits)


# --------------------------------------------------------------------------
# state: display the document at level k
# --------------------------------------------------------------------------
def snapshot_state(doc):
    """Remember tips and visibility so the macro can leave no trace."""
    snap = {"tips": {}, "visible": {}, "display_mode_body": {}}
    for body in body_objects(doc):
        tip = _deref(getattr(body, "Tip", None))
        snap["tips"][body.Name] = tip.Name if tip is not None else None
    for obj in doc.Objects:
        vo = getattr(obj, "ViewObject", None)
        if vo is None:
            continue
        try:
            snap["visible"][obj.Name] = bool(vo.Visibility)
        except Exception:
            pass
        if hasattr(vo, "DisplayModeBody"):
            try:
                snap["display_mode_body"][obj.Name] = vo.DisplayModeBody
            except Exception:
                pass
    return snap


def restore_state(doc, snap):
    """Undo everything apply_level() changed (never touches geometry)."""
    problems = []
    for name, tip_name in snap.get("tips", {}).items():
        body = doc.getObject(name)
        if body is None:
            continue
        tip = doc.getObject(tip_name) if tip_name else None
        if tip is not None:
            try:
                body.Tip = tip
            except Exception as exc:
                problems.append("%s.Tip: %s" % (name, exc))
    for name, visible in snap.get("visible", {}).items():
        obj = doc.getObject(name)
        vo = getattr(obj, "ViewObject", None) if obj is not None else None
        if vo is not None:
            try:
                vo.Visibility = visible
            except Exception:
                pass
    for name, mode in snap.get("display_mode_body", {}).items():
        obj = doc.getObject(name)
        vo = getattr(obj, "ViewObject", None) if obj is not None else None
        if vo is not None and hasattr(vo, "DisplayModeBody"):
            try:
                vo.DisplayModeBody = mode
            except Exception:
                pass
    doc.recompute()
    if problems:
        warn("restore problems: " + "; ".join(problems))
    return problems


def current_volumes(doc):
    """Volume of the tip shape of every body: proof that a step did something
    even when the change is hidden from the current viewing angle."""
    out = {}
    for body in body_objects(doc):
        tip = _deref(getattr(body, "Tip", None))
        if tip is None:
            continue
        shape = getattr(tip, "Shape", None)
        if shape is None:
            continue
        try:
            if shape.isNull():
                continue
            out[body.Name] = round(float(shape.Volume), 6)
        except Exception:
            continue
    return out


def apply_level(doc, tl, level, recompute=True):
    """Show the part as it was after `level` building steps (0 = nothing yet)."""
    steps = tl["steps"]
    total = len(steps)
    level = max(0, min(int(level), total))
    per_body = {}
    for step in steps:
        if step["body"]:
            per_body.setdefault(step["body"], []).append((step["index"], step["_obj"]))

    for body in body_objects(doc):
        vo = getattr(body, "ViewObject", None)
        built = [obj for (idx, obj) in per_body.get(body.Name, []) if idx <= level]
        if built:
            try:
                body.Tip = built[-1]
            except Exception as exc:
                warn("cannot set tip of %s to %s: %s" % (body.Name, built[-1].Name, exc))
                continue
            if vo is not None:
                if hasattr(vo, "DisplayModeBody"):
                    try:
                        vo.DisplayModeBody = "Tip"
                    except Exception:
                        pass
                vo.Visibility = True
        elif vo is not None:
            vo.Visibility = False

    for step in steps:
        if step["body"]:
            continue
        vo = getattr(step["_obj"], "ViewObject", None)
        if vo is not None:
            try:
                vo.Visibility = step["index"] <= level
            except Exception:
                pass

    if recompute:
        doc.recompute()
    return level


# --------------------------------------------------------------------------
# GUI pump, camera, capture
# --------------------------------------------------------------------------
def pump(times=2):
    """Nothing in the GUI is synchronous with a script: force the redraw."""
    if not GUI:
        return
    for _ in range(max(1, times)):
        try:
            QtWidgets.QApplication.processEvents()
        except Exception:
            pass
        try:
            FreeCADGui.updateGui()
        except Exception:
            pass


def settle_view(view, tries=15):
    """Wait for the 3D viewport to stop resizing (hiding a dock resizes it)."""
    if not GUI:
        return None
    last = None
    for _ in range(tries):
        pump(1)
        try:
            size = tuple(int(v) for v in view.getSize())
        except Exception:
            return last
        if size == last:
            return size
        last = size
        time.sleep(0.02)
    return last


def active_view():
    if not GUI:
        raise RuntimeError("no GUI: capture and framing need the FreeCAD GUI")
    gdoc = FreeCADGui.activeDocument()
    if gdoc is None:
        FreeCADGui.ActiveDocument = FreeCADGui.getDocument(active_document().Name)
        gdoc = FreeCADGui.activeDocument()
    if gdoc is None:
        raise RuntimeError("no active 3D view: front the document window first")
    view = gdoc.activeView()
    if view is None:
        raise RuntimeError("no active 3D view: front the document window first")
    return view


def front_document(doc):
    """The tab in front decides what a capture shows."""
    if not GUI:
        return
    mw = FreeCADGui.getMainWindow()
    stem = (doc.FileName or "").replace("\\", "/").rsplit("/", 1)[-1].rsplit(".", 1)[0]
    for sub in mw.findChildren(QtWidgets.QMdiSubWindow):
        if (sub.windowTitle() or "").strip() == "Start":
            sub.close()
    for sub in mw.findChildren(QtWidgets.QMdiSubWindow):
        title = sub.windowTitle() or ""
        if doc.Name in title or (stem and stem[:12] in title):
            mw.setActiveSubWindow(sub)
            sub.widget().setFocus()
    mw.activateWindow()
    mw.raise_()
    pump()


def camera_snapshot(view):
    """Freeze the camera.

    SbVec3f / SbRotation returned by field.getValue() are LIVE proxies of the
    Coin field, not copies: storing them would make the "snapshot" follow every
    later camera move (measured on 1.1.4). Store plain tuples instead.
    """
    cam = view.getCameraNode()
    pos = cam.position.getValue()
    rot = cam.orientation.getValue().getValue()
    return {
        "node": cam,
        "position": (pos[0], pos[1], pos[2]),
        "orientation": (rot[0], rot[1], rot[2], rot[3]),
        "height": cam.height.getValue() if hasattr(cam, "height") else None,
        "near": cam.nearDistance.getValue(),
        "far": cam.farDistance.getValue(),
        "direction": FreeCAD.Vector(view.getViewDirection()),
    }


def rotation_value(value):
    """Coin SbRotation from a stored 4-tuple (an SbRotation passes through)."""
    if isinstance(value, (tuple, list)):
        from pivy import coin
        return coin.SbRotation(float(value[0]), float(value[1]),
                               float(value[2]), float(value[3]))
    return value


def camera_restore(view, snap):
    """Put back angle, zoom, centering and clipping planes of a snapshot."""
    from pivy import coin
    cam = view.getCameraNode()
    p = snap["position"]
    cam.position.setValue(coin.SbVec3f(float(p[0]), float(p[1]), float(p[2])))
    cam.orientation.setValue(rotation_value(snap["orientation"]))
    if snap["height"] is not None and hasattr(cam, "height"):
        cam.height.setValue(snap["height"])
    cam.nearDistance.setValue(snap["near"])
    cam.farDistance.setValue(snap["far"])
    pump()


def animation_duration(value=None):
    """FreeCAD keeps animating a camera after it was framed; 0 during a sweep."""
    param = FreeCAD.ParamGet("User parameter:BaseApp/Preferences/View")
    old = param.GetInt("AnimationDuration", 500)
    if value is not None:
        param.SetInt("AnimationDuration", value)
    return old


def frame_on_final_part(doc, tl, view, outer_attempts=6):
    """Fit the view on the COMPLETE part, then re-apply the user's angle."""
    settle_view(view)
    saved = camera_snapshot(view)
    apply_level(doc, tl, len(tl["steps"]))
    pump()
    view.fitAll()
    pump(3)
    want = saved["direction"]
    for attempt in range(outer_attempts):
        cam = view.getCameraNode()
        cam.orientation.setValue(rotation_value(saved["orientation"]))
        pump()
        got = FreeCAD.Vector(view.getViewDirection())
        if got.dot(want) > 0.999:
            break
        view.fitAll()
        pump(3)
    else:
        warn("camera orientation did not settle on the user's angle")
    log("framed final part, direction %s (dot %.5f)"
        % (tuple(round(c, 3) for c in got), got.dot(want)))
    return saved, view.getCameraNode()


def image_size(view, max_px=1000):
    """Keep the viewport aspect so the render is not stretched."""
    try:
        w, h = view.getSize()
    except Exception:
        w, h = 4, 3
    w, h = int(w or 0), int(h or 0)
    if w < 50 or h < 50:
        w, h = 4, 3
    scale = float(max_px) / float(max(w, h))
    W = max(320, int(round(w * scale)) // 2 * 2)
    H = max(240, int(round(h * scale)) // 2 * 2)
    return W, H


def frame_stats(path):
    """Blank-frame detector + a shape metric, computed with PIL/numpy."""
    from PIL import Image
    import numpy as np
    with Image.open(path) as im:
        rgb = im.convert("RGB")
        arr = np.asarray(rgb, dtype=np.uint8)
        w, h = rgb.size
    low = int(arr.min(axis=2).max()) if arr.size else 0
    spread = int(arr.max()) - int(arr.min())
    dark = int((arr.min(axis=2) < 245).sum())
    return {"w": w, "h": h, "nonwhite": dark, "spread": spread,
            "blank": spread < 8 or dark < 0.0005 * w * h}


def gray_array(path):
    """Luminance array of a frame, for the step-to-step change metric."""
    from PIL import Image
    import numpy as np
    with Image.open(path) as im:
        return np.asarray(im.convert("L"), dtype=np.int16)


def capture_view(view, path, width, height, background="White"):
    """saveImage() then verify the pixels; a blank frame aborts the run."""
    if os.path.exists(path):
        os.remove(path)
    view.saveImage(path, width, height, background)
    if not os.path.exists(path):
        raise RuntimeError("saveImage() wrote no file: %s" % path)
    stats = frame_stats(path)
    if stats["blank"]:
        stats = _capture_fallback(path, width, height) or stats
    if stats["blank"]:
        raise RuntimeError(
            "capture came out blank (%s, %dx%d) -- refusing to build a GIF from it"
            % (path, width, height))
    return stats


def _capture_fallback(path, width, height):
    """Last resort: grab the MDI subwindow and crop it to the 3D view."""
    if not GUI:
        return None
    try:
        mw = FreeCADGui.getMainWindow()
        sub = mw.activeSubWindow()
        if sub is None:
            return None
        pix = mw.grab()
        rect = QtCore.QRect(sub.mapTo(mw, QtCore.QPoint(0, 0)), sub.size())
        crop = pix.copy(rect).scaled(width, height,
                                     QtCore.Qt.KeepAspectRatio,
                                     QtCore.Qt.SmoothTransformation)
        crop.save(path)
        log("saveImage was blank, used main-window grab crop instead")
        return frame_stats(path)
    except Exception as exc:
        warn("capture fallback failed: %s" % exc)
        return None


def overlay_frame(path, headline, subline, progress=None):
    """Burn the step number into the frame so each step is self-describing."""
    from PIL import Image, ImageDraw, ImageFont

    with Image.open(path) as im:
        base = im.convert("RGB")
    W, H = base.size
    bar = max(46, int(H * 0.085))
    canvas = Image.new("RGB", (W, H + bar), (250, 250, 250))
    canvas.paste(base, (0, 0))
    draw = ImageDraw.Draw(canvas)

    def font(px):
        try:
            return ImageFont.load_default(size=px)
        except Exception:
            return ImageFont.load_default()

    big = font(max(18, int(bar * 0.62)))
    small = font(max(13, int(bar * 0.40)))
    pad = max(8, int(W * 0.012))
    y_big = H + max(3, int(bar * 0.10))
    draw.text((pad, y_big), headline, fill=(25, 25, 25), font=big)
    width_big = draw.textlength(headline, font=big)
    draw.text((pad + width_big + pad, y_big + max(3, int(bar * 0.14))),
              subline, fill=(90, 90, 90), font=small)
    if progress is not None:
        y = H + bar - max(5, int(bar * 0.12))
        draw.rectangle([0, y, W - 1, H + bar - 1], fill=(226, 226, 226))
        done = int(max(0.0, min(1.0, progress)) * (W - 1))
        draw.rectangle([0, y, done, H + bar - 1], fill=(40, 120, 200))
    canvas.save(path)


# --------------------------------------------------------------------------
# output folder / GIF
# --------------------------------------------------------------------------
def downloads_dir():
    """Resolve the real Downloads folder (it can be relocated)."""
    try:
        import winreg
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Explorer\Shell Folders")
        path, _ = winreg.QueryValueEx(
            key, "{374DE290-123F-4565-9164-39C4925E467B}")
        if path and os.path.isdir(path):
            return path
    except Exception:
        pass
    guess = os.path.join(os.path.expanduser("~"), "Downloads")
    return guess if os.path.isdir(guess) else os.path.expanduser("~")


def timelapse_root():
    """Folder that holds every run folder."""
    return os.path.join(downloads_dir(), "FreeCAD_timelapse")


def latest_gif(doc=None):
    """Newest GIF under the output root, preferring one made from *doc*."""
    root = timelapse_root()
    if not os.path.isdir(root):
        return None
    wanted = ""
    if doc is not None:
        wanted = _file_safe(doc.Label or doc.Name).lower()
    best = None
    for folder in sorted(os.listdir(root)):
        sub = os.path.join(root, folder)
        if not os.path.isdir(sub):
            continue
        for name in sorted(os.listdir(sub)):
            if not name.lower().endswith(".gif"):
                continue
            path = os.path.join(sub, name)
            try:
                mtime = os.path.getmtime(path)
            except OSError:
                continue
            same_doc = 1 if (wanted and folder.lower().startswith(wanted)) else 0
            key = (same_doc, mtime)
            if best is None or key > best[0]:
                best = (key, path)
    return best[1] if best else None


def reveal_in_explorer(path):
    """Open the folder that holds *path*, with the file selected."""
    path = os.path.normpath(path)
    folder = os.path.dirname(path)
    try:
        import subprocess
        subprocess.Popen(["explorer", "/select," + path])
        return True
    except Exception as exc:
        warn("explorer /select failed (%s), opening the folder instead" % exc)
    try:
        os.startfile(folder)
        return True
    except Exception as exc:
        warn("cannot open %s: %s" % (folder, exc))
        return False


def open_with_system(path):
    """Hand the file to its default Windows application (photo/GIF viewer)."""
    try:
        os.startfile(os.path.normpath(path))
        return True
    except Exception as exc:
        warn("cannot open %s: %s" % (path, exc))
        return False


def make_output_dir(doc, root=None):
    root = root or timelapse_root()
    stamp = time.strftime("%Y%m%d-%H%M%S")
    safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in
                   (doc.Label or doc.Name))
    out = os.path.join(root, "%s_%s" % (safe, stamp))
    frames = os.path.join(out, "frames")
    os.makedirs(frames, exist_ok=True)
    return out, frames


def make_gif(frame_paths, gif_path, duration_ms=700):
    """One shared palette for the whole animation: no per-frame colour drift."""
    from PIL import Image

    frames = []
    for path in frame_paths:
        with Image.open(path) as im:
            frames.append(im.convert("RGB"))
    if not frames:
        raise RuntimeError("no frame to assemble")
    w, h = frames[0].size
    if any(f.size != frames[0].size for f in frames):
        raise RuntimeError("frames do not share one size: %s"
                           % {(f.size) for f in frames})

    tw = 120
    th = max(1, int(round(tw * float(h) / float(w))))
    cols = min(5, len(frames))
    rows = int(math.ceil(len(frames) / float(cols)))
    sheet = Image.new("RGB", (cols * tw, rows * th), (255, 255, 255))
    for i, frame in enumerate(frames):
        sheet.paste(frame.resize((tw, th)), ((i % cols) * tw, (i // cols) * th))
    palette = sheet.quantize(colors=255, method=Image.MEDIANCUT, dither=Image.NONE)

    quantized = [f.quantize(palette=palette, dither=Image.NONE) for f in frames]
    quantized[0].save(gif_path, format="GIF", save_all=True,
                      append_images=quantized[1:], duration=duration_ms,
                      loop=0, optimize=False, disposal=1)
    with Image.open(gif_path) as check:
        n = getattr(check, "n_frames", 1)
        size = check.size
    if n != len(frames):
        raise RuntimeError("GIF holds %d frames, expected %d" % (n, len(frames)))
    return {"frames_in_gif": n, "size": size, "bytes": os.path.getsize(gif_path)}


# --------------------------------------------------------------------------
# the whole run
# --------------------------------------------------------------------------
def camera_report(view, snap):
    """What the framing changed: angle must be untouched, zoom/centering may move."""
    cam = view.getCameraNode()
    got = FreeCAD.Vector(view.getViewDirection())
    want = snap["direction"]
    if got.Length > 0 and want.Length > 0:
        cos = got.normalize().dot(want.normalize())
        offset = math.degrees(math.acos(max(-1.0, min(1.0, cos))))
    else:
        offset = None
    pos = cam.position.getValue()
    p0 = snap["position"]
    report = {
        "angle_offset_deg": None if offset is None else round(offset, 6),
        "angle_preserved": offset is not None and offset < 0.01,
        "zoom_before": None if snap["height"] is None else round(snap["height"], 3),
        "zoom_capture": (round(cam.height.getValue(), 3)
                         if hasattr(cam, "height") else None),
        "centering_mm": round(math.sqrt((pos[0] - p0[0]) ** 2 +
                                        (pos[1] - p0[1]) ** 2 +
                                        (pos[2] - p0[2]) ** 2), 3),
    }
    if offset is not None:
        log("camera: angle offset %.6f deg (preserved=%s), zoom %s -> %s, "
            "centering moved %s mm" % (report["angle_offset_deg"],
                                       report["angle_preserved"],
                                       report["zoom_before"], report["zoom_capture"],
                                       report["centering_mm"]))
    return report


def build_timelapse(doc, tl=None, duration_ms=700, max_px=1000,
                    hide_panel=None, background="White"):
    """Frame the final part, sweep every step, capture, assemble the GIF."""
    if not GUI:
        raise RuntimeError("GIF generation needs the FreeCAD GUI (saveImage)")
    tl = tl or timeline(doc)
    steps = tl["steps"]
    if not steps:
        raise RuntimeError("nothing to animate: the timeline is empty")

    view = active_view()
    snap = snapshot_state(doc)
    saved_camera = camera_snapshot(view)
    old_anim = animation_duration(0)
    started = time.time()
    result = {"doc": doc.Name, "steps": len(steps), "frames": [], "warnings": []}
    try:
        front_document(doc)
        if hide_panel is not None:
            hide_panel(True)
            pump(3)
            settle_view(view)
        out, frames_dir = make_output_dir(doc)
        result["outdir"] = out
        result["frames_dir"] = frames_dir

        frame_on_final_part(doc, tl, view, outer_attempts=6)
        width, height = image_size(view, max_px=max_px)
        result["frame_size"] = [width, height]
        result["camera"] = camera_report(view, saved_camera)

        previous = None
        previous_volumes = {}
        for step in steps:
            level = apply_level(doc, tl, step["index"])
            pump(3)
            name = "frame_%03d_%s.png" % (step["index"], _file_safe(step["label"]))
            path = os.path.join(frames_dir, name)
            stats = capture_view(view, path, width, height, background)
            current = gray_array(path)
            volumes = current_volumes(doc)
            if previous is None:
                delta = None
            elif previous.shape == current.shape:
                import numpy as np
                delta = round(float(np.abs(current - previous).mean()) / 255.0, 5)
            else:
                delta = None
            previous = current
            progress = step["index"] / float(len(steps))
            subline = step["short"]
            if step["profile"]:
                subline += "  <-  " + step["profile"]
            overlay_frame(path, "%d/%d  %s" % (step["index"], len(steps), step["label"]),
                          subline, progress)
            result["frames"].append({
                "index": step["index"], "level": level, "label": step["label"],
                "name": step["name"], "type": step["type"], "profile": step["profile"],
                "detail": step["detail"], "file": os.path.basename(path),
                "path": path, "pixels": stats, "progress": round(progress, 4),
                "change_vs_previous": delta,
                "volumes": volumes,
                "changed": None if previous is None else (
                    (delta is None or delta >= 0.0005) or volumes != previous_volumes
                ),
            })
            previous_volumes = volumes
            log("captured %s (%d non-white px, change %s)"
                % (name, stats["nonwhite"], delta))

        gif_path = os.path.join(out, "timelapse_%s.gif" % _file_safe(doc.Label or doc.Name))
        gif_info = make_gif([f["path"] for f in result["frames"]], gif_path,
                            duration_ms=duration_ms)
        result["gif"] = gif_path
        result["gif_info"] = gif_info
        result["duration_ms"] = duration_ms
        result["seconds"] = round(time.time() - started, 2)
        result["warnings"] = list(tl["warnings"])
        flat = [f["index"] for f in result["frames"]
                if f["change_vs_previous"] is not None
                and f["change_vs_previous"] < 0.0005]
        result["flat_frames"] = flat
        silent = [f["index"] for f in result["frames"] if f.get("changed") is False]
        result["silent_frames"] = silent
        if silent:
            result["warnings"].append(
                "frame(s) %s changed neither the pixels nor the volume: set_tip did "
                "nothing there" % ", ".join(str(i) for i in silent))
        if flat:
            result["warnings"].append(
                "frame(s) %s look identical to their predecessor: the geometry that "
                "changed there is hidden from this angle (interior feature)"
                % ", ".join(str(i) for i in flat))
        _write_manifest(result, tl)
    finally:
        restore_state(doc, snap)
        camera_restore(view, saved_camera)
        animation_duration(old_anim)
        if hide_panel is not None:
            hide_panel(False)
        pump()
    return result


def _file_safe(text):
    return "".join(c if c.isalnum() or c in "-_" else "_" for c in (text or "step"))[:40]


def _write_manifest(result, tl):
    manifest = dict(result)
    manifest.pop("frames", None)
    manifest["frame_list"] = [{k: v for k, v in f.items() if k != "path"}
                              for f in result["frames"]]
    manifest["order"] = [{"index": s["index"], "name": s["name"], "label": s["label"],
                          "type": s["type"], "body": s["body"], "profile": s["profile"],
                          "detail": s["detail"]} for s in tl["steps"]]
    path = os.path.join(result["outdir"], "manifest.json")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, indent=2)
    lines = ["computation order recovered from %s" % result["doc"], ""]
    for step in tl["steps"]:
        lines.append("%2d/%d  %-16s %-24s %s"
                     % (step["index"], len(tl["steps"]), step["label"],
                        step["type"], step["profile"] or ""))
    if tl["warnings"]:
        lines += ["", "warnings:"] + ["  - " + w for w in tl["warnings"]]
    with open(os.path.join(result["outdir"], "steps.txt"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")
    result["manifest"] = path


# --------------------------------------------------------------------------
# panel
# --------------------------------------------------------------------------
if GUI:

    class GifPreview(QtWidgets.QDialog):
        """Non-modal window that plays the generated GIF inside FreeCAD."""

        def __init__(self, gif_path, parent=None):
            super(GifPreview, self).__init__(parent)
            self.setObjectName(GIF_PREVIEW_NAME)
            self.setWindowFlags(self.windowFlags() | QtCore.Qt.Window)
            self.resize(760, 620)
            self.path = None
            self.movie = None
            lay = QtWidgets.QVBoxLayout(self)
            lay.setContentsMargins(6, 6, 6, 6)
            self.label = QtWidgets.QLabel("")
            self.label.setAlignment(QtCore.Qt.AlignCenter)
            self.label.setMinimumSize(320, 240)
            self.label.setStyleSheet("background:#1e1e1e;color:#dddddd;")
            lay.addWidget(self.label, 1)
            self.info = QtWidgets.QLabel("")
            self.info.setWordWrap(True)
            self.info.setTextInteractionFlags(QtCore.Qt.TextSelectableByMouse)
            lay.addWidget(self.info)
            row = QtWidgets.QHBoxLayout()
            self.folder_btn = QtWidgets.QPushButton("open folder")
            self.sys_btn = QtWidgets.QPushButton("open with Windows viewer")
            self.close_btn = QtWidgets.QPushButton("close")
            row.addWidget(self.folder_btn)
            row.addWidget(self.sys_btn)
            row.addStretch(1)
            row.addWidget(self.close_btn)
            lay.addLayout(row)
            self.folder_btn.clicked.connect(lambda: reveal_in_explorer(self.path))
            self.sys_btn.clicked.connect(lambda: open_with_system(self.path))
            self.close_btn.clicked.connect(self.close)
            self.open_path(gif_path)

        def open_path(self, gif_path):
            self.path = gif_path
            self.setWindowTitle("timelapse preview - %s" % os.path.basename(gif_path))
            if self.movie is not None:
                self.movie.stop()
                self.movie = None
            movie = QtGui.QMovie(gif_path)
            if not movie.isValid():
                self.label.setText("this GIF cannot be played here\n%s\n\n"
                                   "use 'open with Windows viewer'"
                                   % os.path.basename(gif_path))
                self.info.setText(gif_path)
                return
            movie.jumpToFrame(0)
            size = movie.currentPixmap().size()
            scale = min(1.0, 700.0 / max(size.width(), 1),
                        480.0 / max(size.height(), 1))
            if scale < 1.0:
                movie.setScaledSize(QtCore.QSize(max(int(size.width() * scale), 1),
                                                 max(int(size.height() * scale), 1)))
            movie.setCacheMode(QtGui.QMovie.CacheAll)
            self.movie = movie
            self.label.setMovie(movie)
            movie.start()
            try:
                kb = os.path.getsize(gif_path) / 1024.0
            except OSError:
                kb = 0.0
            self.info.setText("%d frames  |  %dx%d px  |  %.0f kB\n%s"
                              % (movie.frameCount(), size.width(), size.height(),
                                 kb, gif_path))

    def show_gif_preview(gif_path):
        """Open (or reuse) the in-FreeCAD GIF player."""
        mw = FreeCADGui.getMainWindow()
        dlg = mw.findChild(QtWidgets.QDialog, GIF_PREVIEW_NAME)
        if dlg is None:
            dlg = GifPreview(gif_path, mw)
        else:
            dlg.open_path(gif_path)
        dlg.show()
        dlg.raise_()
        dlg.activateWindow()
        pump(1)
        return dlg

    class TimelapsePanel(QtWidgets.QWidget):

        def __init__(self, doc=None, parent=None):
            super(TimelapsePanel, self).__init__(parent)
            self.setObjectName(PANEL_NAME)
            self.doc = doc
            self.tl = None
            self.level = 0
            self.snapshot = None
            self.busy = False
            self.last_result = None
            self._build_ui()
            self.refresh(initial=True)

        # -- ui --------------------------------------------------------
        def _build_ui(self):
            outer = QtWidgets.QVBoxLayout(self)
            outer.setContentsMargins(6, 6, 6, 6)
            outer.setSpacing(5)

            self.header = QtWidgets.QLabel("no document")
            self.header.setWordWrap(True)
            outer.addWidget(self.header)

            self.list = QtWidgets.QTreeWidget()
            self.list.setObjectName("Timelapse_StepList")
            self.list.setColumnCount(3)
            self.list.setHeaderLabels(["#", "feature", "type  /  made from"])
            self.list.setRootIsDecorated(False)
            self.list.setUniformRowHeights(True)
            self.list.setAlternatingRowColors(True)
            self.list.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
            self.list.setMinimumHeight(230)
            self.list.header().setSectionResizeMode(0, QtWidgets.QHeaderView.ResizeToContents)
            self.list.header().setSectionResizeMode(1, QtWidgets.QHeaderView.ResizeToContents)
            self.list.header().setSectionResizeMode(2, QtWidgets.QHeaderView.Stretch)
            mono = QtGui.QFont("Consolas")
            mono.setStyleHint(QtGui.QFont.Monospace)
            self.list.setFont(mono)
            outer.addWidget(self.list, 1)

            row = QtWidgets.QHBoxLayout()
            self.prev = QtWidgets.QPushButton("< step")
            self.next = QtWidgets.QPushButton("step >")
            self.spin = QtWidgets.QSpinBox()
            self.spin.setRange(0, 0)
            self.spin.setToolTip("Development level: how many building steps are shown")
            self.reset = QtWidgets.QPushButton("reset")
            self.final = QtWidgets.QPushButton("final")
            for widget in (self.prev, self.next, self.spin, self.reset, self.final):
                row.addWidget(widget)
            outer.addLayout(row)

            row2 = QtWidgets.QHBoxLayout()
            self.refresh_btn = QtWidgets.QPushButton("re-read tree")
            self.restore_btn = QtWidgets.QPushButton("restore original")
            row2.addWidget(self.refresh_btn)
            row2.addWidget(self.restore_btn)
            outer.addLayout(row2)

            row3 = QtWidgets.QHBoxLayout()
            self.gif_btn = QtWidgets.QPushButton("create GIF (all steps)")
            self.gif_btn.setMinimumHeight(30)
            self.open_btn = QtWidgets.QPushButton("open GIF")
            self.open_btn.setMinimumHeight(30)
            self.open_btn.setToolTip("Open the output folder and play the GIF that was "
                                     "produced last (for this document if there is one)")
            row3.addWidget(self.gif_btn, 3)
            row3.addWidget(self.open_btn, 2)
            outer.addLayout(row3)

            self.status = QtWidgets.QLabel("")
            self.status.setWordWrap(True)
            outer.addWidget(self.status)

            self.prev.clicked.connect(lambda: self.set_level(self.level - 1))
            self.next.clicked.connect(lambda: self.set_level(self.level + 1))
            self.spin.valueChanged.connect(self.set_level)
            self.reset.clicked.connect(lambda: self.set_level(0))
            self.final.clicked.connect(lambda: self.set_level(self.count()))
            self.refresh_btn.clicked.connect(lambda: self.refresh())
            self.restore_btn.clicked.connect(self.restore_original)
            self.gif_btn.clicked.connect(self.create_gif)
            self.open_btn.clicked.connect(self.open_gif)
            self.list.currentItemChanged.connect(self._on_item)

        # -- model state ----------------------------------------------
        def count(self):
            return len(self.tl["steps"]) if self.tl else 0

        def refresh(self, initial=False):
            try:
                newdoc = active_document()
                if self.doc is not None and self.doc.Name != newdoc.Name:
                    self.snapshot = None      # the old snapshot belongs to another document
                self.doc = newdoc
                self.tl = timeline(self.doc)
            except Exception as exc:
                self.status.setText("cannot read the tree: %s" % exc)
                return
            if initial or self.snapshot is None:
                self.snapshot = snapshot_state(self.doc)
            steps = self.tl["steps"]
            self.list.blockSignals(True)
            self.list.clear()
            for step in steps:
                source = step["profile"] or ""
                item = QtWidgets.QTreeWidgetItem([str(step["index"]), step["label"],
                                                  "%s  <-  %s" % (step["short"], source)
                                                  if source else step["short"]])
                item.setToolTip(2, step["detail"] or step["type"])
                self.list.addTopLevelItem(item)
            self.list.blockSignals(False)
            self.header.setText("%s   -   %d building steps"
                                % (self.doc.Label or self.doc.Name, len(steps)))
            self.spin.blockSignals(True)
            self.spin.setRange(0, len(steps))
            self.spin.setValue(max(0, min(self.level, len(steps))))
            self.spin.blockSignals(False)
            for warning in self.tl["warnings"]:
                log("warning: " + warning)
            self.set_level(max(0, min(self.level, len(steps))), from_refresh=True)

        def set_level(self, level, from_refresh=False):
            if self.busy or not self.tl:
                return
            level = max(0, min(int(level), self.count()))
            self.level = apply_level(self.doc, self.tl, level)
            pump()
            self.spin.blockSignals(True)
            self.spin.setValue(self.level)
            self.spin.blockSignals(False)
            self.list.blockSignals(True)
            if self.level == 0:
                self.list.setCurrentItem(None)
                self.list.clearSelection()
            else:
                item = self.list.topLevelItem(self.level - 1)
                self.list.setCurrentItem(item)
                self.list.scrollToItem(item)
            self.list.blockSignals(False)
            if self.level == 0:
                info = "level 0: nothing built yet"
            else:
                step = self.tl["steps"][self.level - 1]
                volumes = current_volumes(self.doc)
                tail = ""
                if volumes:
                    tail = "   |   %.1f mm3" % sum(volumes.values())
                info = "level %d/%d: %s (%s)%s" % (self.level, self.count(),
                                                   step["label"], step["short"], tail)
            if self.tl["warnings"]:
                info += "  |  %d warning(s), see report view" % len(self.tl["warnings"])
            self.status.setText(info)

        def _on_item(self, current, previous=None):
            if self.busy or current is None:
                return
            row = self.list.indexOfTopLevelItem(current)
            if row >= 0:
                self.set_level(row + 1)

        def restore_original(self):
            if self.snapshot is not None:
                restore_state(self.doc, self.snapshot)
                pump()
                self.status.setText("original tips and visibility restored")

        # -- gif -------------------------------------------------------
        def create_gif(self):
            if self.busy:
                return
            ok = False
            try:
                self.busy = True
                self.gif_btn.setEnabled(False)
                QtWidgets.QApplication.processEvents()
                self.status.setText("capturing %d frames, the window must stay "
                                    "responsive..." % self.count())
                QtWidgets.QApplication.processEvents()
                result = build_timelapse(self.doc, self.tl,
                                         hide_panel=self.set_capture_mode)
                self.last_result = result
                note = ""
                if result.get("flat_frames"):
                    note = "\nnote: frame(s) %s look identical to the previous one" % (
                        ", ".join(str(i) for i in result["flat_frames"]))
                cam = result.get("camera") or {}
                camnote = ""
                if cam.get("angle_offset_deg") is not None:
                    camnote = ("\ncamera: viewing angle %s (%.4f deg), zoom %s -> %s, "
                               "centering moved %s mm"
                               % ("kept" if cam["angle_preserved"] else "CHANGED",
                                  cam["angle_offset_deg"], cam.get("zoom_before"),
                                  cam.get("zoom_capture"), cam.get("centering_mm")))
                self.status.setText(
                    "GIF written: %s\n%d frames, %s, %s s%s%s"
                    % (result["gif"], result["gif_info"]["frames_in_gif"],
                       "x".join(str(v) for v in result["gif_info"]["size"]),
                       result["seconds"], note, camnote))
                log("GIF: " + result["gif"])
                self.snapshot = snapshot_state(self.doc)
                ok = True
            except Exception as exc:
                self.status.setText("GIF failed: %s" % exc)
                warn("GIF failed: %s" % exc)
                traceback.print_exc(file=sys.stdout)
            finally:
                self.busy = False
                self.gif_btn.setEnabled(True)
                if ok:
                    # re-apply the level the user was browsing and keep the run
                    # summary in the status line (set_level would overwrite it)
                    summary = self.status.text()
                    self.set_level(self.level)
                    self.status.setText(summary)

        def open_gif(self):
            """Show the folder that holds the GIF and play the GIF itself."""
            gif = None
            if self.last_result and self.last_result.get("gif"):
                if os.path.isfile(self.last_result["gif"]):
                    gif = self.last_result["gif"]
            if gif is None:
                gif = latest_gif(self.doc)
            if gif is None:
                self.status.setText("no GIF yet - click 'create GIF (all steps)' first\n"
                                    "(output folder: %s)" % timelapse_root())
                return
            try:
                show_gif_preview(gif)
            except Exception as exc:
                warn("in-FreeCAD preview failed (%s), using the Windows viewer" % exc)
                open_with_system(gif)
            reveal_in_explorer(gif)
            self.status.setText("GIF: %s" % gif)
            log("open GIF: " + gif)

        def set_capture_mode(self, on):
            """Give the 3D view the whole window while frames are captured."""
            if not GUI:
                return
            dock = FreeCADGui.getMainWindow().findChild(QtWidgets.QDockWidget, DOCK_NAME)
            if dock is not None:
                dock.setVisible(not on)
                pump(2)
                if not on:
                    dock.setVisible(True)

    class TimelapseDock(QtWidgets.QDockWidget):
        def closeEvent(self, event):
            panel = self.widget()
            if isinstance(panel, TimelapsePanel) and panel.snapshot is not None:
                try:
                    restore_state(panel.doc, panel.snapshot)
                except Exception as exc:
                    warn("restore on close failed: %s" % exc)
            super(TimelapseDock, self).closeEvent(event)


def open_panel():
    """Entry point of the .FCMacro: show (or reuse) the timelapse panel."""
    if not GUI:
        raise RuntimeError("the timelapse panel needs the FreeCAD GUI")
    doc = active_document()
    main = FreeCADGui.getMainWindow()
    dock = main.findChild(QtWidgets.QDockWidget, DOCK_NAME)
    if dock is None:
        dock = TimelapseDock("Timelapse - building steps", main)
        dock.setObjectName(DOCK_NAME)
        dock.setWidget(TimelapsePanel(doc))
        dock.setAllowedAreas(QtCore.Qt.LeftDockWidgetArea | QtCore.Qt.RightDockWidgetArea)
        main.addDockWidget(QtCore.Qt.RightDockWidgetArea, dock)
    else:
        panel = dock.widget()
        if not isinstance(panel, TimelapsePanel):
            # the library was reloaded: the widget holds a stale class instance
            dock.setWidget(TimelapsePanel(doc))
        else:
            panel.doc = doc
            panel.refresh()
        dock.setWidget(dock.widget())
    dock.setVisible(True)
    dock.raise_()
    pump()
    panel = dock.widget()
    if isinstance(panel, TimelapsePanel):
        panel.set_level(panel.count())
    log("panel ready: %s, %d steps" % (doc.Name, panel.count() if isinstance(panel, TimelapsePanel) else -1))
    return dock


# --------------------------------------------------------------------------
# headless report (freecadcmd): python timelapse_lib.py <file.FCStd>
# --------------------------------------------------------------------------
def report(path):
    doc = FreeCAD.openDocument(path)
    doc.recompute()
    tl = timeline(doc)
    print("%s : %d step(s)" % (doc.Label, len(tl["steps"])))
    for step in tl["steps"]:
        print("%2d/%d  %-18s %-26s %s" % (step["index"], len(tl["steps"]),
                                          step["label"], step["type"],
                                          step["profile"] or ""))
    for warning in tl["warnings"]:
        print("WARNING:", warning)
    sys.stdout.flush()
    return tl


if __name__ == "__main__":
    pass
