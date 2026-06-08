#!/usr/bin/env python3
"""
Kazumi end-to-end local smoke test.

Runs one streamer flow + one viewer flow against a running backend.
Usage:
  python scripts/smoke_e2e.py --base-url http://127.0.0.1:8000
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any
from uuid import uuid4


@dataclass
class CheckResult:
    name: str
    ok: bool
    status: int | None = None
    detail: str = ""


def _request_json(
    *,
    base_url: str,
    method: str,
    path: str,
    token: str | None = None,
    streamer_id: int | None = None,
    payload: dict[str, Any] | None = None,
    timeout: int = 20,
) -> tuple[int, Any]:
    url = f"{base_url.rstrip('/')}{path}"
    data: bytes | None = None
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    if streamer_id is not None:
        headers["X-Streamer-Id"] = str(streamer_id)
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url=url, method=method.upper(), data=data, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode("utf-8")
            try:
                parsed = json.loads(body) if body else {}
            except json.JSONDecodeError:
                parsed = {"raw": body}
            return int(resp.status), parsed
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8") if exc.fp else ""
        try:
            parsed = json.loads(body) if body else {}
        except json.JSONDecodeError:
            parsed = {"raw": body}
        return int(exc.code), parsed
    except urllib.error.URLError as exc:
        return 0, {"error": str(exc.reason or exc)}


def _expect_status(
    results: list[CheckResult],
    name: str,
    status: int,
    expected: tuple[int, ...],
    detail: str = "",
) -> bool:
    ok = status in expected
    results.append(CheckResult(name=name, ok=ok, status=status, detail=detail))
    return ok


def run_smoke(base_url: str) -> int:
    results: list[CheckResult] = []
    seed = uuid4().hex[:8]
    streamer_email = f"smoke.streamer.{seed}@example.com"
    viewer_email = f"smoke.viewer.{seed}@example.com"
    password = f"Kazumi!{seed}"

    # 1) Health check
    status, health = _request_json(base_url=base_url, method="GET", path="/api/health")
    if not _expect_status(results, "health", status, (200,), str(health)):
        return _finalize(results)

    # 2) Streamer register/login
    status, reg_streamer = _request_json(
        base_url=base_url,
        method="POST",
        path="/auth/register",
        payload={"email": streamer_email, "password": password, "role": "streamer"},
    )
    _expect_status(results, "register_streamer", status, (200,), str(reg_streamer))
    if status != 200:
        return _finalize(results)

    streamer_token = reg_streamer.get("token")
    streamer_id = reg_streamer.get("streamer_id")
    if not streamer_token or not streamer_id:
        results.append(CheckResult("streamer_token", False, detail="Missing token or streamer_id"))
        return _finalize(results)
    results.append(CheckResult("streamer_token", True, detail=f"streamer_id={streamer_id}"))

    # 3) Streamer endpoints
    status, dashboard = _request_json(
        base_url=base_url,
        method="GET",
        path="/api/dashboard",
        token=streamer_token,
        streamer_id=int(streamer_id),
    )
    _expect_status(results, "streamer_dashboard", status, (200,), str(dashboard))

    status, ml_data = _request_json(
        base_url=base_url,
        method="GET",
        path="/api/ml-training",
        token=streamer_token,
        streamer_id=int(streamer_id),
    )
    _expect_status(results, "ml_training_get", status, (200,), str(ml_data))

    status, ml_train = _request_json(
        base_url=base_url,
        method="POST",
        path="/api/ml-training",
        token=streamer_token,
        streamer_id=int(streamer_id),
        payload={"action": "train"},
    )
    _expect_status(results, "ml_training_post", status, (200,), str(ml_train))

    # 4) Viewer register/login and bind to streamer
    status, reg_viewer = _request_json(
        base_url=base_url,
        method="POST",
        path="/auth/register",
        payload={"email": viewer_email, "password": password, "role": "viewer"},
    )
    _expect_status(results, "register_viewer", status, (200,), str(reg_viewer))
    if status != 200:
        return _finalize(results)

    viewer_token = reg_viewer.get("token")
    if not viewer_token:
        results.append(CheckResult("viewer_token", False, detail="Missing token"))
        return _finalize(results)
    results.append(CheckResult("viewer_token", True))

    status, set_active = _request_json(
        base_url=base_url,
        method="POST",
        path="/auth/active-streamer",
        token=viewer_token,
        payload={"streamer_id": int(streamer_id)},
    )
    _expect_status(results, "viewer_set_active_streamer", status, (200,), str(set_active))

    status, viewer_dash = _request_json(
        base_url=base_url,
        method="GET",
        path="/api/viewer/dashboard",
        token=viewer_token,
        streamer_id=int(streamer_id),
    )
    _expect_status(results, "viewer_dashboard", status, (200,), str(viewer_dash))

    status, vibe = _request_json(
        base_url=base_url,
        method="GET",
        path="/api/viewer/vibe-matcher/recommendations?mood=chill&limit=3",
        token=viewer_token,
        streamer_id=int(streamer_id),
    )
    _expect_status(results, "viewer_vibe_matcher", status, (200,), str(vibe))

    status, stream_token_resp = _request_json(
        base_url=base_url,
        method="POST",
        path="/auth/stream-token",
        token=viewer_token,
        streamer_id=int(streamer_id),
        payload={"streamer_id": int(streamer_id), "ttl_seconds": 120},
    )
    _expect_status(results, "viewer_stream_token", status, (200,), str(stream_token_resp))

    # 5) Quick backend stability probe
    time.sleep(0.6)
    status, health_again = _request_json(base_url=base_url, method="GET", path="/api/health")
    _expect_status(results, "health_after_flow", status, (200,), str(health_again))

    return _finalize(results)


def _finalize(results: list[CheckResult]) -> int:
    print("\nKazumi Smoke Test Results")
    print("=" * 32)
    failed = 0
    for item in results:
        mark = "PASS" if item.ok else "FAIL"
        line = f"[{mark}] {item.name}"
        if item.status is not None:
            line += f" (status={item.status})"
        print(line)
        if item.detail and not item.ok:
            print(f"       detail: {item.detail}")
        if not item.ok:
            failed += 1
    print("=" * 32)
    print(f"Total checks: {len(results)} | Failed: {failed}")
    return 1 if failed else 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Kazumi local streamer+viewer smoke test")
    parser.add_argument(
        "--base-url",
        default="http://127.0.0.1:8000",
        help="Backend base URL (default: http://127.0.0.1:8000)",
    )
    args = parser.parse_args()
    return run_smoke(args.base_url)


if __name__ == "__main__":
    sys.exit(main())
