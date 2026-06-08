"""
Kazumee Health Audit Script
Run from project root: python scripts/audit.py
"""

import subprocess
import sys
import os
import json
import importlib
import ast
from pathlib import Path

ROOT = Path(__file__).parent.parent
BACKEND = ROOT / "backend"

print("\n" + "="*60)
print("  KAZUMEE CODEBASE AUDIT")
print("="*60)

# ── 1. IMPORT CHECK ───────────────────────────────────────────
print("\n[1] CHECKING KEY MODULE IMPORTS...")

modules_to_check = [
    ("faster_whisper", "Voice transcription"),
    ("speech_recognition", "Mic capture"),
    ("obsws_python", "OBS WebSocket"),
    ("groq", "AI inference"),
    ("sqlalchemy", "Database"),
    ("fastapi", "API server"),
    ("slowapi", "Rate limiting"),
    ("resemblyzer", "Voice fingerprint"),
    ("celery", "Background tasks"),
]

working = []
missing = []

for module, description in modules_to_check:
    try:
        importlib.import_module(module)
        print(f"  ✓ {module:25} {description}")
        working.append(module)
    except ImportError:
        print(f"  ✗ {module:25} {description} — NOT INSTALLED")
        missing.append(module)

# ── 2. KEY FILE CHECK ─────────────────────────────────────────
print("\n[2] CHECKING KEY FILES EXIST...")

key_files = [
    "backend/main.py",
    "backend/commands/executor.py",
    "backend/commands/service.py",
    "backend/core/voice_agent.py",
    "backend/core/voice_fingerprint.py",
    "backend/core/irl_mode.py",
    "backend/core/irl_transcriber.py",
    "backend/core/streamer_ai_suite.py",
    "backend/api/routes/billing.py",
    "backend/api/routes/cameras.py",
    "backend/core/entitlements.py",
    "backend/core/rate_limiter.py",
    "backend/database/models/streamer_voice_embedding.py",
    "backend/database/models/streamer_camera_source.py",
]

for f in key_files:
    path = ROOT / f
    if path.exists():
        size = path.stat().st_size
        if size < 100:
            print(f"  ⚠ {f} — exists but very small ({size} bytes), may be empty stub")
        else:
            print(f"  ✓ {f}")
    else:
        print(f"  ✗ {f} — MISSING")

# ── 3. DEAD FILE DETECTION ────────────────────────────────────
print("\n[3] SCANNING FOR POTENTIALLY DEAD FILES...")

dead_patterns = [
    "__create",
    "venv311",
    ".bak",
    "_old",
    "_backup",
    "_unused",
    "test_temp",
]

dead_found = []
for pattern in dead_patterns:
    matches = list(ROOT.rglob(f"*{pattern}*"))
    matches = [m for m in matches if "node_modules" not in str(m)
               and ".git" not in str(m)
               and "venv" not in str(m).lower()
               and "__pycache__" not in str(m)]
    for m in matches:
        print(f"  ⚠ Possibly unused: {m.relative_to(ROOT)}")
        dead_found.append(str(m))

if not dead_found:
    print("  ✓ No obvious dead files found")

# ── 4. NEXT.JS REMNANT CHECK ──────────────────────────────────
print("\n[4] CHECKING FOR NEXTJS REMNANTS...")

nextjs_patterns = ["next-auth", "next/navigation", "next/link",
                   "next/image", "@auth/core", "NextAuth"]
nextjs_found = []

frontend_src = ROOT / "frontend" / "web" / "src"
if frontend_src.exists():
    for f in frontend_src.rglob("*.tsx"):
        content = f.read_text(encoding="utf-8", errors="ignore")
        for pattern in nextjs_patterns:
            if pattern in content:
                print(f"  ✗ {f.relative_to(ROOT)} still contains '{pattern}'")
                nextjs_found.append(str(f))
                break
    for f in frontend_src.rglob("*.ts"):
        content = f.read_text(encoding="utf-8", errors="ignore")
        for pattern in nextjs_patterns:
            if pattern in content:
                print(f"  ✗ {f.relative_to(ROOT)} still contains '{pattern}'")
                nextjs_found.append(str(f))
                break
    for f in frontend_src.rglob("*.jsx"):
        content = f.read_text(encoding="utf-8", errors="ignore")
        for pattern in nextjs_patterns:
            if pattern in content:
                print(f"  ✗ {f.relative_to(ROOT)} still contains '{pattern}'")
                nextjs_found.append(str(f))
                break
    for f in frontend_src.rglob("*.js"):
        content = f.read_text(encoding="utf-8", errors="ignore")
        for pattern in nextjs_patterns:
            if pattern in content:
                print(f"  ✗ {f.relative_to(ROOT)} still contains '{pattern}'")
                nextjs_found.append(str(f))
                break

if not nextjs_found:
    print("  ✓ No Next.js remnants found in frontend source")

# ── 5. HARDCODED VALUES CHECK ─────────────────────────────────
print("\n[5] CHECKING FOR HARDCODED VALUES THAT NEED FIXING...")

hardcoded_checks = [
    ("Mic/Aux", "backend", "Hardcoded mic name — needs to match your OBS source"),
    ("ALLOW_PLAINTEXT_TOKENS", "backend", "Security flag that should be removed"),
    ("localhost:8000", "frontend/web/src", "Hardcoded backend URL — should be env var"),
    ("recognize_google", "backend", "Old Google speech recognition — should be replaced"),
]

for search_term, search_dir, description in hardcoded_checks:
    search_path = ROOT / search_dir
    found_in = []
    if search_path.exists():
        for ext in ["*.py", "*.ts", "*.tsx", "*.js", "*.jsx"]:
            for f in search_path.rglob(ext):
                if "node_modules" in str(f) or "__pycache__" in str(f):
                    continue
                try:
                    content = f.read_text(encoding="utf-8", errors="ignore")
                    if search_term in content:
                        found_in.append(f.relative_to(ROOT))
                except:
                    pass
    if found_in:
        print(f"  ⚠ '{search_term}' — {description}")
        for f in found_in[:3]:
            print(f"    found in: {f}")
    else:
        print(f"  ✓ '{search_term}' — clean")

# ── 6. OBS CONNECTION TEST ────────────────────────────────────
print("\n[6] TESTING OBS CONNECTION...")
try:
    sys.path.insert(0, str(ROOT))
    from backend.commands.obs_adapter import OBSAdapter
    print("  ✓ OBS adapter imports successfully")
except Exception as e:
    print(f"  ✗ OBS adapter import failed: {e}")

# ── 7. DATABASE MODEL CHECK ───────────────────────────────────
print("\n[7] CHECKING DATABASE MODELS...")
models_dir = BACKEND / "database" / "models"
if models_dir.exists():
    models = list(models_dir.glob("*.py"))
    models = [m for m in models if m.name != "__init__.py"]
    print(f"  Found {len(models)} model files:")
    for m in sorted(models):
        size = m.stat().st_size
        status = "✓" if size > 200 else "⚠ (possibly empty)"
        print(f"  {status} {m.name} ({size} bytes)")
else:
    print("  ✗ Models directory not found")

# ── 8. REQUIREMENTS CHECK ─────────────────────────────────────
print("\n[8] CHECKING REQUIREMENTS.TXT...")
req_file = ROOT / "requirements.txt"
if req_file.exists():
    reqs = req_file.read_text().strip().split("\n")
    reqs = [r.strip() for r in reqs if r.strip() and not r.startswith("#")]
    print(f"  Found {len(reqs)} requirements")

    critical = ["faster-whisper", "groq", "fastapi", "sqlalchemy",
                "slowapi", "obsws-python"]
    for c in critical:
        found = any(c.lower() in r.lower() for r in reqs)
        status = "✓" if found else "✗ MISSING"
        print(f"  {status} {c}")
else:
    print("  ✗ requirements.txt not found")

# ── SUMMARY ───────────────────────────────────────────────────
print("\n" + "="*60)
print("  SUMMARY")
print("="*60)
print(f"\n  Missing packages:     {len(missing)}")
print(f"  Next.js remnants:     {len(nextjs_found)}")
print(f"  Dead file patterns:   {len(dead_found)}")
print(f"\n  Run 'pip install faster-whisper resemblyzer'")
print(f"  if those show as missing above.")
print("\n" + "="*60 + "\n")