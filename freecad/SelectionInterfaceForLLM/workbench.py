# SPDX-License-Identifier: LGPL-2.1-or-later
"""The workbench: a toolbar and a menu holding the two commands of this addon.

FreeCAD looks for the class named in ``package.xml`` (``<classname>``) inside the
addon's ``init_gui`` module, which imports this one, so the name must not change
without changing the manifest.
"""

import FreeCADGui as Gui

from .commands import CREATE_GIF, OPEN_PANEL
from .resources import icon


class SelectionInterfaceWorkbench(Gui.Workbench):
    """Nothing but two commands: the addon adds no geometry to the document."""

    MenuText = "Selection interface"
    ToolTip = ("Step through the computation order of a PartDesign document, show one "
               "feature at a time (datum planes and driving sketches included) and "
               "export the build-up as a GIF")
    Icon = icon("Logo.svg")

    def Initialize(self):
        commands = [OPEN_PANEL, CREATE_GIF]
        self.appendToolbar("Selection interface", commands)
        self.appendMenu("Selection interface", commands)

    def Activated(self):
        pass

    def Deactivated(self):
        pass

    def GetClassName(self):
        return "Gui::PythonWorkbench"

    @classmethod
    def Install(cls):
        """Register the workbench; a second call (module reload) is harmless."""
        try:
            Gui.addWorkbench(cls)
            return True
        except Exception as exc:  # already registered
            try:
                from .interface import warn

                warn("cannot register the workbench: %s" % exc)
            except Exception:
                pass
            return False
