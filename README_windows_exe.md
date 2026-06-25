# Windows 免安装 EXE 包

这个版本用于“发给别人用”，对方不需要安装 Python。你只需要把构建出来的压缩包发给对方，对方解压后双击 `run_windows.bat` 即可。

## 对方如何使用（最终用户）

1. 解压你发过去的 `wechat_score_bot_windows_exe.zip`
2. 手动打开 Windows 桌面微信，进入目标小程序页面（保持在前台）
3. 双击 `run_windows.bat`
4. 弹出黑色半透明遮罩后，用鼠标拖拽框选小程序区域
5. 程序会自动开始执行

出错时，把同目录下的：

- `run_windows.log`
- 运行后新生成的 `logs` 文件夹

一起打包发回即可。

## 你如何构建（开发者）

你需要一台 Windows 机器（本地电脑 / 虚拟机 / 朋友电脑也行）来构建 exe。

1. 安装 Python 3.10+（建议 python.org 官方版）
2. 打开 PowerShell，进入项目根目录
3. 执行：

```powershell
powershell -ExecutionPolicy Bypass -File .\tools\windows_exe\build_exe.ps1
```

成功后会在项目根目录生成：

- `wechat_score_bot_windows_exe.zip`（把它发给别人用）

### 更省事：让脚本自动装 Python 3.10（可选）

如果你的 Windows 自带 `winget`（Windows 10/11 通常都有），脚本会在检测不到 Python 3.10 时尝试自动安装。
如果自动安装失败，会自动打开 Python 官方下载页，你手动装一次后再重新运行即可。

## 常见问题

- 首次启动会比较慢：因为 OCR / opencv / onnxruntime 依赖比较大，exe 包体积也会大（这是正常的）。
- 如果在某些机器上启动闪退：通常是杀毒/安全软件拦截或缺少系统运行库；把 `run_windows.log` 发我我再定位。
