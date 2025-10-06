"""Business logic for working with tiles and Hilbert curve identifiers."""
from dataclasses import dataclass
import math
from typing import Dict, List, Tuple

from hilbertcurve.hilbertcurve import HilbertCurve

from ..constants import (
    MARCO_ZERO_X,
    MARCO_ZERO_Y,
    X_MAX_AREA,
    X_MIN_AREA,
    Y_MAX_AREA,
    Y_MIN_AREA,
)
from ..projections import sirgas_to_wgs84, wgs84_to_sirgas
from ..utils import from_base36, to_base36


@dataclass(frozen=True)
class TileGrid:
    level: int
    tile_size: float
    min_i: int
    min_j: int
    max_i: int
    max_j: int

    @property
    def width(self) -> int:
        return self.max_i - self.min_i + 1

    @property
    def height(self) -> int:
        return self.max_j - self.min_j + 1

    @property
    def hilbert_order(self) -> int:
        return max(1, math.ceil(math.log2(max(self.width, self.height))))


@dataclass(frozen=True)
class Tile:
    tile_id: str
    level: int
    bbox: Tuple[float, float, float, float]
    grid_coords: Tuple[int, int]
    normalized_coords: Tuple[int, int]
    hilbert_distance: int

    @property
    def center(self) -> Tuple[float, float]:
        x_min, y_min, x_max, y_max = self.bbox
        return (x_min + x_max) / 2.0, (y_min + y_max) / 2.0


class TileService:
    """Service responsible for computing tile metadata."""

    def __init__(self) -> None:
        self._grid_cache: Dict[int, TileGrid] = {}

    def _grid_for_level(self, level: int) -> TileGrid:
        if level in self._grid_cache:
            return self._grid_cache[level]

        tile_size = get_tile_size_from_level(level)
        min_i = math.floor((X_MIN_AREA - (MARCO_ZERO_X - tile_size / 2)) / tile_size)
        min_j = math.floor((Y_MIN_AREA - (MARCO_ZERO_Y - tile_size / 2)) / tile_size)
        max_i = math.ceil((X_MAX_AREA - (MARCO_ZERO_X - tile_size / 2)) / tile_size) - 1
        max_j = math.ceil((Y_MAX_AREA - (MARCO_ZERO_Y - tile_size / 2)) / tile_size) - 1

        grid = TileGrid(
            level=level,
            tile_size=tile_size,
            min_i=min_i,
            min_j=min_j,
            max_i=max_i,
            max_j=max_j,
        )
        self._grid_cache[level] = grid
        return grid

    def _hilbert_curve(self, grid: TileGrid) -> HilbertCurve:
        return HilbertCurve(grid.hilbert_order, 2)

    def generate_tiles(self, level: int) -> List[Tile]:
        grid = self._grid_for_level(level)
        hilbert = self._hilbert_curve(grid)
        tiles: List[Tile] = []

        for j_idx in range(grid.min_j, grid.max_j + 1):
            for i_idx in range(grid.min_i, grid.max_i + 1):
                x_min = (MARCO_ZERO_X - grid.tile_size / 2) + i_idx * grid.tile_size
                y_min = (MARCO_ZERO_Y - grid.tile_size / 2) + j_idx * grid.tile_size
                x_max = x_min + grid.tile_size
                y_max = y_min + grid.tile_size

                normalized_i = i_idx - grid.min_i
                normalized_j = j_idx - grid.min_j
                hilbert_distance = hilbert.distances_from_points([[normalized_i, normalized_j]])[0]
                tile_id = to_base36(hilbert_distance)

                tiles.append(
                    Tile(
                        tile_id=tile_id,
                        level=level,
                        bbox=(x_min, y_min, x_max, y_max),
                        grid_coords=(i_idx, j_idx),
                        normalized_coords=(normalized_i, normalized_j),
                        hilbert_distance=hilbert_distance,
                    )
                )

        tiles.sort(key=lambda t: t.hilbert_distance)
        return tiles

    def tile_from_id(self, level: int, tile_id: str) -> Tile:
        grid = self._grid_for_level(level)
        hilbert = self._hilbert_curve(grid)
        distance = from_base36(tile_id)

        max_distance = (2 ** grid.hilbert_order) ** 2
        if not 0 <= distance < max_distance:
            raise ValueError("Tile identifier is out of bounds for the specified level.")

        normalized_i, normalized_j = hilbert.points_from_distances([distance])[0]
        if normalized_i >= grid.width or normalized_j >= grid.height:
            raise ValueError("Tile identifier does not map to the configured area extent.")

        i_idx = normalized_i + grid.min_i
        j_idx = normalized_j + grid.min_j

        x_min = (MARCO_ZERO_X - grid.tile_size / 2) + i_idx * grid.tile_size
        y_min = (MARCO_ZERO_Y - grid.tile_size / 2) + j_idx * grid.tile_size
        x_max = x_min + grid.tile_size
        y_max = y_min + grid.tile_size

        return Tile(
            tile_id=tile_id.upper(),
            level=level,
            bbox=(x_min, y_min, x_max, y_max),
            grid_coords=(i_idx, j_idx),
            normalized_coords=(normalized_i, normalized_j),
            hilbert_distance=distance,
        )

    def tile_for_coordinates(self, level: int, lon: float, lat: float) -> Tile:
        easting, northing = wgs84_to_sirgas(lon, lat)
        tile_size = get_tile_size_from_level(level)
        origin_x = MARCO_ZERO_X - tile_size / 2
        origin_y = MARCO_ZERO_Y - tile_size / 2
        i_idx = math.floor((easting - origin_x) / tile_size)
        j_idx = math.floor((northing - origin_y) / tile_size)

        grid = self._grid_for_level(level)
        normalized_i = i_idx - grid.min_i
        normalized_j = j_idx - grid.min_j
        if normalized_i < 0 or normalized_j < 0 or normalized_i >= grid.width or normalized_j >= grid.height:
            raise ValueError("Coordinates fall outside of the configured area extent.")

        hilbert = self._hilbert_curve(grid)
        distance = hilbert.distances_from_points([[normalized_i, normalized_j]])[0]
        tile_id = to_base36(distance)

        x_min = (MARCO_ZERO_X - grid.tile_size / 2) + i_idx * grid.tile_size
        y_min = (MARCO_ZERO_Y - grid.tile_size / 2) + j_idx * grid.tile_size
        x_max = x_min + grid.tile_size
        y_max = y_min + grid.tile_size

        return Tile(
            tile_id=tile_id,
            level=level,
            bbox=(x_min, y_min, x_max, y_max),
            grid_coords=(i_idx, j_idx),
            normalized_coords=(normalized_i, normalized_j),
            hilbert_distance=distance,
        )


def get_tile_size_from_level(level: int) -> float:
    base_size = 100_000.0
    if level < 0:
        raise ValueError("Level cannot be negative.")

    tile_size = base_size / (2**level)
    return tile_size if tile_size >= 1.0 else 1.0


def build_tile_feature(tile: Tile) -> Dict:
    center_x, center_y = tile.center
    center_lon, center_lat = sirgas_to_wgs84(center_x, center_y)
    x_min, y_min, x_max, y_max = tile.bbox

    ring_vertices = [
        (x_min, y_min),
        (x_max, y_min),
        (x_max, y_max),
        (x_min, y_max),
    ]
    polygon = []
    for vertex_x, vertex_y in ring_vertices:
        lon, lat = sirgas_to_wgs84(vertex_x, vertex_y)
        polygon.append([lon, lat])
    polygon.append(polygon[0])

    return {
        "type": "Feature",
        "geometry": {
            "type": "Polygon",
            "coordinates": [polygon],
        },
        "properties": {
            "id": tile.tile_id.upper(),
            "level": tile.level,
            "center_x": center_x,
            "center_y": center_y,
            "center_lon": center_lon,
            "center_lat": center_lat,
            "tile_size": x_max - x_min,
            "bbox": {
                "x_min": x_min,
                "y_min": y_min,
                "x_max": x_max,
                "y_max": y_max,
            },
            "grid_coords": {
                "i": tile.grid_coords[0],
                "j": tile.grid_coords[1],
            },
            "normalized_grid_coords": {
                "i": tile.normalized_coords[0],
                "j": tile.normalized_coords[1],
            },
            "hilbert_distance": tile.hilbert_distance,
        },
    }
