# SPDX-License-Identifier: LGPL-2.1-or-later
"""Files shipped with the addon: icons and documentation.

Kept free of Qt at import time: ``gui_register_icons()`` is only called from
``init_gui.py``, i.e. when a GUI really exists.
"""

import os

RESOURCES_DIR = os.path.dirname(os.path.abspath(__file__))
ICONS_DIR = os.path.join(RESOURCES_DIR, "icons")
DOCS_DIR = os.path.join(RESOURCES_DIR, "docs")


def icon(name):
    """Absolute path of an icon file, or '' when it is missing."""
    path = os.path.join(ICONS_DIR, name)
    return path if os.path.isfile(path) else ""


def gui_register_icons():
    """Let FreeCAD/Qt resolve the icon names of this addon by file name."""
    try:
        import FreeCADGui

        FreeCADGui.addIconPath(ICONS_DIR)
        return True
    except Exception:  # pragma: no cover - no GUI, nothing to register
        return False


def doc_path(name):
    """Absolute path of a documentation file shipped with the addon."""
    return os.path.join(DOCS_DIR, name)
