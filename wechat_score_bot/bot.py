from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Sequence, Tuple

from PIL import Image

from .config import BotConfig
from .models import OcrItem, Point, Rect
from .ocr import OcrEngine, contains_text, find_first_text, find_items_containing, join_ocr_text
from .screen import Screen
from .vision import crop_around, find_a_options, is_selected_near


class BotError(RuntimeError):
    pass


MAX_PAGES = 120
MAX_SCROLLS_PER_PAGE = 80
POLL_INTERVAL_SECONDS = 0.35
PAGE_CHANGE_POLLS = 24
SELECT_STATE_POLLS = 8
SCROLL_CHANGE_POLLS = 10


@dataclass
class SelectResult:
    text: str
    point: Point
    success: bool
    attempts: int


class WeChatScoreBot:
    def __init__(
        self,
        config: BotConfig,
        screen: Screen,
        ocr: OcrEngine,
        log_dir: Optional[Path] = None,
    ) -> None:
        self.config = config
        self.screen = screen
        self.ocr = ocr
        self.region = config.screen_region
        self.log_dir = log_dir or Path("logs") / f"run-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
        self.log_dir.mkdir(parents=True, exist_ok=True)

    def run(self) -> None:
        self.ensure_target_page()
        if self.screen.dry_run:
            self.preview_current_screen()
            return
        print("[mode] skipping start/claim flow; selecting A options from current screen")
        self.fill_pages()

    def preview_current_screen(self) -> None:
        image, items = self.capture_and_ocr("dry-run-preview")
        print("[dry-run] current screen OCR:")
        print(join_ocr_text(items))

        for label, keywords in [
            ("current form", ["请输入姓名", "立即领取测评表", "立即领取打分表", "领取打分表"]),
            ("next page", ["下一页"]),
            ("submit", ["提交"]),
        ]:
            item = find_first_text(items, keywords)
            print(f"[dry-run] {label}: {item.rect.center if item else 'not found'}")

        a_options = find_a_options(items, image.height)
        print(f"[dry-run] visible A options: {len(a_options)}")
        for item, point in a_options:
            print(f"[dry-run] A option {item.text!r}: click={point}, selected={is_selected_near(image, point)}")

    def ensure_target_page(self) -> None:
        image, items = self.capture_and_ocr("title-check")
        all_text = join_ocr_text(items)
        missing = [keyword for keyword in self.config.title_keywords if not contains_text(all_text, keyword)]
        if missing:
            raise BotError(
                "Target mini-program was not recognized. "
                f"Missing keywords: {missing}. OCR text was:\n{all_text}"
            )
        print("[ok] recognized target mini-program")

    def start_form(self) -> None:
        image, items = self.capture_and_ocr("home")
        button = self.find_required(items, ["开始打分"])
        self.click_and_wait_for_text(
            button.rect.center,
            "start scoring",
            [["请输入姓名"], ["立即领取打分表"], ["领取打分表"]],
        )

    def claim_form(self) -> None:
        image, items = self.capture_and_ocr("claim-form")
        input_point = self.find_name_input_point(items)
        self.screen.click(input_point, self.region)
        self.screen.sleep(POLL_INTERVAL_SECONDS)
        self.screen.paste_text(self.config.name)
        self.wait_for_screen_settle("name-input-settle")

        image, items = self.capture_and_ocr("claim-form-filled")
        button = self.find_required(items, ["立即领取打分表", "领取打分表"])
        self.click_and_wait_for_form(button.rect.center, "claim score sheet")

    def find_name_input_point(self, items: Sequence[OcrItem]) -> Point:
        matches = find_items_containing(items, "请输入姓名")
        if len(matches) >= 2:
            # The label is usually above the input placeholder; click the lower
            # match to focus the actual text field.
            return sorted(matches, key=lambda item: item.rect.top)[-1].rect.center
        if len(matches) == 1:
            item = matches[0]
            return (item.rect.left + max(80, item.rect.width // 2), item.rect.bottom + 28)

        label = self.find_required(items, ["姓名"])
        return (label.rect.left + max(80, label.rect.width // 2), label.rect.bottom + 28)

    def fill_pages(self) -> None:
        for page_index in range(1, MAX_PAGES + 1):
            print(f"[page {page_index}] selecting visible A options")
            reached_end = self.fill_current_page(page_index)
            if reached_end:
                print("[done] reached submit page. The script did not click Submit.")
                return
        raise BotError(f"Stopped after max_pages={MAX_PAGES}; page loop did not finish")

    def fill_current_page(self, page_index: int) -> bool:
        for scroll_index in range(MAX_SCROLLS_PER_PAGE):
            image, items = self.capture_and_ocr(f"page-{page_index:03d}-scroll-{scroll_index:03d}")
            results = self.select_visible_a_options(image, items, page_index, scroll_index)
            if results:
                ok_count = sum(1 for result in results if result.success)
                retry_count = sum(result.attempts - 1 for result in results)
                print(
                    f"[page {page_index}] selected {ok_count}/{len(results)} visible A options, "
                    f"extra retries={retry_count}"
                )

            nav = self.detect_navigation(items)
            if nav == "submit":
                self.capture_and_ocr(f"page-{page_index:03d}-submit-ready")
                return True
            if nav == "next":
                next_button = self.find_required(items, ["下一页"])
                self.click_and_wait_for_form(next_button.rect.center, "next page")
                self.after_page_turn(page_index)
                return False

            self.scroll_until_content_changes(image, items, page_index, scroll_index)

        raise BotError(
            f"Could not find Next or Submit after {MAX_SCROLLS_PER_PAGE} scrolls on page {page_index}"
        )

    def select_visible_a_options(
        self,
        image: Image.Image,
        items: Sequence[OcrItem],
        page_index: int,
        scroll_index: int,
    ) -> List[SelectResult]:
        results: List[SelectResult] = []
        for item, point in find_a_options(items, image.height):
            if is_selected_near(image, point):
                continue
            success, attempts, final_point = self.try_select(point, item.text)
            results.append(SelectResult(item.text, final_point, success, attempts))
            if not success:
                failed_image = self.screen.screenshot(self.region)
                self.screen.save(
                    failed_image,
                    self.log_dir / f"failed-page-{page_index:03d}-scroll-{scroll_index:03d}.png",
                )
                raise BotError(
                    f"Failed to select A option after {attempts} attempts: {item.text!r} at {final_point}"
                )
        return results

    def try_select(self, point: Point, label: str) -> Tuple[bool, int, Point]:
        for attempt in range(1, self.config.max_select_retry + 1):
            candidate = (point[0] - (attempt - 1) * self.config.retry_left_step_px, point[1])
            self.screen.click(candidate, self.region)
            image = self.wait_until_selected(candidate)
            if image:
                safe_label = "".join(ch if ch.isalnum() else "_" for ch in label[:16]).strip("_") or "option"
                self.screen.save(
                    crop_around(image, candidate, 24),
                    self.log_dir / "selected-crops" / f"{safe_label}-{attempt}.png",
                )
                return True, attempt, candidate
        return False, self.config.max_select_retry, candidate

    def detect_navigation(self, items: Sequence[OcrItem]) -> Optional[str]:
        if find_first_text(items, ["提交"]):
            return "submit"
        if find_first_text(items, ["下一页"]):
            return "next"
        return None

    def capture_and_ocr(self, name: str) -> Tuple[Image.Image, List[OcrItem]]:
        image = self.screen.screenshot(self.region)
        self.screen.save(image, self.log_dir / f"{name}.png")
        items = self.ocr.recognize(image)
        with (self.log_dir / f"{name}.ocr.txt").open("w", encoding="utf-8") as handle:
            for item in items:
                handle.write(f"{item.confidence:.3f}\t{item.rect}\t{item.text}\n")
        return image, items

    def find_required(self, items: Sequence[OcrItem], keywords: Sequence[str]) -> OcrItem:
        found = find_first_text(items, keywords)
        if not found:
            raise BotError(f"Could not find any of {keywords}. OCR text was:\n{join_ocr_text(items)}")
        return found

    def click_and_wait_for_text(self, point: Point, label: str, keyword_groups: Sequence[Sequence[str]]) -> None:
        print(f"[action] {label}: {point}")
        self.screen.click(point, self.region)
        self.wait_for_text(keyword_groups, label)

    def click_and_wait_for_form(self, point: Point, label: str) -> None:
        print(f"[action] {label}: {point}")
        before_image = self.screen.screenshot(self.region)
        before_signature = self.image_signature(before_image)
        self.screen.click(point, self.region)
        for poll_index in range(PAGE_CHANGE_POLLS):
            self.screen.sleep(POLL_INTERVAL_SECONDS)
            image, items = self.capture_and_ocr(f"wait-{label.replace(' ', '-')}-{poll_index:02d}")
            if self.image_signature(image) != before_signature:
                if find_a_options(items, image.height) or self.detect_navigation(items):
                    return
        raise BotError(f"Timed out waiting for form content after action: {label}")

    def after_page_turn(self, page_index: int) -> None:
        """
        点击“下一页”并检测到页面刷新后做一次收尾动作：
        先轻微向上滚动一次，再截图/识别，避免停在页面中部导致漏题或识别混乱。
        """
        if not self.config.page_turn_scroll_up:
            return
        image = self.screen.screenshot(self.region)
        amount = self.page_turn_scroll_up_amount_for(image)
        if amount <= 0:
            return
        print(f"[page {page_index}] after page turn: scroll up once (amount={amount})")
        self.screen.scroll(
            amount,
            region=self.region,
            focus=self.config.scroll_focus,
            focus_point=self.scroll_focus_point(),
            focus_click=False,
        )
        # 截图/识别一次作为新的起点
        self.screen.sleep(POLL_INTERVAL_SECONDS)
        self.capture_and_ocr(f"page-{page_index:03d}-after-next-page")

    def wait_for_text(self, keyword_groups: Sequence[Sequence[str]], label: str) -> None:
        for poll_index in range(PAGE_CHANGE_POLLS):
            self.screen.sleep(POLL_INTERVAL_SECONDS)
            image, items = self.capture_and_ocr(f"wait-{label.replace(' ', '-')}-{poll_index:02d}")
            for keywords in keyword_groups:
                if find_first_text(items, keywords):
                    return
        raise BotError(f"Timed out waiting for OCR text after action: {label}")

    def wait_until_selected(self, point: Point) -> Optional[Image.Image]:
        for _ in range(SELECT_STATE_POLLS):
            self.screen.sleep(POLL_INTERVAL_SECONDS)
            image = self.screen.screenshot(self.region)
            if is_selected_near(image, point):
                return image
        return None

    def wait_for_screen_settle(self, label: str) -> None:
        previous = self.screen.screenshot(self.region)
        previous_signature = self.image_signature(previous)
        for poll_index in range(PAGE_CHANGE_POLLS):
            self.screen.sleep(POLL_INTERVAL_SECONDS)
            current = self.screen.screenshot(self.region)
            current_signature = self.image_signature(current)
            if current_signature == previous_signature:
                return
            previous_signature = current_signature
            self.screen.save(current, self.log_dir / f"wait-{label}-{poll_index:02d}.png")

    def scroll_until_content_changes(
        self,
        image: Image.Image,
        items: Sequence[OcrItem],
        page_index: int,
        scroll_index: int,
    ) -> None:
        before_signature = self.ocr_signature(items)
        scroll_amount = self.scroll_amount_for(image)
        print(
            f"[page {page_index}] scrolling to find more content (amount={scroll_amount}, repeats={self.config.scroll_repeats})"
        )

        for repeat_index in range(max(1, self.config.scroll_repeats)):
            self.screen.scroll(
                scroll_amount,
                region=self.region,
                focus=self.config.scroll_focus,
                focus_point=self.scroll_focus_point(),
                focus_click=self.config.scroll_focus_click,
            )
            for poll_index in range(SCROLL_CHANGE_POLLS):
                self.screen.sleep(POLL_INTERVAL_SECONDS)
                new_image, new_items = self.capture_and_ocr(
                    f"page-{page_index:03d}-scroll-{scroll_index:03d}-r{repeat_index}-wait-{poll_index:02d}"
                )
                # 目标：滚动到“出现未勾选题目”或“出现下一页/提交”。
                # 1) 一旦出现导航按钮，立刻返回给主循环处理点击/停止
                if self.detect_navigation(new_items):
                    return
                # 2) 一旦出现新的未勾选 A 选项，立刻返回给主循环去点击
                if self.has_unselected_a_option(new_image, new_items):
                    return
                # 3) 内容发生变化也返回（避免过度滚动跳题）
                if self.ocr_signature(new_items) != before_signature:
                    return

        # 如果滚动后页面内容无变化，通常是“焦点不在小程序里”或“滚动幅度太小”。
        # 这里用 PageDown 做一次兜底（比 wheel 更稳定），但只做一次，避免跳过题目。
        if self.config.scroll_fallback_pagedown:
            print(f"[page {page_index}] wheel scroll did not change OCR; trying PageDown fallback once")
            if self.region and self.config.scroll_focus:
                # 默认只 moveTo 不 click（避免误触）
                try:
                    focus = self.scroll_focus_point()
                    if focus:
                        self.screen.scroll(0, region=self.region, focus=True, focus_point=focus, focus_click=False)
                except Exception:
                    pass
            self.screen.press("pagedown")
            for poll_index in range(SCROLL_CHANGE_POLLS):
                self.screen.sleep(POLL_INTERVAL_SECONDS)
                new_image, new_items = self.capture_and_ocr(
                    f"page-{page_index:03d}-scroll-{scroll_index:03d}-pagedown-wait-{poll_index:02d}"
                )
                if self.detect_navigation(new_items):
                    return
                if self.has_unselected_a_option(new_image, new_items):
                    return
                if self.ocr_signature(new_items) != before_signature:
                    return

        print(f"[page {page_index}] scroll did not visibly change OCR content; continuing recognition loop")

    def has_unselected_a_option(self, image: Image.Image, items: Sequence[OcrItem]) -> bool:
        for _, point in find_a_options(items, image.height):
            if not is_selected_near(image, point):
                return True
        return False

    def scroll_focus_point(self) -> Optional[Point]:
        """
        返回用于滚动聚焦的区域内相对坐标点 (x, y)。
        为了减少误触选项，默认选在“区域右侧边缘偏内”的位置，而不是正中心。
        """
        if not self.region:
            return None
        if self.config.scroll_focus_point and len(self.config.scroll_focus_point) == 2:
            try:
                x = int(self.config.scroll_focus_point[0])
                y = int(self.config.scroll_focus_point[1])
                return (x, y)
            except Exception:
                pass
        # 默认：靠右的中上位置（通常比中心更不容易压到选项圈）
        x = max(10, self.region.width - 15)
        y = max(10, min(self.region.height - 10, self.region.height // 3))
        return (x, y)

    def scroll_amount_for(self, image: Image.Image) -> int:
        # 如果用户在配置里显式指定滚动幅度，则优先使用（Windows 下常需要调大）。
        if self.config.scroll_amount is not None:
            return int(self.config.scroll_amount)
        # PyAutoGUI scroll uses wheel units rather than pixels. This derives a
        # page-sized wheel movement from the actual screenshot height, so users
        # do not need to tune a scroll distance.
        # 旧公式在部分 Windows 机器上滚动太小，因此把默认滚动幅度整体调大一些。
        # 经验值：image.height 约 700~1000 时，wheel clicks 取 18~25 比较合适。
        base = max(18, min(36, image.height // 40))
        return -int(base)

    def page_turn_scroll_up_amount_for(self, image: Image.Image) -> int:
        if self.config.page_turn_scroll_up_amount is not None:
            return int(self.config.page_turn_scroll_up_amount)
        # 默认给一个“偏小的向上回拉”，避免把页面拉回上一页或拉太多导致视觉跳动
        down = abs(self.scroll_amount_for(image))
        return max(12, min(60, down // 4))

    @staticmethod
    def ocr_signature(items: Sequence[OcrItem]) -> Tuple[Tuple[str, int], ...]:
        return tuple((item.text, item.rect.top) for item in items[:12])

    @staticmethod
    def image_signature(image: Image.Image) -> Tuple[int, int, bytes]:
        small = image.convert("L").resize((24, 24))
        return (image.width, image.height, small.tobytes())
