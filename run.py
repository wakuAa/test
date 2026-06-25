from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple


PROJECT_ROOT = Path(__file__).resolve().parent
VENV_DIR = PROJECT_ROOT / ".venv"
REQUIREMENTS = PROJECT_ROOT / "requirements.txt"
MAIN = PROJECT_ROOT / "main.py"
MIN_PYTHON = (3, 9)
RECOMMENDED_PYTHON = (3, 10)

REQUIRED_IMPORTS = [
    "cv2",
    "numpy",
    "PIL",
    "pyautogui",
    "pyperclip",
    "rapidocr_onnxruntime",
    "yaml",
]


def venv_python() -> Path:
    if os.name == "nt":
        return VENV_DIR / "Scripts" / "python.exe"
    return VENV_DIR / "bin" / "python"


def run_command(command: Sequence[str], env: Optional[Dict[str, str]] = None) -> None:
    print("+ " + " ".join(command))
    subprocess.check_call(list(command), cwd=str(PROJECT_ROOT), env=env)


def check_current_python() -> None:
    if sys.version_info < MIN_PYTHON:
        version = ".".join(map(str, MIN_PYTHON))
        raise SystemExit(f"Python {version}+ is required. Current: {sys.version.split()[0]}")
    if sys.version_info < RECOMMENDED_PYTHON:
        recommended = ".".join(map(str, RECOMMENDED_PYTHON))
        print(f"[warn] Python {recommended}+ is recommended. Current: {sys.version.split()[0]}")


def create_venv_if_missing() -> None:
    python = venv_python()
    if python.exists():
        return
    print(f"[env] creating virtual environment: {VENV_DIR}")
    run_command([sys.executable, "-m", "venv", str(VENV_DIR)])


def install_requirements(force: bool = False) -> None:
    python = venv_python()
    if not python.exists():
        create_venv_if_missing()
    if force or not dependencies_ok(python):
        print("[env] installing/updating dependencies")
        run_command([str(python), "-m", "ensurepip", "--upgrade"])
        run_command([str(python), "-m", "pip", "install", "--upgrade", "pip"])
        run_command([str(python), "-m", "pip", "install", "-r", str(REQUIREMENTS)])
    else:
        print("[env] dependencies already installed")


def dependencies_ok(python: Path) -> bool:
    import_code = "\n".join(
        [
            "import importlib.util",
            f"mods = {REQUIRED_IMPORTS!r}",
            "missing = [m for m in mods if importlib.util.find_spec(m) is None]",
            "print('\\n'.join(missing))",
            "raise SystemExit(1 if missing else 0)",
        ]
    )
    result = subprocess.run(
        [str(python), "-c", import_code],
        cwd=str(PROJECT_ROOT),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if result.returncode == 0:
        return True
    missing = result.stdout.strip()
    if missing:
        print("[env] missing dependencies:")
        for name in missing.splitlines():
            print(f"  - {name}")
    elif result.stderr.strip():
        print(result.stderr.strip())
    return False


def forward_to_main(args: Sequence[str]) -> int:
    python = venv_python()
    env = os.environ.copy()
    env["WECHAT_SCORE_BOT_BOOTSTRAPPED"] = "1"
    process = subprocess.run([str(python), str(MAIN), *args], cwd=str(PROJECT_ROOT), env=env)
    return int(process.returncode)


def parse_args(argv: Sequence[str]) -> Tuple[argparse.Namespace, List[str]]:
    parser = argparse.ArgumentParser(
        description="Environment bootstrapper for the WeChat score bot",
        add_help=True,
    )
    parser.add_argument("--check-env", action="store_true", help="Check/create environment, then exit")
    parser.add_argument("--install-only", action="store_true", help="Install dependencies, then exit")
    parser.add_argument("--reinstall", action="store_true", help="Run pip install even if dependencies look present")
    parser.add_argument("--no-install", action="store_true", help="Do not create venv or install dependencies")
    args, remaining = parser.parse_known_args(argv)
    return args, remaining


def main(argv: Optional[Sequence[str]] = None) -> int:
    args, remaining = parse_args(argv or sys.argv[1:])
    check_current_python()

    if args.no_install:
        python = Path(sys.executable)
        if not dependencies_ok(python):
            return 1
        if args.check_env or args.install_only:
            print(f"[env] ready: {python}")
            return 0
        return subprocess.call([str(python), str(MAIN), *remaining], cwd=str(PROJECT_ROOT))

    create_venv_if_missing()
    install_requirements(force=args.reinstall)

    if args.check_env or args.install_only:
        print(f"[env] ready: {venv_python()}")
        return 0

    return forward_to_main(remaining)


if __name__ == "__main__":
    raise SystemExit(main())
