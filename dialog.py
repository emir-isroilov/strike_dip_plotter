"""Dialog that reads a CSV file and builds a styled strike/dip point layer."""

import csv
import os

from qgis.core import (
    Qgis,
    QgsCoordinateReferenceSystem,
    QgsFeature,
    QgsGeometry,
    QgsPalLayerSettings,
    QgsPointXY,
    QgsProject,
    QgsProperty,
    QgsSingleSymbolRenderer,
    QgsSvgMarkerSymbolLayer,
    QgsMarkerSymbol,
    QgsTextFormat,
    QgsVectorLayer,
    QgsVectorLayerSimpleLabeling,
)
from qgis.gui import QgsFileWidget, QgsProjectionSelectionWidget
from qgis.PyQt.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QVBoxLayout,
)

# Column names we try to recognise automatically (lower case).
GUESSES = {
    "x": ["x", "lon", "long", "longitude", "lng", "easting", "east", "e"],
    "y": ["y", "lat", "latitude", "northing", "north", "n"],
    "azimuth": ["strike", "azimuth", "az", "dip_dir", "dipdir", "dip_direction", "dd"],
    "dip": ["dip", "dip_angle", "inclination"],
}

MODE_STRIKE_RHR = 0
MODE_DIP_DIRECTION = 1


def _message_level(name):
    """Return a Qgis message level that works on old and new QGIS versions."""
    levels = getattr(Qgis, "MessageLevel", None)
    if levels is not None and hasattr(levels, name):
        return getattr(levels, name)
    return getattr(Qgis, name)


def _to_float(value):
    """Convert a CSV cell to float, accepting decimal commas."""
    return float(str(value).strip().replace(",", "."))


class StrikeDipDialog(QDialog):
    def __init__(self, iface, plugin_dir, parent=None):
        super().__init__(parent)
        self.iface = iface
        self.plugin_dir = plugin_dir
        self.delimiter = ","
        self.setWindowTitle("Strike/Dip Plotter")
        self.setMinimumWidth(460)
        self._build_ui()

    # ------------------------------------------------------------------ UI
    def _build_ui(self):
        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.file_widget = QgsFileWidget()
        self.file_widget.setFilter("CSV files (*.csv *.txt)")
        self.file_widget.fileChanged.connect(self._load_header)
        form.addRow("CSV file:", self.file_widget)

        self.x_combo = QComboBox()
        self.y_combo = QComboBox()
        self.az_combo = QComboBox()
        self.dip_combo = QComboBox()
        form.addRow("X / Longitude column:", self.x_combo)
        form.addRow("Y / Latitude column:", self.y_combo)
        form.addRow("Azimuth column:", self.az_combo)
        form.addRow("Dip column:", self.dip_combo)

        self.mode_combo = QComboBox()
        self.mode_combo.addItem("Strike (right-hand rule)", MODE_STRIKE_RHR)
        self.mode_combo.addItem("Dip direction", MODE_DIP_DIRECTION)
        form.addRow("Azimuth means:", self.mode_combo)

        self.crs_widget = QgsProjectionSelectionWidget()
        self.crs_widget.setCrs(QgsCoordinateReferenceSystem("EPSG:4326"))
        form.addRow("Coordinate system:", self.crs_widget)

        self.name_edit = QLineEdit("Strike-Dip measurements")
        form.addRow("Layer name:", self.name_edit)

        layout.addLayout(form)
        hint = QLabel(
            "Strike and azimuth values: 0-360 degrees. Dip: 0-90 degrees.\n"
            "Rows with missing or invalid values are skipped."
        )
        hint.setWordWrap(True)
        layout.addWidget(hint)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _load_header(self, path):
        """Read the CSV header, detect delimiter and fill the column combos."""
        combos = (self.x_combo, self.y_combo, self.az_combo, self.dip_combo)
        for combo in combos:
            combo.clear()
        if not path or not os.path.isfile(path):
            return
        try:
            with open(path, newline="", encoding="utf-8-sig") as f:
                sample = f.read(4096)
                try:
                    self.delimiter = csv.Sniffer().sniff(sample, delimiters=",;\t").delimiter
                except csv.Error:
                    self.delimiter = ","
                f.seek(0)
                header = next(csv.reader(f, delimiter=self.delimiter))
        except (OSError, UnicodeDecodeError, StopIteration) as err:
            QMessageBox.warning(self, "Strike/Dip Plotter", f"Could not read file:\n{err}")
            return

        header = [h.strip() for h in header]
        for combo in combos:
            combo.addItems(header)

        lower = [h.lower() for h in header]
        for combo, key in zip(combos, ("x", "y", "azimuth", "dip")):
            for guess in GUESSES[key]:
                if guess in lower:
                    combo.setCurrentIndex(lower.index(guess))
                    break

        # If the azimuth column looks like dip direction, switch mode.
        az_name = self.az_combo.currentText().lower()
        if az_name in ("dip_dir", "dipdir", "dip_direction", "dd"):
            self.mode_combo.setCurrentIndex(MODE_DIP_DIRECTION)

    # --------------------------------------------------------------- logic
    def accept(self):
        path = self.file_widget.filePath()
        if not path or not os.path.isfile(path):
            QMessageBox.warning(self, "Strike/Dip Plotter", "Please choose a CSV file.")
            return
        if self.x_combo.count() == 0:
            QMessageBox.warning(self, "Strike/Dip Plotter", "The CSV file has no columns.")
            return

        layer, loaded, skipped = self._build_layer(path)
        if loaded == 0:
            QMessageBox.warning(
                self,
                "Strike/Dip Plotter",
                "No valid measurements found. Check the selected columns.",
            )
            return

        self._style_layer(layer)
        QgsProject.instance().addMapLayer(layer)
        self.iface.setActiveLayer(layer)
        self.iface.zoomToActiveLayer()

        msg = f"Loaded {loaded} measurements."
        level = _message_level("Success")
        if skipped:
            msg += f" Skipped {skipped} invalid rows."
            level = _message_level("Warning")
        self.iface.messageBar().pushMessage("Strike/Dip Plotter", msg, level=level, duration=6)
        super().accept()

    def _build_layer(self, path):
        cols = (
            self.x_combo.currentText(),
            self.y_combo.currentText(),
            self.az_combo.currentText(),
            self.dip_combo.currentText(),
        )
        mode = self.mode_combo.currentData()

        uri = (
            "Point?field=id:integer&field=strike:double"
            "&field=dip_dir:double&field=dip:double"
        )
        layer = QgsVectorLayer(uri, self.name_edit.text() or "Strike-Dip", "memory")
        layer.setCrs(self.crs_widget.crs())

        features = []
        skipped = 0
        with open(path, newline="", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f, delimiter=self.delimiter)
            reader.fieldnames = [h.strip() for h in reader.fieldnames]
            for row in reader:
                try:
                    x, y, azimuth, dip = (_to_float(row[c]) for c in cols)
                except (ValueError, KeyError, TypeError):
                    skipped += 1
                    continue
                if not (0 <= azimuth <= 360 and 0 <= dip <= 90):
                    skipped += 1
                    continue

                if mode == MODE_DIP_DIRECTION:
                    dip_dir = azimuth % 360
                    strike = (azimuth - 90) % 360
                else:
                    strike = azimuth % 360
                    dip_dir = (azimuth + 90) % 360

                feat = QgsFeature(layer.fields())
                feat.setGeometry(QgsGeometry.fromPointXY(QgsPointXY(x, y)))
                feat.setAttributes([len(features) + 1, strike, dip_dir, dip])
                features.append(feat)

        layer.dataProvider().addFeatures(features)
        layer.updateExtents()
        return layer, len(features), skipped

    def _style_layer(self, layer):
        # Oriented strike/dip symbol, rotated clockwise by the strike value.
        svg_path = os.path.join(self.plugin_dir, "symbols", "strike_dip.svg")
        svg_layer = QgsSvgMarkerSymbolLayer(svg_path, 8.0)
        symbol = QgsMarkerSymbol()
        symbol.changeSymbolLayer(0, svg_layer)
        symbol.setDataDefinedAngle(QgsProperty.fromField("strike"))
        layer.setRenderer(QgsSingleSymbolRenderer(symbol))

        # Dip angle label next to each symbol.
        settings = QgsPalLayerSettings()
        settings.fieldName = 'round("dip")'
        settings.isExpression = True
        settings.dist = 1.5
        text_format = QgsTextFormat()
        text_format.setSize(8)
        settings.setFormat(text_format)
        layer.setLabeling(QgsVectorLayerSimpleLabeling(settings))
        layer.setLabelsEnabled(True)
        layer.triggerRepaint()
