#!/usr/bin/env python3
"""
install_deps.py - Install required Python packages for image-processor skill

Usage:
    python install_deps.py [--full]

    --full  Also install optional packages (opencv, rembg, requests)
"""

import subprocess
import sys

PYTHON = sys.executable

CORE_PACKAGES = [
    "Pillow",
    "numpy",
]

OPTIONAL_PACKAGES = [
    "opencv-python",   # Advanced filters (blur, vignette, noise)
    "rembg",           # Local AI background removal
    "requests",        # RemoveBG API support
]


def pip_install(packages: list):
    for pkg in packages:
        print(f"Installing {pkg}...")
        result = subprocess.run(
            [PYTHON, "-m", "pip", "install", pkg, "--quiet"],
            capture_output=True, text=True
        )
        if result.returncode == 0:
            print(f"  [OK] {pkg}")
        else:
            print(f"  [FAIL] {pkg}: {result.stderr.strip()}")


def main():
    full = '--full' in sys.argv
    print("=== Installing core packages ===")
    pip_install(CORE_PACKAGES)
    if full:
        print("\n=== Installing optional packages ===")
        pip_install(OPTIONAL_PACKAGES)
        print("\nNote: 'rembg' will download AI model on first use (~100MB)")
    else:
        print("\nFor full functionality (AI bg removal, advanced filters):")
        print(f"  {PYTHON} install_deps.py --full")


if __name__ == '__main__':
    main()
