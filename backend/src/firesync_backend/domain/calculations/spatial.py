"""Bounded WGS84 selections; H3 IDs stay as text at domain boundaries."""
from math import isfinite

import h3
from pyproj import Geod
from shapely.geometry import Polygon, mapping, shape

from firesync_backend.domain.models.error import CalendarError

MAX_CELLS = 250_000


def cells_for_area(area, resolution=6):
    if resolution != 6:
        raise CalendarError("invalid_data", "Unsupported H3 resolution.")
    if area.type == "point":
        geod = Geod(ellps="WGS84")
        coordinates = [geod.fwd(area.lon, area.lat, angle, area.radius_km * 1000)[:2]
                       for angle in range(0, 360, 3)]
        polygon = Polygon(coordinates)
    elif area.type == "geojson":
        geometry = area.geometry
        if geometry.get("type") not in {"Polygon", "MultiPolygon"}:
            raise CalendarError("invalid_geometry", "Use a Polygon or MultiPolygon.")
        try:
            polygons = [geometry["coordinates"]] if geometry["type"] == "Polygon" else geometry["coordinates"]
            for rings in polygons:
                for ring in rings:
                    if len(ring) < 4 or ring[0] != ring[-1]:
                        raise ValueError
                    for point in ring:
                        if len(point) != 2 or not all(isfinite(x) for x in point):
                            raise ValueError
                        if not (-180 <= point[0] <= 180 and -90 <= point[1] <= 90):
                            raise ValueError
            polygon = shape(geometry)
        except (KeyError, ValueError, TypeError, IndexError):
            raise CalendarError("invalid_geometry", "Invalid WGS84 polygon.") from None
    else:
        raise CalendarError("invalid_geometry", "Regions must be resolved by the repository.")
    if polygon.is_empty or not polygon.is_valid or polygon.area == 0:
        raise CalendarError("invalid_geometry", "Invalid polygon topology.")
    geo = mapping(polygon)
    # Reject very large selections before allocating their fine-resolution cells.
    if len(h3.geo_to_cells(geo, 3)) > 2000:
        raise CalendarError("area_too_large", "The selected area is too large.")
    cells = set(h3.geo_to_cells(geo, resolution))
    if not cells:
        center = polygon.representative_point()
        cells.add(h3.latlng_to_cell(center.y, center.x, resolution))
    if len(cells) > MAX_CELLS:
        raise CalendarError("area_too_large", "The selected area is too large.")
    return tuple(sorted(cells))
