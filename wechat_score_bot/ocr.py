from __future__ import annotations

import re
from pathlib import Path
from typing import Iterable, List, Optional, Sequence

from PIL import Image

from .models import OcrItem


def normalize_text(text: str) -> str:
    replacements = {
        " ": "",
        "\n": "",
        "\t": "",
        "（": "(",
        "）": ")",
        "。": ".",
        "：": ":",
        "，": ",",
    }
    normalized = text
    for source, target in replacements.items():
        normalized = normalized.replace(source, target)
    return normalized.strip().lower()


def contains_text(text: str, keyword: str) -> bool:
    return normalize_text(keyword) in normalize_text(text)


def join_ocr_text(items: Iterable[OcrItem]) -> str:
    return "\n".join(item.text for item in items)


def is_a_option_text(text: str) -> bool:
    normalized = normalize_text(text)
    return bool(
        re.search(r"^a[.、:]?a?\(?2[.]?5分?\)?", normalized)
        or re.search(r"^a[.、:]?a", normalized)
        or normalized.startswith("a(2.5")
    )


class OcrEngine:
    def recognize(self, image: Image.Image) -> List[OcrItem]:
        raise NotImplementedError


class RapidOcrEngine(OcrEngine):
    def __init__(self) -> None:
        try:
            from rapidocr_onnxruntime import RapidOCR
        except ImportError as exc:
            raise RuntimeError(
                "rapidocr-onnxruntime is not installed. Run: pip install -r requirements.txt"
            ) from exc
        self._engine = RapidOCR()

    def recognize(self, image: Image.Image) -> List[OcrItem]:
        try:
            import numpy as np
        except ImportError as exc:
            raise RuntimeError("numpy is not installed. Run: pip install -r requirements.txt") from exc

        array = np.asarray(image.convert("RGB"))
        result = self._engine(array)
        if isinstance(result, tuple):
            raw_items = result[0] or []
        else:
            raw_items = result or []

        items: List[OcrItem] = []
        for raw in raw_items:
            if len(raw) < 3:
                continue
            box, text, confidence = raw[0], str(raw[1]), float(raw[2])
            try:
                items.append(OcrItem.from_raw_box(text, confidence, box))
            except ValueError:
                continue
        return items


def find_items_containing(items: Sequence[OcrItem], keyword: str, min_confidence: float = 0.35) -> List[OcrItem]:
    return [
        item
        for item in items
        if item.confidence >= min_confidence and contains_text(item.text, keyword)
    ]


def find_first_text(items: Sequence[OcrItem], keywords: Sequence[str]) -> Optional[OcrItem]:
    for keyword in keywords:
        matches = find_items_containing(items, keyword)
        if matches:
            return sorted(matches, key=lambda item: item.confidence, reverse=True)[0]
    return None


def load_image(path: Path) -> Image.Image:
    return Image.open(path).convert("RGB")
