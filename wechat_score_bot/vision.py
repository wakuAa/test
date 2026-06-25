from __future__ import annotations

from typing import Iterable, List, Tuple

from PIL import Image

from .models import OcrItem, Point, Rect
from .ocr import is_a_option_text


def crop_rect(image: Image.Image, rect: Rect) -> Image.Image:
    left = max(0, rect.left)
    top = max(0, rect.top)
    right = min(image.width, rect.right)
    bottom = min(image.height, rect.bottom)
    return image.crop((left, top, right, bottom))


def crop_around(image: Image.Image, point: Point, radius: int = 18) -> Image.Image:
    x, y = point
    return crop_rect(image, Rect(x - radius, y - radius, radius * 2, radius * 2))


def selected_blue_ratio(image: Image.Image) -> float:
    rgb_image = image.convert("RGB")
    pixels = list(rgb_image.getdata())
    if not pixels:
        return 0.0

    # WeChat selected radios and selected A text are saturated blue. Keep the
    # condition broad enough for different desktop color profiles.
    blue_pixels = 0
    for red, green, blue in pixels:
        if blue >= 135 and green >= 80 and red <= 110 and (blue - red) >= 45:
            blue_pixels += 1
    return float(blue_pixels) / float(len(pixels))


def is_selected_near(image: Image.Image, point: Point, radius: int = 20) -> bool:
    return selected_blue_ratio(crop_around(image, point, radius)) >= 0.025


def estimate_radio_point(a_item: OcrItem) -> Point:
    text_height = max(14, a_item.rect.height)
    offset = max(22, min(46, int(text_height * 1.05)))
    return (a_item.rect.left - offset, a_item.rect.top + a_item.rect.height // 2)


def find_a_options(items: Iterable[OcrItem], viewport_height: int) -> List[Tuple[OcrItem, Point]]:
    options: List[Tuple[OcrItem, Point]] = []
    for item in items:
        if not is_a_option_text(item.text):
            continue
        if item.rect.top < 60 or item.rect.bottom > viewport_height - 20:
            continue
        point = estimate_radio_point(item)
        if point[0] < 0:
            continue
        options.append((item, point))
    return sorted(options, key=lambda pair: (pair[0].rect.top, pair[0].rect.left))
