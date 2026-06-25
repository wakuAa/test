from __future__ import annotations

import argparse
import subprocess
from pathlib import Path
from typing import List, Optional

from wechat_score_bot.config import load_config, save_screen_region
from wechat_score_bot.models import Rect


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Desktop WeChat mini-program score bot")
    parser.add_argument("--config", default="config.yaml", help="Path to config YAML")
    parser.add_argument("--dry-run", action="store_true", help="Print actions without clicking/typing")
    parser.add_argument(
        "--calibrate",
        action="store_true",
        help="Drag to save mini-program screen_region into config",
    )
    parser.add_argument("--inspect-image", help="Run OCR/locator inspection on a saved screenshot")
    return parser


def select_screen_region() -> Rect:
    selector = Path(__file__).resolve().parent / "tools" / "region_selector.swift"
    if not selector.exists():
        raise FileNotFoundError(f"Missing selector tool: {selector}")

    result = subprocess.run(
        ["swift", str(selector)],
        check=False,
        text=True,
        capture_output=True,
    )
    stdout = result.stdout.strip()
    stderr = result.stderr.strip()
    if result.returncode != 0:
        details = stderr or stdout or f"swift exited with code {result.returncode}"
        raise RuntimeError(f"Region selector failed: {details}")
    if stdout == "CANCELLED":
        raise SystemExit("Calibration cancelled.")

    try:
        x_text, y_text, width_text, height_text = stdout.split(",")
        region = Rect(int(x_text), int(y_text), int(width_text), int(height_text))
    except Exception as exc:
        details = stdout or stderr or "empty output"
        raise RuntimeError(f"Unexpected selector output: {details}") from exc

    if region.width <= 0 or region.height <= 0:
        raise SystemExit("Invalid region. Please drag a larger area.")
    return region


def calibrate(config_path: Path) -> None:
    print("请在弹出的全屏截图上拖拽框选小程序区域，按 Esc 可取消。")
    region = select_screen_region()
    save_screen_region(config_path, region)
    print(f"Saved screen_region: {[region.x, region.y, region.width, region.height]}")


def inspect_image(path: Path) -> None:
    from wechat_score_bot.ocr import RapidOcrEngine, find_first_text, join_ocr_text, load_image
    from wechat_score_bot.vision import find_a_options, is_selected_near

    ocr = RapidOcrEngine()
    image = load_image(path)
    items = ocr.recognize(image)
    print("OCR text:")
    print(join_ocr_text(items))
    print()

    for label, keywords in [
        ("start", ["开始打分"]),
        ("name input", ["请输入姓名"]),
        ("claim", ["立即领取打分表", "领取打分表"]),
        ("next", ["下一页"]),
        ("submit", ["提交"]),
    ]:
        item = find_first_text(items, keywords)
        print(f"{label}: {item.rect.center if item else 'not found'}")

    a_options = find_a_options(items, image.height)
    print(f"A options: {len(a_options)}")
    for item, point in a_options:
        selected = is_selected_near(image, point)
        print(f"- text={item.text!r} text_rect={item.rect} click={point} selected={selected}")


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    config_path = Path(args.config)

    try:
        if args.calibrate:
            calibrate(config_path)
            return 0
        if args.inspect_image:
            inspect_image(Path(args.inspect_image))
            return 0

        from wechat_score_bot.bot import BotError, WeChatScoreBot
        from wechat_score_bot.ocr import RapidOcrEngine
        from wechat_score_bot.screen import Screen

        config = load_config(config_path)
        screen = Screen(dry_run=args.dry_run)
        ocr = RapidOcrEngine()
        bot = WeChatScoreBot(config=config, screen=screen, ocr=ocr)
        bot.run()
        return 0
    except (RuntimeError, ValueError, FileNotFoundError) as exc:
        print(f"[error] {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
