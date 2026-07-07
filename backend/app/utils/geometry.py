from typing import List, Tuple, Optional
from shapely.geometry import Point, Polygon, LineString

def points_to_polygon(points: List[List[int]]) -> Polygon:
    return Polygon(points)

def points_to_line(points: List[List[int]]) -> LineString:
    return LineString(points)

def point_in_polygon(x: float, y: float, polygon: Polygon) -> bool:
    return polygon.contains(Point(x, y))

def bbox_center(x1: float, y1: float, x2: float, y2: float) -> Tuple[float, float]:
    return (x1 + x2) / 2.0, (y1 + y2) / 2.0
