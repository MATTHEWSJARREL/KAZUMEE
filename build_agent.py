#!/usr/bin/env python3
"""
Build script for Kazumee Agent executable using PyInstaller.

Usage:
    python build_agent.py

Creates: dist/kazumee-agent.exe (Windows) or dist/kazumee-agent (Mac/Linux)
"""

import subprocess
import sys
import os

def build():
    """Build the agent into a standalone executable."""

    print("\n" + "=" * 60)
    print("  BUILDING KAZUMEE AGENT")
    print("=" * 60 + "\n")

    # Check if PyInstaller is installed
    try:
        import PyInstaller
    except ImportError:
        print("[FAIL] PyInstaller not installed.")
        print("  pip install pyinstaller")
        sys.exit(1)

    # PyInstaller command
    cmd = [
        "pyinstaller",
        "--onedir",                            # Directory with all files (more reliable)
        "--windowed",                          # No console window (for tray)
        "--icon=kazumee.ico" if os.path.exists("kazumee.ico") else None,
        "--name=KazumeeAgent",                 # Output name
        "--add-data=kazumee-agent.py:.",       # Include script
        "kazumee-agent.py"
    ]

    # Remove None values
    cmd = [c for c in cmd if c]

    print("[INFO] Running PyInstaller...")
    print(f"[INFO] Command: {' '.join(cmd)}\n")

    try:
        result = subprocess.run(cmd, check=True)

        exe_path = "dist/KazumeeAgent/KazumeeAgent.exe" if sys.platform == "win32" else "dist/KazumeeAgent/KazumeeAgent"
        if os.path.exists(exe_path):
            print("\n" + "=" * 60)
            print("[SUCCESS] BUILD SUCCESSFUL")
            print("=" * 60)
            print(f"\nExecutable: {exe_path}")
            print(f"Size: {os.path.getsize(exe_path) / 1024 / 1024:.1f} MB")
            print("\nNext steps:")
            print("1. Test locally: python kazumee-agent.py")
            print(f"2. Or run: {exe_path}")
            print("3. Create .zip of dist/KazumeeAgent/ folder")
            print("4. Upload to GitHub releases")
            return 0
        else:
            print("[FAIL] Executable not found at {exe_path}")
            return 1

    except subprocess.CalledProcessError as e:
        print(f"\n[FAIL] Build failed with error code {e.returncode}")
        return 1
    except Exception as e:
        print(f"\n[FAIL] Build error: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(build())
