from __future__ import annotations

import time
import sys
from pathlib import Path
from typing import Optional, Tuple

from PIL import Image

from .models import Point, Rect


def _enable_windows_dpi_awareness() -> None:
    """
    Windows 显示缩放（125%/150%）时，如果进程不是 DPI aware，
    截图坐标与鼠标坐标会出现倍率偏差，导致“点不准/滚不动/框选偏移”。
    这里尽量把进程设为 DPI aware，提升 pyautogui 与截图坐标一致性。
    """
    if sys.platform != "win32":
        return
    try:
        import ctypes  # noqa: WPS433 (stdlib)

        # Windows 8.1+：PER_MONITOR_AWARE = 2
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(2)
            return
        except Exception:
            pass

        # Windows 7/旧环境兜底
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass
    except Exception:
        pass


class Screen:
    def __init__(self, dry_run: bool = False) -> None:
        _enable_windows_dpi_awareness()
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

    def scroll(
        self,
        amount: int,
        region: Optional[Rect] = None,
        focus: bool = True,
        focus_point: Optional[Point] = None,
        focus_click: bool = False,
    ) -> None:
        if self.dry_run:
            print(f"[dry-run] scroll {amount}")
            return
        x: Optional[int] = None
        y: Optional[int] = None
        if region:
            if focus_point:
                x = region.x + int(focus_point[0])
                y = region.y + int(focus_point[1])
            else:
                x = region.x + region.width // 2
                y = region.y + region.height // 2
            if focus:
                # 确保滚动目标窗口/控件拥有焦点（Windows 上特别重要）
                try:
                    # 默认只移动鼠标，不点击，避免误触选项（例如把已选 A 点成 C）
                    self._pyautogui.moveTo(x, y)
                    if focus_click:
                        self._pyautogui.click(x, y)
                except Exception:
                    pass

        # pyautogui.scroll 在不同版本上参数可能不同：有的支持 (amount, x, y)，有的只支持 (amount)
        try:
            if x is not None and y is not None:
                self._pyautogui.scroll(amount, x=x, y=y)
            else:
                self._pyautogui.scroll(amount)
        except TypeError:
            if x is not None and y is not None:
                try:
                    self._pyautogui.moveTo(x, y)
                except Exception:
                    pass
            self._pyautogui.scroll(amount)

    def press(self, key: str) -> None:
        if self.dry_run:
            print(f"[dry-run] press {key}")
            return
        self._pyautogui.press(key)

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
