"""
scripts/verify_day21.py

Independent verification script for Day 21:
1. Validates real case b2f89382-9416-4e94-9486-b00c6b1de64b
2. Validates technical, general, and provenance endpoints
3. Confirms computational metrics preservation (volume, coordinates, host)
4. Confirms structure availability and unavailable vessels
5. Verifies strict determinism
"""

import sys
from fastapi.testclient import TestClient
from src.api.main import app

client = TestClient(app)
case_id = "b2f89382-9416-4e94-9486-b00c6b1de64b"

print(f"=== VERIFYING CASE {case_id} ===")

# 1. Technical endpoint
r_tech = client.get(f"/api/cases/{case_id}/planning/explanation?audience=technical")
assert r_tech.status_code == 200, f"Technical status code: {r_tech.status_code}"
d_tech = r_tech.json()
print("[OK] GET /api/cases/{case_id}/planning/explanation?audience=technical -> 200 OK")

# 2. General endpoint
r_gen = client.get(f"/api/cases/{case_id}/planning/explanation?audience=general")
assert r_gen.status_code == 200, f"General status code: {r_gen.status_code}"
d_gen = r_gen.json()
print("[OK] GET /api/cases/{case_id}/planning/explanation?audience=general -> 200 OK")

# 3. Provenance endpoint
r_prov = client.get(f"/api/cases/{case_id}/planning/explanation/provenance")
assert r_prov.status_code == 200, f"Provenance status code: {r_prov.status_code}"
d_prov = r_prov.json()
print("[OK] GET /api/cases/{case_id}/planning/explanation/provenance -> 200 OK")

# Confirm findings
findings = d_tech["computational_findings"]
assert len(findings) > 0, "No computational findings found"
primary = findings[0]
print(f"Finding ID: {primary['finding_id']}")
print(f"Model Class: {primary['model_class']}")
print(f"Volume: {primary['volume_ml']} mL")
print(f"Host Organ: {primary['host_organ']}")
print(f"Voxel Centroid: {primary['centroid_voxel']}")
print(f"Physical Centroid: {primary['centroid_physical_mm']}")

# Assertions
assert "cyst_left" in primary["finding_id"] or "model_cyst_left" in primary["finding_id"], "Finding ID mismatch"
assert abs(primary["volume_ml"] - 0.3071) < 0.001, f"Volume mismatch: {primary['volume_ml']}"
assert primary["host_organ"] == "kidney_left", f"Host organ mismatch: {primary['host_organ']}"
assert primary["centroid_voxel"] == [110, 89, 218], f"Voxel centroid mismatch: {primary['centroid_voxel']}"
print("[OK] Computational metrics verified: model_cyst_left, 0.3071 mL, kidney_left, voxel [110, 89, 218]")

# Confirm anatomy & unavailable renal vessels
anatomy = d_tech["relevant_anatomy"]
avail_count = sum(1 for a in anatomy if a["available"])
unavail_count = sum(1 for a in anatomy if not a["available"])
print(f"Anatomy structures: {len(anatomy)} total ({avail_count} available, {unavail_count} unavailable)")

vessels = [a for a in anatomy if "renal_artery" in a["structure_id"] or "renal_vein" in a["structure_id"]]
assert len(vessels) > 0, "Renal vessels not found in anatomy registry"
for v in vessels:
    assert v["available"] is False, f"Vessel {v['structure_id']} incorrectly presented as available!"
print(f"[OK] Verified {len(vessels)} renal vessels correctly presented as unavailable")

# Confirm spatial relationships
rels = d_tech["spatial_relationships"]
avail_rels = [r for r in rels if r["available"]]
assert len(avail_rels) > 0, "No available spatial relationships found"
print(f"[OK] Verified {len(avail_rels)} computational distances from existing spatial services")

# Confirm planning targets
targets = d_tech["planning_targets"]
assert len(targets) > 0, "No planning targets found"
print(f"[OK] Verified {len(targets)} planning targets present")

# Confirm limitations
limitations = d_tech["limitations"]
assert len(limitations) >= 4, "Insufficient limitations documented"
print(f"[OK] Verified {len(limitations)} technical limitations present")

# Confirm provenance
assert d_prov["case_id"] == case_id
assert d_prov["generation_method"] == "deterministic_data_aggregation"
print("[OK] Provenance confirmed: case_id match, deterministic method")

# Verify deterministic behavior
r_tech_2 = client.get(f"/api/cases/{case_id}/planning/explanation?audience=technical")
d_tech_2 = r_tech_2.json()

# Dynamic timestamp fields
del d_tech["generated_at"]
del d_tech_2["generated_at"]
del d_tech["provenance"]["generation_timestamp"]
del d_tech_2["provenance"]["generation_timestamp"]

assert d_tech == d_tech_2, "Outputs across two identical calls differed!"
print("[OK] DETERMINISTIC VERIFICATION PASSED: 100% identical outputs across independent invocations")
print("=== ALL REAL-CASE CHECKS PASSED ===")
