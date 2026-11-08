# SPDX-License-Identifier: LGPL-2.1-or-later
"""Single source of truth for the version number.

``pyproject.toml`` reads it (``[tool.hatch.version]``), ``__init__.py`` re-exports
it, and ``interface.py`` uses it for the panel header and the status lines. Keep it
in step with ``<version>`` in ``package.xml``: the Addon Manager only talks about
that one.
"""

__version__ = "2.3.0"
