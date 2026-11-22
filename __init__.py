"""Strike/Dip Plotter - QGIS plugin entry point."""


def classFactory(iface):
    """Called by QGIS to load the plugin."""
    from .strike_dip import StrikeDipPlugin

    return StrikeDipPlugin(iface)
