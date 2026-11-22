# Strike Dip Plotter

A QGIS plugin that loads structural geology field measurements from a CSV file
and displays them as oriented strike/dip symbols with dip-angle labels.

## Features

- Reads CSV files separated by comma, semicolon or tab; accepts decimal commas.
- Detects common column names automatically (`lon/lat`, `x/y`, `easting/northing`,
  `strike`, `dip_dir`, `dip`).
- Supports two conventions: strike (right-hand rule) and dip direction.
- Any coordinate reference system (e.g. EPSG:4326, UTM).
- Skips invalid rows and reports how many were skipped.

## Installation

From the QGIS Plugin Repository: *Plugins → Manage and Install Plugins*, search
for **Strike Dip Plotter**.

From ZIP: *Plugins → Manage and Install Plugins → Install from ZIP*.

## Usage

1. Click the **Strike/Dip Plotter** toolbar button (or *Vector → Strike/Dip Plotter*).
2. Choose a CSV file and check the detected columns.
3. Choose the convention and coordinate system, then press **OK**.

A sample file, `sample_data.csv`, is included.

### CSV example

```
id,lon,lat,strike,dip
1,69.240,41.311,45,30
2,69.252,41.318,120,55
```

## Contributing

Bug reports and pull requests are welcome in the issue tracker.

## License

GNU General Public License v2.0 or later. See `LICENSE`.
