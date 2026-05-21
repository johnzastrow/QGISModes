# -*- coding: utf-8 -*-
"""QGIS Modes — switchable simplified QGIS interfaces.

Copyright (C) 2026  John Zastrow

Derived from QGIS Light (https://github.com/ITC-CRIB/qgis-light),
Copyright (C) 2024  Serkan Girgin. QGIS Modes extends QGIS Light's single
config-driven simplified interface into multiple named, switchable "modes".

This program is free software: you can redistribute it and/or modify it under
the terms of the GNU General Public License as published by the Free Software
Foundation, either version 3 of the License, or (at your option) any later
version. See the LICENSE file for details.
"""


def classFactory(iface):
    """Entry point QGIS calls to instantiate the plugin.

    Args:
        iface: QGIS interface object.

    Returns:
        A QGISModesPlugin instance.
    """
    from .qgis_modes import QGISModesPlugin
    return QGISModesPlugin(iface)
