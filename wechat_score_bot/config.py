from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

from .models import Rect


DEFAULT_CONFIG: Dict[str, Any] = {
    "name": "刘凯夫",
    "title_keywords": ["汝城县第二中学师德"],
    "pause_before_submit": True,
    "max_select_retry": 10,
    "retry_left_step_px": 4,
    # 滚动相关：大部分情况下无需配置；如果 Windows 下“只下滑一点点”，可调大 scroll_amount 或 scroll_repeats。
    # scroll_amount: PyAutoGUI 的 wheel clicks（负数=向下滚动）
    "scroll_amount": None,
    # 每次识别循环滚动几次（用于 Windows 滚动幅度太小的情况）
    "scroll_repeats": 1,
    # 滚动前是否先点一下区域中心，确保焦点在小程序内（Windows 推荐开启）
    "scroll_focus": True,
    # 滚动聚焦是否真的“点击一下”。默认 false，避免误触把已选 A 改成 C。
    "scroll_focus_click": False,
    # 滚动聚焦点（相对 screen_region 的偏移坐标）。如果不填，默认使用区域中心。
    # 例：scroll_focus_point: [380, 60]
    "scroll_focus_point": None,
    # 如果滚动后 OCR 内容没变化，是否用 PageDown 作为兜底
    "scroll_fallback_pagedown": True,
    # 翻到下一页后，先向上滚动一次（把页面拉到更靠上的位置），再开始截图/识别
    "page_turn_scroll_up": True,
    # 翻页后的向上滚动幅度（wheel clicks，正数=向上）。不填则自动推导一个偏小的值。
    "page_turn_scroll_up_amount": None,
    "screen_region": None,
}


@dataclass
class BotConfig:
    name: str
    title_keywords: List[str]
    pause_before_submit: bool = True
    max_select_retry: int = 10
    retry_left_step_px: int = 4
    scroll_amount: Optional[int] = None
    scroll_repeats: int = 1
    scroll_focus: bool = True
    scroll_focus_click: bool = False
    scroll_focus_point: Optional[List[int]] = None
    scroll_fallback_pagedown: bool = True
    page_turn_scroll_up: bool = True
    page_turn_scroll_up_amount: Optional[int] = None
    screen_region: Optional[Rect] = None


def _as_keywords(value: Any) -> List[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, list) and all(isinstance(item, str) for item in value):
        return value
    raise ValueError("title_keywords must be a string or a list of strings")


def _as_region(value: Any) -> Optional[Rect]:
    if value in (None, ""):
        return None
    if not isinstance(value, list) or len(value) != 4:
        raise ValueError("screen_region must be [x, y, width, height]")
    x, y, width, height = [int(v) for v in value]
    if width <= 0 or height <= 0:
        raise ValueError("screen_region width and height must be positive")
    return Rect(x, y, width, height)


def load_config(path: Path) -> BotConfig:
    try:
        import yaml
    except ImportError as exc:
        raise RuntimeError("PyYAML is not installed. Run: pip install -r requirements.txt") from exc

    if not path.exists():
        raw = dict(DEFAULT_CONFIG)
    else:
        with path.open("r", encoding="utf-8") as handle:
            raw = dict(DEFAULT_CONFIG)
            raw.update(yaml.safe_load(handle) or {})

    name = str(raw.get("name", "")).strip()
    if not name:
        raise ValueError("config.name is required")

    keywords = _as_keywords(raw.get("title_keywords", []))
    if not any(keyword.strip() for keyword in keywords):
        raise ValueError("config.title_keywords is required")

    return BotConfig(
        name=name,
        title_keywords=[keyword.strip() for keyword in keywords if keyword.strip()],
        pause_before_submit=bool(raw.get("pause_before_submit", True)),
        max_select_retry=int(raw.get("max_select_retry", 10)),
        retry_left_step_px=int(raw.get("retry_left_step_px", 4)),
        scroll_amount=None if raw.get("scroll_amount") in (None, "") else int(raw.get("scroll_amount")),
        scroll_repeats=max(1, int(raw.get("scroll_repeats", 1))),
        scroll_focus=bool(raw.get("scroll_focus", True)),
        scroll_focus_click=bool(raw.get("scroll_focus_click", False)),
        scroll_focus_point=raw.get("scroll_focus_point") if isinstance(raw.get("scroll_focus_point"), list) else None,
        scroll_fallback_pagedown=bool(raw.get("scroll_fallback_pagedown", True)),
        page_turn_scroll_up=bool(raw.get("page_turn_scroll_up", True)),
        page_turn_scroll_up_amount=None
        if raw.get("page_turn_scroll_up_amount") in (None, "")
        else int(raw.get("page_turn_scroll_up_amount")),
        screen_region=_as_region(raw.get("screen_region")),
    )


def save_screen_region(path: Path, region: Rect) -> None:
    try:
        import yaml
    except ImportError as exc:
        raise RuntimeError("PyYAML is not installed. Run: pip install -r requirements.txt") from exc

    raw: Dict[str, Any] = {}
    if path.exists():
        with path.open("r", encoding="utf-8") as handle:
            raw = yaml.safe_load(handle) or {}
    else:
        raw = dict(DEFAULT_CONFIG)
    raw["screen_region"] = [region.x, region.y, region.width, region.height]
    with path.open("w", encoding="utf-8") as handle:
        yaml.safe_dump(raw, handle, allow_unicode=True, sort_keys=False)
