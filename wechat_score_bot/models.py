from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List, Sequence, Tuple


Point = Tuple[int, int]


@dataclass(frozen=True)
class Rect:
    x: int
    y: int
    width: int
    height: int

    @property
    def left(self) -> int:
        return self.x

    @property
    def top(self) -> int:
        return self.y

    @property
    def right(self) -> int:
        return self.x + self.width

    @property
    def bottom(self) -> int:
        return self.y + self.height

    @property
    def center(self) -> Point:
        return (self.x + self.width // 2, self.y + self.height // 2)

    def expand(self, pixels: int) -> "Rect":
        return Rect(
            self.x - pixels,
            self.y - pixels,
            self.width + pixels * 2,
            self.height + pixels * 2,
        )

    @classmethod
    def from_points(cls, points: Sequence[Sequence[float]]) -> "Rect":
        xs = [int(round(point[0])) for point in points]
        ys = [int(round(point[1])) for point in points]
        return cls(min(xs), min(ys), max(xs) - min(xs), max(ys) - min(ys))


@dataclass(frozen=True)
class OcrItem:
    text: str
    confidence: float
    box: Tuple[Point, Point, Point, Point]
    rect: Rect

    @classmethod
    def from_raw_box(cls, text: str, confidence: float, box: Sequence[Sequence[float]]) -> "OcrItem":
        points = tuple((int(round(point[0])), int(round(point[1]))) for point in box)
        if len(points) != 4:
            raise ValueError(f"OCR box must contain 4 points, got {len(points)}")
        return cls(text=text, confidence=confidence, box=points, rect=Rect.from_points(points))


def union_rect(items: Iterable[OcrItem]) -> Rect:
    item_list: List[OcrItem] = list(items)
    if not item_list:
        raise ValueError("Cannot build union rect from empty items")
    left = min(item.rect.left for item in item_list)
    top = min(item.rect.top for item in item_list)
    right = max(item.rect.right for item in item_list)
    bottom = max(item.rect.bottom for item in item_list)
    return Rect(left, top, right - left, bottom - top)
