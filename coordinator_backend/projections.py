"""Projection helpers for converting between WGS84 and SIRGAS 2000 / Brazil Albers."""
from functools import lru_cache
from typing import Tuple

from pyproj import CRS, Transformer

from .constants import SIRGAS_2000_BRAZIL_ALBERS_WKT


@lru_cache(maxsize=1)
def _wgs84_crs() -> CRS:
    return CRS("EPSG:4326")


@lru_cache(maxsize=1)
def _sirgas_albers_crs() -> CRS:
    return CRS(SIRGAS_2000_BRAZIL_ALBERS_WKT)


@lru_cache(maxsize=1)
def _wgs84_to_sirgas_transformer() -> Transformer:
    return Transformer.from_crs(_wgs84_crs(), _sirgas_albers_crs(), always_xy=True)


@lru_cache(maxsize=1)
def _sirgas_to_wgs84_transformer() -> Transformer:
    return Transformer.from_crs(_sirgas_albers_crs(), _wgs84_crs(), always_xy=True)


def wgs84_to_sirgas(lon: float, lat: float) -> Tuple[float, float]:
    """Convert longitude/latitude (WGS84) to SIRGAS 2000 / Brazil Albers coordinates."""
    transformer = _wgs84_to_sirgas_transformer()
    easting, northing = transformer.transform(lon, lat)
    return float(easting), float(northing)


def sirgas_to_wgs84(easting: float, northing: float) -> Tuple[float, float]:
    """Convert SIRGAS 2000 / Brazil Albers coordinates to longitude/latitude."""
    transformer = _sirgas_to_wgs84_transformer()
    lon, lat = transformer.transform(easting, northing)
    return float(lon), float(lat)
