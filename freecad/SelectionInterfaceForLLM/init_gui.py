# SPDX-License-Identifier: LGPL-2.1-or-later
"""GUI entry point: register the icons, the commands and the workbench.

FreeCAD imports this module (after ``__init__.py``) only when a GUI exists, so it
is the only place of the addon where Qt or FreeCADGui may be used at import time.
Keep it fast: it runs on every FreeCAD GUI startup.

Loading sequence, as documented by the FreeCAD addon template:

    1. freecad.SelectionInterfaceForLLM            (headless, always)
    2. freecad.SelectionInterfaceForLLM.init_gui   (GUI only, this file)
"""

from .commands import install as install_commands
from .resources import gui_register_icons
from .workbench import SelectionInterfaceWorkbench

_REGISTERED = False

if not _REGISTERED:
    gui_register_icons()
    install_commands()
    SelectionInterfaceWorkbench.Install()
    _REGISTERED = True
