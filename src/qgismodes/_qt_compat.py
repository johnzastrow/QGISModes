# -*- coding: utf-8 -*-
"""Qt 5 / Qt 6 compatibility shims.

Two known API differences between PyQt5 (QGIS 3) and PyQt6 (QGIS 4):

  * ``QgsSettings`` preserves Qt enum types under Qt 6 but returns plain
    integers under Qt 5. Use :func:`to_enum` to normalise reads.
  * ``QAction.associatedWidgets()`` was renamed to ``associatedObjects()``
    when ``QAction`` moved to ``QtGui`` in Qt 6. Use
    :func:`associated_objects` instead of either directly.
"""


def to_enum(enum_type, value):
    """Coerce a value (int or enum) to an instance of ``enum_type``.

    Args:
        enum_type: A Qt enum class (e.g. ``Qt.ToolBarArea``).
        value: A value previously read from ``QgsSettings`` — either an enum
            instance (Qt 6) or a plain integer (Qt 5).

    Returns:
        The value as an instance of ``enum_type``.
    """
    if isinstance(value, enum_type):
        return value
    return enum_type(value)


def associated_objects(action):
    """Return widgets/objects associated with a ``QAction`` (Qt5/Qt6)."""
    if hasattr(action, "associatedObjects"):
        return action.associatedObjects()
    return action.associatedWidgets()
