# SPDX-License-Identifier: LGPL-2.1-or-later
"""Selection interface for LLM -- a FreeCAD addon (headless entry point).

This module is imported once at FreeCAD startup, in headless mode too, so it must
stay cheap and must not import Qt. All GUI work happens in ``init_gui.py``, which
FreeCAD imports after this file when the GUI is available.

FreeCAD finds the addon through the native namespace package layout::

    freecad/SelectionInterfaceForLLM/

The ``freecad`` directory itself has no ``__init__.py`` on purpose: it is a shared
namespace, so several addons can live under it at the same time without their
top-level module names colliding in ``sys.modules``.

What the addon does is described in ``README.md``; the panel, the ordering engine
and the GIF export live in ``interface.py``.
"""

from .version import __version__  # noqa: F401  (re-exported for convenience)
