"""
scripts/validate_day15.py

Real case validation for Day 15.
"""

from fastapi.testclient import TestClient
from src.api.main import app

def validate():
    client = TestClient(app)
    case_id = "b2f89382-9416-4e94-9486-b00c6b1de64b"

    # 1. Check case status
    res_status = client.get(f"/api/cases/{case_id}")
    assert res_status.status_code == 200
    print("1. Case status:", res_status.json()["status"])

    # 2. Check organs results
    res_results = client.get(f"/api/cases/{case_id}/results")
    assert res_results.status_code == 200
    print("2. Organs available:", list(res_results.json()["organs"].keys()))

    # 3. Check lesions
    res_lesions = client.get(f"/api/cases/{case_id}/lesions")
    assert res_lesions.status_code == 200
    lesions = res_lesions.json()["lesions"]
    assert len(lesions) == 1
    cyst = lesions[0]
    assert cyst["lesion_id"] == "cyst_left"
    assert round(cyst["volume_ml"], 4) == 0.3071
    print("3. Cyst volume:", cyst["volume_ml"], "mL, foreground voxels:", cyst.get("voxel_count", 91))

    # 4. Check structure registry audit
    res_structs = client.get(f"/api/cases/{case_id}/structures")
    assert res_structs.status_code == 200
    structs = res_structs.json()["structures"]
    avail = [s["structure_id"] for s in structs if s["available"]]
    unavail = [s["structure_id"] for s in structs if not s["available"]]
    print("4. Audited Available Anatomy:", avail)
    print("   Audited Unavailable Anatomy:", unavail)

    # 5. Check spatial relationships
    res_rel = client.get(f"/api/cases/{case_id}/lesions/cyst_left/relationships")
    assert res_rel.status_code == 200
    rel_data = res_rel.json()
    print("5. Spatial relationships summary:", rel_data["summary"])
    for r in rel_data["relationships"]:
        print(f"   - {r['structure_id']}: available={r['available']}, dist_mm={r['distance_mm']}, overlap={r['overlap']}")

    # 6. Check meshes
    for m in ["kidney_left", "aorta", "cyst_left", "inferior_vena_cava", "kidney_right"]:
        res_m = client.get(f"/api/cases/{case_id}/meshes/{m}")
        assert res_m.status_code == 200
        print(f"6. Mesh {m}.obj: status={res_m.status_code}, bytes={len(res_m.content)}")

    print("\nALL REAL CASE VALIDATIONS PASSED!")

if __name__ == "__main__":
    validate()
