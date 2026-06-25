#!/usr/bin/env python3
from __future__ import annotations

def _enable_windows_dpi_awareness() -> None:
    # 必须尽早调用：在 tkinter/pyautogui 等模块初始化前设置，才能避免 125% 缩放带来的坐标偏差。
    try:
        import sys

        if sys.platform != "win32":
            return
        import ctypes

        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(2)  # per-monitor DPI aware
            return
        except Exception:
            pass
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass
    except Exception:
        pass


_enable_windows_dpi_awareness()

import sys
import tempfile
import textwrap
from pathlib import Path

NAME = "刘凯夫"
TITLE_KEYWORDS = ["汝城县第二中学师德"]
PAUSE_BEFORE_SUBMIT = True
MAX_SELECT_RETRY = 10
RETRY_LEFT_STEP_PX = 4

# 滚动基础幅度（wheel clicks，负数=向下）。实际幅度 = 基础幅度 * 倍率
BASE_SCROLL_AMOUNT = -24
DEFAULT_SCROLL_MULTIPLIER = 10
SCROLL_REPEATS = 1
SCROLL_FOCUS = True
# 默认不点击聚焦，避免误触选项（例如把已选 A 改成 C）
SCROLL_FOCUS_CLICK = False
SCROLL_FALLBACK_PAGEDOWN = True
PAGE_TURN_SCROLL_UP = True

PROJECT_ROOT = Path(__file__).resolve().parent


def select_screen_region() -> tuple[int, int, int, int]:
    """
    Windows 用 tkinter 画全屏遮罩，鼠标拖拽框选小程序区域。
    返回 (left, top, width, height)，坐标为屏幕绝对坐标。
    """
    try:
        import tkinter as tk
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError("当前 Python 缺少 tkinter，建议安装 Python 官方版后重试。") from exc

    root = tk.Tk()
    root.withdraw()
    root.update_idletasks()

    screen_x = root.winfo_vrootx()
    screen_y = root.winfo_vrooty()
    screen_width = root.winfo_vrootwidth()
    screen_height = root.winfo_vrootheight()

    overlay = tk.Toplevel(root)
    overlay.overrideredirect(True)
    overlay.geometry(f"{screen_width}x{screen_height}+{screen_x}+{screen_y}")
    overlay.attributes("-topmost", True)
    try:
        overlay.attributes("-alpha", 0.30)
    except tk.TclError:
        # 部分系统不支持 alpha，忽略即可
        pass
    overlay.configure(bg="black", cursor="crosshair")

    canvas = tk.Canvas(
        overlay,
        width=screen_width,
        height=screen_height,
        highlightthickness=0,
        bg="black",
    )
    canvas.pack(fill="both", expand=True)
    canvas.create_text(
        24,
        24,
        anchor="nw",
        text="按住鼠标左键拖拽框选微信小程序区域，松开后自动开始执行；按 Esc 取消。",
        fill="white",
        font=("Microsoft YaHei UI", 16, "bold"),
    )

    state: dict[str, object] = {"start": None, "rect_id": None, "region": None}

    def on_press(event: tk.Event) -> None:
        state["start"] = (event.x_root, event.y_root)
        if state["rect_id"] is not None:
            canvas.delete(state["rect_id"])
        start_x = event.x_root - screen_x
        start_y = event.y_root - screen_y
        state["rect_id"] = canvas.create_rectangle(
            start_x,
            start_y,
            start_x,
            start_y,
            outline="#00d1ff",
            width=3,
            fill="#00d1ff",
            stipple="gray25",
        )

    def on_drag(event: tk.Event) -> None:
        start = state["start"]
        rect_id = state["rect_id"]
        if start is None or rect_id is None:
            return
        sx, sy = start  # type: ignore[misc]
        canvas.coords(
            rect_id,  # type: ignore[arg-type]
            sx - screen_x,
            sy - screen_y,
            event.x_root - screen_x,
            event.y_root - screen_y,
        )

    def finish(region: tuple[int, int, int, int] | None) -> None:
        state["region"] = region
        root.quit()
        overlay.destroy()

    def on_release(event: tk.Event) -> None:
        start = state["start"]
        if start is None:
            return
        sx, sy = start  # type: ignore[misc]
        left = min(sx, event.x_root)
        top = min(sy, event.y_root)
        width = abs(event.x_root - sx)
        height = abs(event.y_root - sy)
        if width < 5 or height < 5:
            finish(None)
            return
        finish((left, top, width, height))

    def on_cancel(_: tk.Event) -> None:
        finish(None)

    canvas.bind("<ButtonPress-1>", on_press)
    canvas.bind("<B1-Motion>", on_drag)
    canvas.bind("<ButtonRelease-1>", on_release)
    overlay.bind("<Escape>", on_cancel)
    overlay.focus_force()
    overlay.grab_set()
    root.mainloop()
    root.destroy()

    region = state["region"]
    if region is None:
        raise SystemExit("已取消框选。")
    return region  # type: ignore[return-value]


def prompt_scroll_multiplier(default_value: int = DEFAULT_SCROLL_MULTIPLIER) -> int:
    """
    让用户在框选后输入滚动倍率。倍率越大，滚动越快。
    默认使用当前基础幅度的 10 倍（用户提出的诉求）。
    """
    try:
        text = input(f"请输入滚动倍率（回车默认 {default_value}，建议 5~30）：").strip()
    except EOFError:
        text = ""
    if not text:
        return default_value
    try:
        value = int(text)
    except ValueError:
        print("[warn] 输入不是整数，将使用默认倍率。")
        return default_value
    if value <= 0:
        print("[warn] 倍率必须为正数，将使用默认倍率。")
        return default_value
    return value


def build_config_text(region: tuple[int, int, int, int], scroll_amount: int) -> str:
    keywords = "\n".join(f'  - "{keyword}"' for keyword in TITLE_KEYWORDS)
    return textwrap.dedent(
        f"""\
        name: "{NAME}"
        title_keywords:
        {keywords}
        pause_before_submit: {"true" if PAUSE_BEFORE_SUBMIT else "false"}
        max_select_retry: {MAX_SELECT_RETRY}
        retry_left_step_px: {RETRY_LEFT_STEP_PX}
        scroll_amount: {scroll_amount}
        scroll_repeats: {SCROLL_REPEATS}
        scroll_focus: {"true" if SCROLL_FOCUS else "false"}
        scroll_focus_click: {"true" if SCROLL_FOCUS_CLICK else "false"}
        scroll_fallback_pagedown: {"true" if SCROLL_FALLBACK_PAGEDOWN else "false"}
        page_turn_scroll_up: {"true" if PAGE_TURN_SCROLL_UP else "false"}
        screen_region: [{region[0]}, {region[1]}, {region[2]}, {region[3]}]
        """
    )


def write_runtime_config(region: tuple[int, int, int, int], scroll_amount: int) -> Path:
    with tempfile.NamedTemporaryFile(
        mode="w",
        suffix=".yaml",
        prefix="wechat-score-bot-",
        dir=PROJECT_ROOT,
        delete=False,
        encoding="utf-8",
    ) as handle:
        handle.write(build_config_text(region, scroll_amount))
        return Path(handle.name)


def main() -> int:
    print("请把目标微信小程序放到前台，然后在弹出的遮罩上拖拽框选。")
    region = select_screen_region()
    print(f"[ok] selected screen_region: {list(region)}")

    multiplier = prompt_scroll_multiplier()
    scroll_amount = int(BASE_SCROLL_AMOUNT * multiplier)
    print(f"[ok] scroll_amount={scroll_amount} (base={BASE_SCROLL_AMOUNT} * multiplier={multiplier})")

    config_path = write_runtime_config(region, scroll_amount)
    print(f"[ok] generated runtime config: {config_path}")

    # 直接调用 main.py 的入口（exe 环境也能工作），避免再起子进程找 run.py/venv。
    from main import main as app_main

    argv = ["--config", str(config_path), *sys.argv[1:]]
    return int(app_main(argv))


if __name__ == "__main__":
    raise SystemExit(main())
