# WeChat Score Bot

桌面微信小程序打分自动化脚本。支持 Windows/macOS，要求目标小程序首页已经由用户手动打开。脚本会点击“开始打分”，输入配置里的姓名，逐页把所有题目选择为 A，并停在最后的“提交”按钮页面，不会自动提交。

## 环境检查与安装

建议 Python 3.10+。脚本自带环境启动器，会先检查 `.venv` 和依赖；如果没有虚拟环境或缺少依赖，会自动创建并安装。

```bash
cd work/wechat_score_bot
python run.py --check-env
```

如果只想安装环境但不启动小程序流程：

```bash
python run.py --install-only
```

macOS 首次运行需要给终端或 Python 授权：

- 系统设置 -> 隐私与安全性 -> 辅助功能
- 系统设置 -> 隐私与安全性 -> 屏幕录制

## 配置

现在不创建 `config.yaml` 也可以直接运行，脚本内置默认姓名为“刘凯夫”，标题关键词为“汝城县第二中学师德”。

如果以后要临时改姓名或窗口区域，再复制并编辑 `config.yaml`。

```bash
cp config.example.yaml config.yaml
```

配置里不需要填写等待时间或滚动距离。脚本会根据 OCR 识别结果继续流程：点击后等到识别到下一阶段文字，滚动后等到识别内容发生变化，再继续找 A 选项、“下一页”或“提交”。

如果你发现页面“滚动太慢 / 只下滑一点点”（常见于 Windows），可以在 `config.yaml` 里打开滚动参数：`scroll_amount`、`scroll_repeats`，并保持 `scroll_focus: true`。

如果全屏 OCR 容易识别到其它窗口，可以先校准小程序窗口区域：

```bash
python run.py --calibrate
```

校准会弹出一张全屏截图。按住鼠标左键拖拽框选小程序区域，松开后脚本会把 `screen_region` 写入配置；按 `Esc` 可取消。

## 运行

先手动打开桌面微信里的目标小程序首页，再执行：

```bash
python run.py
```

## Windows 免安装 EXE

如果要发给别人用（对方不想装 Python），可以用 PyInstaller 构建 Windows exe 压缩包：`wechat_score_bot_windows_exe.zip`。详细步骤见 `README_windows_exe.md`。

演练模式不会点击按钮或输入文字，只会截图、OCR、打印识别结果：

```bash
python run.py --dry-run
```

## 离线截图检查

可以用已有截图检查 OCR 和定位效果：

```bash
python run.py --inspect-image /path/to/screenshot.png
```

如果你已经手动激活了虚拟环境，也可以直接运行 `python main.py ...`。日常建议使用 `python run.py ...`，它会自动补齐环境。

## 安全行为

- 不会从微信里搜索或打开小程序。
- 不会自动点击“提交”。
- A 选项点击后会检测选中态；超过重试次数仍失败会保存失败截图并停止。
- 每次运行都会写入 `logs/run-YYYYmmdd-HHMMSS/`。
