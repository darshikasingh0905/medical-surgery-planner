"""
tests/test_day15_planning.py

Comprehensive unit tests for Day 15:
- Anatomical structure registry
- Availability & unsegmented structure handling
- Physical Euclidean distance with anisotropic spacing
- Volumetric mask overlap detection
- Missing/empty mask handling
- Lesion relationship API endpoints
- Error handling (missing case, missing lesion)
- Real-case validation on genuine KiTS23 cyst
"""

from pathlib import Path
import numpy as np
import pytest
from fastapi.testclient import TestClient

from src.api.main import app
from src.anatomy.structure_registry import (
    STRUCTURE_CATALOG,
    get_structure_definitions,
    inspect_case_structures,
    get_available_structures,
    get_structure_metadata,
    get_structure_mask_path,
    is_structure_available,
)
from src.measurements.spatial_relationships import (
    calculate_mask_pair_spatial_relationship,
    compute_lesion_spatial_relationships,
)

REAL_CASE_ID = "b2f89382-9416-4e94-9486-b00c6b1de64b"
client = TestClient(app)


# =====================================================================
# Phase 1 & 2: Structure Registry Tests
# =====================================================================

class TestStructureRegistry:
    def test_catalog_definitions_integrity(self):
        """Verify the canonical catalog contains all required renal planning structures."""
        defs = get_structure_definitions()
        required_keys = [
            "kidney_left",
            "kidney_right",
            "aorta",
            "inferior_vena_cava",
            "renal_artery",
            "renal_vein",
            "renal_pelvis",
            "ureter",
            "adrenal_gland_left",
            "adrenal_gland_right",
        ]
        for k in required_keys:
            assert k in defs
            assert "display_name" in defs[k]
            assert "category" in defs[k]
            assert "unavailable_explanation" in defs[k]

    def test_inspect_real_case_structures(self):
        """Audits the real case b2f89382-9416-4e94-9486-b00c6b1de64b on disk."""
        audit = inspect_case_structures(REAL_CASE_ID)
        assert isinstance(audit, dict)

        # Available structures in this real CT case
        assert audit["kidney_left"]["available"] is True
        assert audit["kidney_left"]["voxel_count"] > 0
        assert audit["kidney_left"]["mesh_available"] is True

        assert audit["aorta"]["available"] is True
        assert audit["aorta"]["mesh_available"] is True

        assert audit["inferior_vena_cava"]["available"] is True

        # Non-segmented / unavailable structures
        assert audit["renal_artery"]["available"] is False
        assert audit["renal_artery"]["voxel_count"] == 0
        assert "vascular" in audit["renal_artery"]["status_reason"].lower()

        assert audit["renal_vein"]["available"] is False
        assert audit["renal_pelvis"]["available"] is False
        assert audit["ureter"]["available"] is False

    def test_available_structures_filter(self):
        """get_available_structures returns only structures that genuinely exist."""
        avail = get_available_structures(REAL_CASE_ID)
        for struct_id, info in avail.items():
            assert info["available"] is True
            assert info["voxel_count"] > 0
            assert info["mask_path"] is not None

        # Unavailable structures must NOT be in available dict
        assert "renal_artery" not in avail
        assert "renal_vein" not in avail
        assert "ureter" not in avail

    def test_get_structure_metadata_and_availability(self):
        """Verify helper accessors."""
        meta_kidney = get_structure_metadata("kidney_left", REAL_CASE_ID)
        assert meta_kidney is not None
        assert meta_kidney["display_name"] == "Left Kidney"
        assert is_structure_available("kidney_left", REAL_CASE_ID) is True

        meta_artery = get_structure_metadata("renal_artery", REAL_CASE_ID)
        assert meta_artery is not None
        assert meta_artery["available"] is False
        assert is_structure_available("renal_artery", REAL_CASE_ID) is False

        # Non-existent ID returns None
        assert get_structure_metadata("unknown_structure_xyz", REAL_CASE_ID) is None
        assert is_structure_available("unknown_structure_xyz", REAL_CASE_ID) is False

    def test_get_structure_mask_path(self):
        """get_structure_mask_path returns valid path for available, None for unavailable."""
        path = get_structure_mask_path("kidney_left", REAL_CASE_ID)
        assert path is not None
        assert path.exists()

        path_unavail = get_structure_mask_path("renal_artery", REAL_CASE_ID)
        assert path_unavail is None


# =====================================================================
# Phase 3: Spatial Relationships & Physical Distance Tests
# =====================================================================

class TestSpatialRelationships:
    def test_spatial_relationship_overlap(self):
        """Overlapping masks must return overlap=True and distance_mm=0.0."""
        shape = (30, 30, 30)
        spacing = (1.5, 1.5, 2.0)

        lesion = np.zeros(shape, dtype=np.uint8)
        structure = np.zeros(shape, dtype=np.uint8)

        # Create intersection at [10:15, 10:15, 10:15]
        lesion[10:15, 10:15, 10:15] = 1
        structure[12:18, 12:18, 12:18] = 1

        rel = calculate_mask_pair_spatial_relationship(lesion, structure, spacing)
        assert rel["available"] is True
        assert rel["overlap"] is True
        assert rel["distance_mm"] == 0.0
        assert rel["computational_minimum_distance_mm"] == 0.0
        assert rel["overlap_voxel_count"] > 0

    def test_physical_distance_anisotropic_spacing(self):
        """
        Calculates physical distance correctly with anisotropic spacing.
        Separation along z-axis by 5 voxels with dz=3.0 mm must yield 15.0 mm.
        """
        shape = (40, 40, 40)
        spacing = (1.0, 1.0, 3.0)  # dx=1mm, dy=1mm, dz=3mm

        lesion = np.zeros(shape, dtype=np.uint8)
        structure = np.zeros(shape, dtype=np.uint8)

        lesion[10, 10, 10] = 1
        structure[10, 10, 15] = 1  # 5 voxels along z (5 * 3.0 = 15.0 mm)

        rel = calculate_mask_pair_spatial_relationship(lesion, structure, spacing)
        assert rel["available"] is True
        assert rel["overlap"] is False
        assert pytest.approx(rel["distance_mm"], abs=1e-2) == 15.0
        assert pytest.approx(rel["computational_minimum_distance_mm"], abs=1e-2) == 15.0

    def test_spatial_relationship_missing_or_empty_mask(self):
        """None or empty structure mask returns available=False and distance=None."""
        shape = (20, 20, 20)
        spacing = (1.5, 1.5, 1.5)
        lesion = np.zeros(shape, dtype=np.uint8)
        lesion[5:8, 5:8, 5:8] = 1

        # 1. Structure is None
        rel_none = calculate_mask_pair_spatial_relationship(lesion, None, spacing)
        assert rel_none["available"] is False
        assert rel_none["overlap"] is None
        assert rel_none["distance_mm"] is None

        # 2. Structure has 0 foreground voxels
        empty_struct = np.zeros(shape, dtype=np.uint8)
        rel_empty = calculate_mask_pair_spatial_relationship(lesion, empty_struct, spacing)
        assert rel_empty["available"] is False
        assert rel_empty["overlap"] is None
        assert rel_empty["distance_mm"] is None

    def test_compute_lesion_spatial_relationships_real_case(self):
        """Tests end-to-end spatial relationships calculation on the real case cyst."""
        lesion_path = Path("outputs/cases") / REAL_CASE_ID / "lesions" / "cyst_left.nii.gz"
        assert lesion_path.exists()

        result = compute_lesion_spatial_relationships(lesion_path, REAL_CASE_ID)
        assert result["lesion_id"] == "cyst_left"
        assert "relationships" in result
        assert len(result["relationships"]) == len(STRUCTURE_CATALOG)

        rel_map = {r["structure_id"]: r for r in result["relationships"]}

        # Kidney left: cyst is embedded in it -> overlap=True, dist=0.0
        assert rel_map["kidney_left"]["available"] is True
        assert rel_map["kidney_left"]["overlap"] is True
        assert rel_map["kidney_left"]["distance_mm"] == 0.0

        # Aorta: separated -> overlap=False, dist > 0
        assert rel_map["aorta"]["available"] is True
        assert rel_map["aorta"]["overlap"] is False
        assert rel_map["aorta"]["distance_mm"] > 50.0

        # Inferior vena cava: separated -> overlap=False, dist > 0
        assert rel_map["inferior_vena_cava"]["available"] is True
        assert rel_map["inferior_vena_cava"]["overlap"] is False
        assert rel_map["inferior_vena_cava"]["distance_mm"] > 80.0

        # Renal artery: unavailable -> distance=None
        assert rel_map["renal_artery"]["available"] is False
        assert rel_map["renal_artery"]["distance_mm"] is None
        assert rel_map["renal_artery"]["overlap"] is None


# =====================================================================
# Phase 4: API Endpoints Tests
# =====================================================================

class TestPlanningAPI:
    def test_get_case_structures_success(self):
        """GET /api/cases/{case_id}/structures returns audited structures."""
        res = client.get(f"/api/cases/{REAL_CASE_ID}/structures")
        assert res.status_code == 200
        data = res.json()
        assert data["case_id"] == REAL_CASE_ID
        assert "structures" in data
        assert len(data["structures"]) >= 10

        struct_map = {s["structure_id"]: s for s in data["structures"]}
        assert struct_map["kidney_left"]["available"] is True
        assert struct_map["renal_artery"]["available"] is False

    def test_get_case_structures_missing_case(self):
        """GET /api/cases/{missing}/structures returns 404."""
        res = client.get("/api/cases/non-existent-uuid/structures")
        assert res.status_code == 404
        assert "not found" in res.json()["detail"].lower()

    def test_get_lesion_relationships_success(self):
        """GET /api/cases/{case_id}/lesions/{lesion_id}/relationships returns 200."""
        res = client.get(f"/api/cases/{REAL_CASE_ID}/lesions/cyst_left/relationships")
        assert res.status_code == 200
        data = res.json()
        assert data["case_id"] == REAL_CASE_ID
        assert data["lesion_id"] == "cyst_left"
        assert "relationships" in data
        assert len(data["relationships"]) >= 10

        # Check safety disclaimer present
        assert "safety_disclaimer" in data
        assert "computational" in data["safety_disclaimer"].lower()

    def test_get_lesion_relationships_missing_lesion(self):
        """GET relationships for non-existent lesion returns 404."""
        res = client.get(f"/api/cases/{REAL_CASE_ID}/lesions/fake_lesion_xyz/relationships")
        assert res.status_code == 404
        assert "not found" in res.json()["detail"].lower()

    def test_get_lesion_relationships_missing_case(self):
        """GET relationships for non-existent case returns 404."""
        res = client.get("/api/cases/fake-case-uuid/lesions/cyst_left/relationships")
        assert res.status_code == 404

    def test_get_case_mesh_ivc(self):
        """GET /api/cases/{case_id}/meshes/inferior_vena_cava returns 200."""
        res = client.get(f"/api/cases/{REAL_CASE_ID}/meshes/inferior_vena_cava")
        assert res.status_code == 200
        assert res.text.startswith("# Generated by Medical Surgery Planner")

    def test_get_case_mesh_kidney_right(self):
        """GET /api/cases/{case_id}/meshes/kidney_right returns 200."""
        res = client.get(f"/api/cases/{REAL_CASE_ID}/meshes/kidney_right")
        assert res.status_code == 200
        assert res.text.startswith("# Generated by Medical Surgery Planner")
