#!/usr/bin/env python
"""
Screen Time Tracker Build Script
Usage: python build/build.py [exe|installer|all]
"""

import os
import sys
import shutil
import subprocess
from pathlib import Path

# Project root directory
PROJECT_ROOT = Path(__file__).parent.parent
BUILD_DIR = PROJECT_ROOT / "build"
DIST_DIR = PROJECT_ROOT / "dist"
SPEC_FILE = BUILD_DIR / "screen_time_tracker.spec"
ISS_FILE = BUILD_DIR / "setup.iss"
EXE_NAME = "ScreenTimeTracker.exe"
SETUP_NAME = "ScreenTimeTracker_Setup.exe"


def clean():
    """Remove build artifacts"""
    print("Cleaning build artifacts...")

    dirs_to_remove = [
        PROJECT_ROOT / "build" / "__pycache__",
        PROJECT_ROOT / "build" / "ScreenTimeTracker",
        DIST_DIR,
    ]

    for d in dirs_to_remove:
        if d.exists():
            shutil.rmtree(d)
            print(f"  Removed: {d}")

    # Remove spec temp files
    for f in BUILD_DIR.glob("*.pyc"):
        f.unlink()

    print("Clean complete.\n")


def build_exe():
    """Build standalone executable using PyInstaller"""
    print("Building executable with PyInstaller...")

    # Ensure dist directory exists
    DIST_DIR.mkdir(parents=True, exist_ok=True)

    # Run PyInstaller
    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--clean",
        "--noconfirm",
        str(SPEC_FILE),
    ]

    result = subprocess.run(cmd, cwd=PROJECT_ROOT)

    if result.returncode != 0:
        print(f"ERROR: PyInstaller failed with code {result.returncode}")
        sys.exit(1)

    exe_path = DIST_DIR / EXE_NAME
    if exe_path.exists():
        size_mb = exe_path.stat().st_size / (1024 * 1024)
        print(f"SUCCESS: {exe_path}")
        print(f"  Size: {size_mb:.1f} MB")
        return True
    else:
        print(f"ERROR: Executable not found at {exe_path}")
        sys.exit(1)


def build_installer():
    """Build setup installer using Inno Setup"""
    print("\nBuilding installer with Inno Setup...")

    # Check if EXE exists
    exe_path = DIST_DIR / EXE_NAME
    if not exe_path.exists():
        print("ERROR: Executable not found. Run 'build exe' first.")
        sys.exit(1)

    # Find Inno Setup compiler
    iscc_paths = [
        Path(os.environ.get("ProgramFiles(x86)", "C:\\Program Files (x86)")) / "Inno Setup 6" / "ISCC.exe",
        Path(os.environ.get("ProgramFiles", "C:\\Program Files")) / "Inno Setup 6" / "ISCC.exe",
        Path("C:\\Program Files (x86)\\Inno Setup 6\\ISCC.exe"),
        Path("C:\\Program Files\\Inno Setup 6\\ISCC.exe"),
        Path("D:\\Inno Setup 6\\ISCC.exe"),
    ]

    iscc = None
    for path in iscc_paths:
        if path.exists():
            iscc = path
            break

    if not iscc:
        print("ERROR: Inno Setup not found!")
        print("Please download and install from: https://jrsoftware.org/isinfo.php")
        print("After installation, the EXE is ready at:")
        print(f"  {exe_path}")
        sys.exit(1)

    print(f"Using Inno Setup: {iscc}")

    # Run Inno Setup
    cmd = [str(iscc), str(ISS_FILE)]
    result = subprocess.run(cmd, cwd=PROJECT_ROOT)

    if result.returncode != 0:
        print(f"ERROR: Inno Setup failed with code {result.returncode}")
        sys.exit(1)

    setup_path = DIST_DIR / SETUP_NAME
    if setup_path.exists():
        size_mb = setup_path.stat().st_size / (1024 * 1024)
        print(f"SUCCESS: {setup_path}")
        print(f"  Size: {size_mb:.1f} MB")
        return True
    else:
        print(f"ERROR: Installer not found at {setup_path}")
        sys.exit(1)


def main():
    """Main build entry point"""
    if len(sys.argv) < 2:
        print(__doc__)
        print("\nAvailable commands:")
        print("  python build/build.py exe       - Build executable only")
        print("  python build/build.py installer - Build installer (requires exe first)")
        print("  python build/build.py all       - Build everything")
        print("  python build/build.py clean     - Remove build artifacts")
        sys.exit(1)

    command = sys.argv[1].lower()

    if command == "clean":
        clean()
    elif command == "exe":
        clean()
        build_exe()
    elif command == "installer":
        build_installer()
    elif command == "all":
        clean()
        build_exe()
        build_installer()
        print("\n" + "=" * 50)
        print("BUILD COMPLETE!")
        print("=" * 50)
        print(f"Executable: {DIST_DIR / EXE_NAME}")
        print(f"Installer:  {DIST_DIR / SETUP_NAME}")
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)


if __name__ == "__main__":
    main()
