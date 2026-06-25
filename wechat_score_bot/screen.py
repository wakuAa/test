from __future__ import annotations

import time
import sys
from pathlib import Path
from typing import Optional, Tuple

from PIL import Image

from .models import Point, Rect


class Screen:
    def __init__(self, dry_run: bool = False) -> None:
        try:
            import pyautogui
        except ImportError as exc:
            raise RuntimeError("pyautogui is not installed. Run: pip install -r requirements.txt") from exc
        self._pyautogui = pyautogui
        self.dry_run = dry_run
        self._pyautogui.FAILSAFE = True

    def screenshot(self, region: Optional[Rect] = None) -> Image.Image:
        if region:
            return self._pyautogui.screenshot(region=(region.x, region.y, region.width, region.height)).convert("RGB")
        return self._pyautogui.screenshot().convert("RGB")

    def click(self, point: Point, region: Optional[Rect] = None) -> None:
        absolute = self.to_absolute(point, region)
        if self.dry_run:
            print(f"[dry-run] click {absolute}")
            return
        self._pyautogui.click(*absolute)

    def scroll(self, amount: int) -> None:
        if self.dry_run:
            print(f"[dry-run] scroll {amount}")
            return
        self._pyautogui.scroll(amount)

    def write_text(self, text: str) -> None:
        if self.dry_run:
            print(f"[dry-run] write text: {text}")
            return
        self._pyautogui.write(text, interval=0.02)

    def paste_text(self, text: str) -> None:
        if self.dry_run:
            print(f"[dry-run] paste text: {text}")
            return
        try:
            import pyperclip
        except ImportError:
            self.write_text(text)
            return
        pyperclip.copy(text)
        hotkey = ("command", "v") if sys.platform == "darwin" else ("ctrl", "v")
        self._pyautogui.hotkey(*hotkey)

    def position(self) -> Point:
        point = self._pyautogui.position()
        return (int(point.x), int(point.y))

    def sleep(self, seconds: float) -> None:
        time.sleep(seconds)

    @staticmethod
    def to_absolute(point: Point, region: Optional[Rect]) -> Point:
        if not region:
            return point
        return (point[0] + region.x, point[1] + region.y)

    @staticmethod
    def save(image: Image.Image, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        image.save(path)
