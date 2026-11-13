"""Test suite for verifying modelScaniTem FastAPI backend using httpx.AsyncClient."""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

# Force UTF-8 stdout
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

import httpx
from api.main import app


async def run_tests():
    print("========================================")
    print("Testing modelScaniTem REST API Endpoints")
    print("========================================")

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Root & Health
        r = await client.get("/")
        assert r.status_code == 200, f"Root failed: {r.status_code}"
        print(" Root [/]:", r.json()["service"])

        r = await client.get("/health")
        assert r.status_code == 200, f"Health failed: {r.status_code}"
        health = r.json()
        print(" Health check [/health]:", health["status"], "- Trays:", health["available_trays"])

        # 2. List Trays
        r = await client.get("/api/v1/trays")
        assert r.status_code == 200, f"Trays list failed: {r.status_code}"
        trays = r.json()
        print(f" List Trays [/api/v1/trays]: Found {len(trays)} trays")
        for t in trays:
            print(f"   - {t['tray_id']}: {t['tray_name']} ({t['total_slots']} slots, has_ref={t['has_reference_image']})")

        # 3. Tray Details
        test_tray_id = "box2-template01_31-item"
        r = await client.get(f"/api/v1/trays/{test_tray_id}")
        assert r.status_code == 200, f"Tray detail failed: {r.status_code}"
        detail = r.json()
        print(f" Tray Detail [/api/v1/trays/{test_tray_id}]: {detail['tray_name']} with {len(detail['slots'])} slots")

        # 4. Camera Guide Wireframe PNG
        r = await client.get(f"/api/v1/trays/{test_tray_id}/guide?width=640&height=480&transparent=true")
        assert r.status_code == 200, f"Tray guide failed: {r.status_code}"
        assert r.headers["content-type"] == "image/png"
        assert len(r.content) > 1000
        print(f" Tray Guide PNG [/api/v1/trays/{test_tray_id}/guide]: {len(r.content)} bytes received (image/png)")

        # 5. Tray Scan
        img_path = Path("data/tray_refs") / f"{test_tray_id}.jpg"
        assert img_path.exists(), f"Reference image not found: {img_path}"
        
        with open(img_path, "rb") as f:
            file_bytes = f.read()

        print(f"\n Running Tray Scan [/api/v1/scan/tray] with {img_path.name}...")
        r = await client.post(
            "/api/v1/scan/tray",
            data={
                "tray_id": test_tray_id,
                "skip_quality": "true",
                "crop_mode": "smart",
                "return_annotated": "true",
                "save_history": "false",
            },
            files={"image": ("test.jpg", file_bytes, "image/jpeg")},
        )
        assert r.status_code == 200, f"Scan failed: {r.status_code} - {r.text}"
        scan_res = r.json()
        counters = scan_res["counters"]
        print(" Scan Response Summary:")
        print(f"   - Tray: {scan_res['tray_name']} ({scan_res['tray_id']})")
        print(f"   - Success: {scan_res['success']}")
        print(f"   - Accuracy: {counters['accuracy_pct']}%")
        print(f"   - Correct: {counters['correct']}/{counters['total_slots']}")
        print(f"   - Missing: {counters['missing']}")
        print(f"   - Misplaced: {counters['misplaced']}")
        print(f"   - Recheck: {counters['recheck']}")
        print(f"   - Annotated Image returned: {'Yes (' + str(len(scan_res.get('annotated_image_base64', ''))) + ' b64 chars)' if scan_res.get('annotated_image_base64') else 'No'}")
        
        # The special-tools panel lists 31 checklist items in 41 slots; the reference photo is complete.
        assert counters["correct"] == counters["total_slots"] == len(detail["slots"]), (
            f"Expected all {len(detail['slots'])} slots correct, got {counters['correct']}/{counters['total_slots']}")
        print("\n ALL API TESTS PASSED SUCCESSFULLY! ")


if __name__ == "__main__":
    asyncio.run(run_tests())
