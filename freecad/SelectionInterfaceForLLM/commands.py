# SPDX-License-Identifier: LGPL-2.1-or-later
"""Toolbar/menu commands of the Selection interface workbench.

Every command is registered under its own ``Name`` so that it can be reached from
the toolbar, the menu, a macro (``FreeCADGui.runCommand("...")``) or a test.
Nothing here runs at import time except the class definitions.
"""

import FreeCAD as App
import FreeCADGui as Gui

from . import interface
from .resources import icon

OPEN_PANEL = "SelectionInterface_OpenPanel"
CREATE_GIF = "SelectionInterface_CreateGif"

_COMMANDS = []


class OpenPanelCommand:
    """Show (or re-use) the panel that steps through the computation order."""

    Name = OPEN_PANEL

    def GetResources(self):
        return {
            "Pixmap": icon("Logo.svg"),
            "MenuText": "Building steps panel",
            "ToolTip": "Step through the computation order of this document,\n"
                       "show one feature at a time, and export the build-up as a GIF",
        }

    def IsActive(self):
        return App.ActiveDocument is not None

    def Activated(self):
        dock = interface.open_panel()
        interface.log("command %s: dock %s" % (self.Name, bool(dock)))
        return dock


class CreateGifCommand:
    """Open the panel and run the whole capture straight away."""

    Name = CREATE_GIF

    def GetResources(self):
        return {
            "Pixmap": icon("Logo.svg"),
            "MenuText": "GIF of the whole build",
            "ToolTip": "Open the panel and export every building step of this document\n"
                       "as an animated GIF in the Downloads folder",
        }

    def IsActive(self):
        return App.ActiveDocument is not None

    def Activated(self):
        dock = interface.open_panel()
        panel = dock.widget() if dock is not None else None
        if panel is None or not hasattr(panel, "gif_btn"):
            interface.warn("the panel did not open: no GIF was created")
            return None
        panel.gif_btn.click()  # same code path as the button, including busy guard
        return panel.last_result


def install():
    """Register the commands; safe to call twice (a reload cannot raise)."""
    for command in (OpenPanelCommand(), CreateGifCommand()):
        try:
            Gui.addCommand(command.Name, command)
            _COMMANDS.append(command.Name)
        except Exception as exc:  # already registered (module reloaded, etc.)
            if command.Name not in _COMMANDS:
                interface.warn("cannot register %s: %s" % (command.Name, exc))
    return list(_COMMANDS)


def command_names():
    return [OPEN_PANEL, CREATE_GIF]
