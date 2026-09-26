"""
src/planning/report_service.py

Preoperative Case Planning Report Generation Service (Day 22).

Consolidates existing authoritative computational services:
  - PlanningSummaryService (computational planning aggregation)
  - ProcedureExplanationService (deterministic multi-audience context)
into an authoritative, reproducible PreoperativeReport (JSON) and ReportLab PDF document.

CLINICAL GOVERNANCE & SAFETY NOTICE:
This report compiles computational imaging outputs and user annotations for
educational and research exploration only.
It DOES NOT:
- provide a clinical diagnosis
- assess malignancy or benign pathology
- determine histological staging or TNM classification
- recommend a surgical procedure or operative approach
- determine surgical risk or feasibility
- substitute for medical specialist consultation or clinical records
"""

import io
from datetime import datetime, timezone
from typing import Any

from src.api.utils.case_manager import case_exists, get_case_info
from src.planning.planning_summary import planning_summary_service
from src.planning.procedure_explanation_service import procedure_explanation_service
from src.planning.report_models import (
    PreoperativeReport,
    ReportMetadata,
    ReportCaseOverview,
    ReportImagingInfo,
    ReportFindingItem,
    ReportAnatomyItem,
    ReportSpatialRelationshipItem,
    ReportLesionMeasurementItem,
    ReportPlanningTargetItem,
    ReportPlanningMeasurementItem,
    ReportPlanningSessionNotes,
    ReportProceduralContextItem,
    ReportClinicalReviewItem,
    ReportLimitationItem,
    ReportProvenance,
    ReportGovernance,
)


class PreoperativeReportService:
    """
    Synthesizes the Preoperative Case Planning Report from existing planning engines.
    Zero calculation duplication; purely an aggregation and presentation layer.
    """

    def generate_report(
        self,
        case_id: str,
        audience: str = "technical",
    ) -> PreoperativeReport:
        """
        Constructs the PreoperativeReport for a given case and audience.

        Args:
            case_id: Unique case UUID.
            audience: 'technical' (default) or 'general'.

        Returns:
            PreoperativeReport: Fully structured, 15-section report document.

        Raises:
            ValueError: If the case does not exist or audience is invalid.
        """
        if not case_exists(case_id):
            raise ValueError(f"Case '{case_id}' not found")

        if audience not in ("technical", "general"):
            raise ValueError(f"Invalid audience '{audience}'. Allowed: 'technical', 'general'")

        # 1. Consume existing authoritative planning summary
        summary = planning_summary_service.get_planning_summary(case_id)
        case_info = get_case_info(case_id) or {}

        # 2. Consume existing authoritative procedure explanation
        explanation = procedure_explanation_service.generate_explanation(
            case_id=case_id, audience=audience
        )

        # ── 1. Report Metadata ───────────────────────────────────────────────
        metadata = ReportMetadata(
            report_id=f"report_{case_id[:8]}_{audience}",
            case_id=case_id,
            target_audience=audience,
            generated_at_utc=datetime.now(timezone.utc).isoformat(),
        )

        # ── 2. Case Overview ─────────────────────────────────────────────────
        # Determine host anatomy from primary finding
        host_organ = None
        if explanation.computational_findings:
            host_organ = explanation.computational_findings[0].host_organ_display

        case_overview = ReportCaseOverview(
            case_id=case_id,
            target_anatomy=host_organ,
            status=summary.status,
            narrative_summary=(
                f"Computational planning session for case {case_id[:8]}. "
                f"{len(explanation.computational_findings)} model-predicted finding(s) identified. "
                f"{len([a for a in explanation.relevant_anatomy if a.available])} anatomical "
                f"structure(s) available. Audience: {audience}."
            ),
            original_filename=case_info.get("filename") or summary.scan_info.get("filename"),
            source_type="case_metadata",
        )

        # ── 3. Imaging Information ───────────────────────────────────────────
        scan = summary.scan_info or {}
        imaging_info = ReportImagingInfo(
            modality="CT",
            dimensions=scan.get("shape"),
            spacing_mm=scan.get("voxel_spacing_mm"),
            orientation=scan.get("orientation"),
            intensity_range_hu=scan.get("intensity_range"),
            provenance="derived_computation",
            source_type="derived_computation",
        )

        # ── 4. Computational Findings ────────────────────────────────────────
        findings_out: list[ReportFindingItem] = []
        for f in explanation.computational_findings:
            findings_out.append(
                ReportFindingItem(
                    finding_id=f.finding_id,
                    label=f.label or f.finding_id,
                    class_name=f.model_class,
                    host_organ=f.host_organ,
                    host_organ_display=f.host_organ_display,
                    volume_ml=f.volume_ml,
                    bounding_box_mm=f.dimensions_mm,
                    centroid_voxel=f.centroid_voxel,
                    centroid_physical_mm=f.centroid_physical_mm,
                    computational_interpretation=f.computational_interpretation,
                    source_provenance=f.source_provenance,
                    review_requirement="Qualified clinical review required",
                    source_type="model_inference",
                )
            )

        # ── 5. Anatomical Structures ─────────────────────────────────────────
        anatomy_out: list[ReportAnatomyItem] = []
        for a in explanation.relevant_anatomy:
            # Build availability note
            if a.available:
                avail_note = f"Segmented structure ({a.source_segmentation or 'TotalSegmentator'})."
            else:
                avail_note = f"Not segmented — not available in TotalSegmentator output for this case. {a.unavailability_reason or ''}".strip()

            # Try to get volume and centroid from summary anatomy
            vol_ml = None
            centroid_phys = None
            for sum_a in summary.anatomy:
                if sum_a.get("structure_id") == a.structure_id:
                    vol_ml = sum_a.get("volume_ml")
                    centroid_phys = sum_a.get("centroid_physical_mm") or sum_a.get("centroid_mm")
                    break

            anatomy_out.append(
                ReportAnatomyItem(
                    structure_id=a.structure_id,
                    display_name=a.display_name,
                    category=a.category,
                    available=a.available,
                    voxel_count=a.voxel_count,
                    volume_ml=vol_ml,
                    centroid_physical_mm=centroid_phys,
                    mesh_available=a.mesh_available,
                    relationship_to_finding=a.relationship_to_finding,
                    unavailability_reason=a.unavailability_reason,
                    availability_note=avail_note,
                    color=a.color,
                    source_type="derived_computation",
                )
            )

        # ── 6. Spatial Relationships ─────────────────────────────────────────
        relationships_out: list[ReportSpatialRelationshipItem] = []
        for r in explanation.spatial_relationships:
            finding_id = "primary_finding"
            if explanation.computational_findings:
                finding_id = explanation.computational_findings[0].finding_id
            relationships_out.append(
                ReportSpatialRelationshipItem(
                    finding_id=finding_id,
                    target_structure=r.target_id,
                    target_display_name=r.target_display_name,
                    min_distance_mm=r.distance_mm,
                    centroid_distance_mm=None,
                    overlap_detected=(r.overlap is True),
                    overlap_voxel_count=r.overlap_voxel_count,
                    available=r.available,
                    unavailability_reason=r.unavailability_reason,
                    interpretation=r.interpretation,
                    source=r.source,
                    source_type="derived_computation",
                )
            )

        # ── 7. Lesion Measurements ───────────────────────────────────────────
        measurements_out: list[ReportLesionMeasurementItem] = []
        for f in summary.findings:
            measurements_out.append(
                ReportLesionMeasurementItem(
                    finding_id=f.get("lesion_id", "primary"),
                    volume_ml=f.get("volume_ml"),
                    dimensions_mm=f.get("dimensions_mm"),
                    voxel_count=f.get("voxel_count"),
                    source_type="derived_computation",
                )
            )

        # ── 8. Planning Targets ──────────────────────────────────────────────
        targets_out: list[ReportPlanningTargetItem] = []
        for t in summary.targets:
            src_str = t.source.value if hasattr(t.source, "value") else str(t.source)
            targets_out.append(
                ReportPlanningTargetItem(
                    target_id=t.target_id,
                    label=t.label,
                    target_type=t.target_type.value if hasattr(t.target_type, "value") else str(t.target_type),
                    provenance="model_inference" if src_str == "model" else "user_annotation",
                    voxel_coordinate=t.voxel_coordinate,
                    physical_coordinate_mm=t.physical_coordinate,
                    linked_finding_id=t.lesion_id,
                    source_type="model_inference" if src_str == "model" else "user_annotation",
                )
            )

        # ── 9. Planning Measurements ─────────────────────────────────────────
        planning_measurements_out: list[ReportPlanningMeasurementItem] = []
        for m in summary.measurements:
            m_type_str = m.measurement_type.value if hasattr(m.measurement_type, "value") else str(m.measurement_type)
            planning_measurements_out.append(
                ReportPlanningMeasurementItem(
                    measurement_id=m.measurement_id,
                    label=m.label,
                    length_mm=m.distance_mm,
                    length_cm=m.distance_cm,
                    slice_plane=m_type_str,
                    slice_index=0,
                    start_voxel=m.start_voxel,
                    end_voxel=m.end_voxel,
                    source_type="user_annotation",
                )
            )

        # ── 10. Planning Session Notes ───────────────────────────────────────
        session = summary.session
        session_notes = ReportPlanningSessionNotes(
            session_id=session.session_id if session else None,
            content=(session.planning_notes if session and session.planning_notes else None),
            author="Computational Planning System",
            updated_at=session.updated_at if session else None,
            provenance="user_annotation",
            source_type="user_annotation",
        )

        # ── 11. Procedural Context ───────────────────────────────────────────
        context_out: list[ReportProceduralContextItem] = []
        if explanation.procedural_context and explanation.procedural_context.items:
            for item in explanation.procedural_context.items:
                context_out.append(
                    ReportProceduralContextItem(
                        topic=item.get("heading", ""),
                        summary=item.get("text", ""),
                        heading=item.get("heading", ""),
                        text=item.get("text", ""),
                        source_type="explanatory_context",
                    )
                )

        # ── 12. Clinical Review Items ────────────────────────────────────────
        clinical_review_out: list[ReportClinicalReviewItem] = []
        for cr in explanation.clinical_review_items:
            clinical_review_out.append(
                ReportClinicalReviewItem(
                    item_id=cr.item_id,
                    item=cr.statement,
                    category=cr.category,
                    rationale=cr.statement,
                    statement=cr.statement,
                    source_type="mandatory_clinical_review",
                )
            )

        # ── 13. System Limitations ───────────────────────────────────────────
        limitations_out: list[ReportLimitationItem] = []
        for lim in explanation.limitations:
            limitations_out.append(
                ReportLimitationItem(
                    limitation_id=lim.limitation_id,
                    domain=lim.domain,
                    limitation=lim.description,
                    description=lim.description,
                    recommended_action="Consult a qualified medical professional for clinical interpretation.",
                    source_type="system_limitation",
                )
            )

        # ── 14. Provenance ───────────────────────────────────────────────────
        prov = explanation.provenance
        import hashlib, json as _json
        substantive_data = {
            "case_id": case_id,
            "findings": [f.model_dump(exclude={"source_type"}) for f in findings_out],
            "relationships": [r.model_dump(exclude={"source_type"}) for r in relationships_out],
            "targets": [t.model_dump(exclude={"source_type"}) for t in targets_out],
        }
        det_hash = hashlib.sha256(
            _json.dumps(substantive_data, sort_keys=True, default=str).encode()
        ).hexdigest()[:16]

        provenance_out = ReportProvenance(
            report_generator="PreoperativeReportService",
            summary_service="PlanningSummaryService",
            explanation_service="ProcedureExplanationService",
            deterministic_hash=det_hash,
            data_sources={
                "findings": "model_inference (KiTS23)",
                "anatomy": "derived_computation (TotalSegmentator)",
                "spatial_relationships": "derived_computation (Euclidean surface distance)",
                "targets": "model_inference / user_annotation",
                "measurements": "user_annotation",
                "notes": "user_annotation",
            },
            case_id=case_id,
            ct_source=prov.ct_source if prov else None,
            segmentation_source=prov.segmentation_source if prov else None,
            lesion_model_source=prov.lesion_model_source if prov else None,
            lesion_class_mapping=prov.lesion_class_mapping if prov else None,
            coordinate_system_source=prov.coordinate_system_source if prov else "src.geometry.coordinate_system",
            measurement_source=prov.measurement_source if prov else "src.planning.measurement_service",
            spatial_relationship_source=prov.spatial_relationship_source if prov else "src.measurements.spatial_relationships",
            anatomy_registry_source=prov.anatomy_registry_source if prov else "src.anatomy.structure_registry",
            planning_session_source=prov.planning_session_source if prov else "src.planning.planning_session",
            generation_method="deterministic_data_aggregation",
            source_type="audit_trail",
        )

        # ── 15. Governance ───────────────────────────────────────────────────
        governance_out = ReportGovernance()

        return PreoperativeReport(
            metadata=metadata,
            case_overview=case_overview,
            imaging_info=imaging_info,
            computational_findings=findings_out,
            anatomical_structures=anatomy_out,
            spatial_relationships=relationships_out,
            lesion_measurements=measurements_out,
            planning_targets=targets_out,
            planning_measurements=planning_measurements_out,
            planning_session_notes=session_notes,
            procedural_context=context_out,
            clinical_review_items=clinical_review_out,
            system_limitations=limitations_out,
            provenance=provenance_out,
            governance=governance_out,
        )


    def generate_report_pdf(
        self,
        case_id: str,
        audience: str = "technical",
    ) -> bytes:
        """
        Generates a publication-grade A4 PDF document for the Preoperative Report.

        Args:
            case_id: Unique case UUID.
            audience: 'technical' or 'general'.

        Returns:
            bytes: Binary content of the compiled PDF.
        """
        report = self.generate_report(case_id=case_id, audience=audience)
        return build_pdf_document(report)



# ==============================================================================
# ReportLab PDF Document Builder
# ==============================================================================

def build_pdf_document(report: PreoperativeReport) -> bytes:
    """
    Builds an A4 portrait PDF using ReportLab Platypus.
    Two-pass canvas handles dynamic total page numbering ('Page X of Y').
    """
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.platypus import (
        SimpleDocTemplate,
        Paragraph,
        Spacer,
        Table,
        TableStyle,
        KeepTogether,
        HRFlowable,
    )
    from reportlab.pdfgen import canvas

    class NumberedCanvas(canvas.Canvas):
        """Two-pass canvas to compute and render total page count on running headers/footers."""

        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self._saved_page_states = []

        def showPage(self):
            self._saved_page_states.append(dict(self.__dict__))
            self._startPage()

        def save(self):
            num_pages = len(self._saved_page_states)
            for state in self._saved_page_states:
                self.__dict__.update(state)
                self.draw_page_decorations(num_pages)
                super().showPage()
            super().save()

        def draw_page_decorations(self, page_count: int):
            self.saveState()
            self.setFont("Helvetica", 7.5)
            self.setFillColor(colors.HexColor("#64748b"))

            # Running header (all pages after page 1)
            if self._pageNumber > 1:
                self.drawString(
                    36,
                    A4[1] - 25,
                    f"AI-Assisted Preoperative Planning — Case {report.metadata.case_id[:8]} — {report.metadata.target_audience.upper()} REPORT",
                )
                self.setStrokeColor(colors.HexColor("#e2e8f0"))
                self.setLineWidth(0.5)
                self.line(36, A4[1] - 28, A4[0] - 36, A4[1] - 28)

            # Running footer (all pages)
            footer_text = (
                f"Page {self._pageNumber} of {page_count} | Research Prototype — Not for Primary Diagnostic Use"
            )
            self.drawRightString(A4[0] - 36, 20, footer_text)
            self.drawString(
                36,
                20,
                f"Generated: {report.metadata.generated_at_utc[:19]}Z | ID: {report.metadata.report_id}",
            )
            self.setStrokeColor(colors.HexColor("#e2e8f0"))
            self.setLineWidth(0.5)
            self.line(36, 28, A4[0] - 36, 28)

            self.restoreState()

    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=36,
        rightMargin=36,
        topMargin=36,
        bottomMargin=36,
    )

    styles = getSampleStyleSheet()

    # Custom styles
    title_style = ParagraphStyle(
        "ReportTitle",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=15,
        leading=18,
        textColor=colors.HexColor("#0f172a"),
        spaceAfter=3,
    )

    meta_style = ParagraphStyle(
        "ReportMeta",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8,
        leading=10,
        textColor=colors.HexColor("#475569"),
    )

    section_heading = ParagraphStyle(
        "SectionHeading",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=10.5,
        leading=13,
        textColor=colors.HexColor("#0369a1"),
        spaceBefore=8,
        spaceAfter=3,
    )

    body_style = ParagraphStyle(
        "ReportBody",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8,
        leading=11,
        textColor=colors.HexColor("#1e293b"),
    )

    governance_style = ParagraphStyle(
        "ReportGovernance",
        parent=styles["Normal"],
        fontName="Helvetica-Oblique",
        fontSize=7.2,
        leading=9.5,
        textColor=colors.HexColor("#78350f"),
    )

    table_header = ParagraphStyle(
        "TableHeader",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=7.5,
        leading=9,
        textColor=colors.HexColor("#0f172a"),
    )

    table_cell = ParagraphStyle(
        "TableCell",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=7.5,
        leading=9,
        textColor=colors.HexColor("#334155"),
    )

    table_cell_mono = ParagraphStyle(
        "TableCellMono",
        parent=styles["Normal"],
        fontName="Courier",
        fontSize=7.0,
        leading=8.5,
        textColor=colors.HexColor("#0f172a"),
    )

    story = []

    # ── HEADER & TITLE ────────────────────────────────────────────────────────
    story.append(Paragraph(report.metadata.report_title, title_style))
    story.append(
        Paragraph(
            f"<b>Case ID:</b> {report.metadata.case_id} &nbsp;|&nbsp; "
            f"<b>Audience:</b> {report.metadata.target_audience.upper()} &nbsp;|&nbsp; "
            f"<b>System:</b> {report.metadata.system_name} ({report.metadata.software_version})",
            meta_style,
        )
    )
    story.append(Spacer(1, 6))

    # ── MANDATORY GOVERNANCE ALERT BOX ────────────────────────────────────────
    gov_text = (
        f"<b>MANDATORY CLINICAL GOVERNANCE NOTICE:</b><br/>"
        f"{report.governance.statement}"
    )
    gov_table = Table(
        [[Paragraph(gov_text, governance_style)]],
        colWidths=[A4[0] - 72],
    )
    gov_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#fef3c7")),
                ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#d97706")),
                ("PADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    story.append(gov_table)
    story.append(Spacer(1, 8))

    # ── SECTION 1 & 2: CASE OVERVIEW & IMAGING INFORMATION ───────────────────
    story.append(Paragraph("1. Case Overview & CT Acquisition Context", section_heading))
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#cbd5e1"), spaceAfter=4))

    img = report.imaging_info
    overview_data = [
        [
            Paragraph("<b>Original File:</b>", table_header),
            Paragraph(report.case_overview.original_filename or "N/A", table_cell),
            Paragraph("<b>Status:</b>", table_header),
            Paragraph(report.case_overview.status.upper(), table_cell),
        ],
        [
            Paragraph("<b>CT Matrix Shape:</b>", table_header),
            Paragraph(f"{img.dimensions[0]} × {img.dimensions[1]} × {img.dimensions[2]} voxels" if img.dimensions else "N/A", table_cell_mono),
            Paragraph("<b>Voxel Spacing:</b>", table_header),
            Paragraph(f"{img.spacing_mm[0]:.2f} × {img.spacing_mm[1]:.2f} × {img.spacing_mm[2]:.2f} mm" if img.spacing_mm else "N/A", table_cell_mono),
        ],
        [
            Paragraph("<b>Orientation:</b>", table_header),
            Paragraph("".join(img.orientation) if img.orientation else "N/A", table_cell_mono),
            Paragraph("<b>HU Range:</b>", table_header),
            Paragraph(f"{img.intensity_range_hu[0]} to {img.intensity_range_hu[1]} HU" if img.intensity_range_hu else "N/A", table_cell_mono),
        ],
    ]
    t_overview = Table(overview_data, colWidths=[110, 150, 100, 163])
    t_overview.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
                ("PADDING", (0, 0), (-1, -1), 3),
            ]
        )
    )
    story.append(t_overview)
    story.append(Spacer(1, 6))

    # ── SECTION 3: COMPUTATIONAL FINDINGS ─────────────────────────────────────
    story.append(Paragraph("2. Model-Predicted Computational Findings [MODEL INFERENCE]", section_heading))
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#cbd5e1"), spaceAfter=4))

    if not report.computational_findings:
        story.append(Paragraph("<i>No computational findings detected for this case.</i>", body_style))
    else:
        findings_rows = [
            [
                Paragraph("<b>Finding ID</b>", table_header),
                Paragraph("<b>Model Class</b>", table_header),
                Paragraph("<b>Host Organ</b>", table_header),
                Paragraph("<b>Volume</b>", table_header),
                Paragraph("<b>Bounding Box</b>", table_header),
                Paragraph("<b>Voxel Centroid</b>", table_header),
            ]
        ]
        for f in report.computational_findings:
            findings_rows.append(
                [
                    Paragraph(f.finding_id, table_cell_mono),
                    Paragraph(f.class_name.upper(), table_cell),
                    Paragraph(f.host_organ_display or f.host_organ or "—", table_cell),
                    Paragraph(f"{f.volume_ml:.4f} mL" if f.volume_ml is not None else "—", table_cell_mono),
                    Paragraph(f"{f.bounding_box_mm[0]:.1f} × {f.bounding_box_mm[1]:.1f} × {f.bounding_box_mm[2]:.1f} mm" if f.bounding_box_mm else "—", table_cell_mono),
                    Paragraph(f"[{f.centroid_voxel[0]}, {f.centroid_voxel[1]}, {f.centroid_voxel[2]}]" if f.centroid_voxel else "—", table_cell_mono),
                ]
            )
        t_findings = Table(findings_rows, colWidths=[90, 75, 95, 75, 110, 78])
        t_findings.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f1f5f9")),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
                    ("PADDING", (0, 0), (-1, -1), 3),
                ]
            )
        )
        story.append(t_findings)

        # Interpretation note
        for f in report.computational_findings:
            if f.computational_interpretation:
                story.append(Spacer(1, 2))
                story.append(
                    Paragraph(
                        f"<b>Interpretation ({f.finding_id}):</b> {f.computational_interpretation}",
                        meta_style,
                    )
                )

    story.append(Spacer(1, 6))

    # ── SECTION 4: SPATIAL RELATIONSHIPS ─────────────────────────────────────
    story.append(Paragraph("3. Spatial Relationships & Proximities [DERIVED COMPUTATION]", section_heading))
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#cbd5e1"), spaceAfter=4))
    story.append(
        Paragraph(
            "<i>Note: All values describe computational minimum Euclidean surface distances in CT coordinate space. "
            "They do NOT represent surgical clearance, safe margins, or operative planes.</i>",
            meta_style,
        )
    )
    story.append(Spacer(1, 3))

    if not report.spatial_relationships:
        story.append(Paragraph("<i>No spatial relationships computed.</i>", body_style))
    else:
        rel_rows = [
            [
                Paragraph("<b>Target Structure</b>", table_header),
                Paragraph("<b>Status</b>", table_header),
                Paragraph("<b>Minimum Distance</b>", table_header),
                Paragraph("<b>Overlap State</b>", table_header),
                Paragraph("<b>Computational Interpretation</b>", table_header),
            ]
        ]
        for r in report.spatial_relationships:
            status_text = "Available" if r.available else "Not Segmented"
            dist_text = f"{r.min_distance_mm:.2f} mm" if r.min_distance_mm is not None else "N/A"
            overlap_text = "Yes (Overlap)" if r.overlap_detected else "No"
            rel_rows.append(
                [
                    Paragraph(r.target_display_name or r.target_structure, table_cell),
                    Paragraph(status_text, table_cell),
                    Paragraph(dist_text, table_cell_mono),
                    Paragraph(overlap_text, table_cell),
                    Paragraph(r.interpretation or r.unavailability_reason or "—", table_cell),
                ]
            )
        t_rels = Table(rel_rows, colWidths=[120, 75, 85, 75, 168])
        t_rels.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f1f5f9")),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
                    ("PADDING", (0, 0), (-1, -1), 2.5),
                ]
            )
        )
        story.append(t_rels)

    story.append(Spacer(1, 6))

    # ── SECTION 5: ANATOMICAL STRUCTURE AUDIT ─────────────────────────────────
    story.append(Paragraph("4. Anatomical Structure Availability Registry [DERIVED COMPUTATION]", section_heading))
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#cbd5e1"), spaceAfter=4))

    avail_structs = [a for a in report.anatomical_structures if a.available]
    unavail_structs = [a for a in report.anatomical_structures if not a.available]

    struct_rows = [
        [
            Paragraph("<b>Structure</b>", table_header),
            Paragraph("<b>Category</b>", table_header),
            Paragraph("<b>Presence</b>", table_header),
            Paragraph("<b>Voxel Count</b>", table_header),
            Paragraph("<b>Relationship to Finding / Unavailability Note</b>", table_header),
        ]
    ]
    for a in avail_structs:
        struct_rows.append(
            [
                Paragraph(a.display_name, table_cell),
                Paragraph(a.category.title(), table_cell),
                Paragraph("Available", table_cell),
                Paragraph(f"{a.voxel_count:,}" if a.voxel_count else "—", table_cell_mono),
                Paragraph(a.relationship_to_finding or "Verified on disk", table_cell),
            ]
        )
    for a in unavail_structs:
        struct_rows.append(
            [
                Paragraph(a.display_name, table_cell),
                Paragraph(a.category.title(), table_cell),
                Paragraph("Not Segmented", table_cell),
                Paragraph("0", table_cell_mono),
                Paragraph(a.unavailability_reason or "Mask not available in model output", meta_style),
            ]
        )
    t_structs = Table(struct_rows, colWidths=[120, 65, 75, 65, 198])
    t_structs.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f1f5f9")),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
                ("PADDING", (0, 0), (-1, -1), 2.5),
            ]
        )
    )
    story.append(t_structs)
    story.append(Spacer(1, 6))

    # ── SECTION 6: PLANNING TARGETS & MEASUREMENTS ────────────────────────────
    story.append(Paragraph("5. Surgical Planning Targets & Measurements [USER & MODEL ANNOTATIONS]", section_heading))
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#cbd5e1"), spaceAfter=4))

    targets_text = []
    if not report.planning_targets:
        targets_text.append("<i>No planning targets registered.</i>")
    else:
        for t in report.planning_targets:
            targets_text.append(
                f"• <b>[{t.provenance.replace('_', ' ').upper()}] {t.label}</b> (Type: {t.target_type}) — "
                f"Voxel: <font name='Courier'>[{t.voxel_coordinate[0]}, {t.voxel_coordinate[1]}, {t.voxel_coordinate[2]}]</font>, "
                f"Physical: <font name='Courier'>[{t.physical_coordinate_mm[0]:.1f}, {t.physical_coordinate_mm[1]:.1f}, {t.physical_coordinate_mm[2]:.1f}] mm</font>"
            )

    meas_text = []
    if not report.planning_measurements:
        meas_text.append("<i>No user measurements recorded.</i>")
    else:
        for m in report.planning_measurements:
            meas_text.append(
                f"• <b>{m.label}:</b> <font name='Courier'>{m.length_mm:.2f} mm ({m.length_cm:.3f} cm)</font>"
            )

    combined_annot_data = [
        [Paragraph("<b>Planning Reference Targets</b>", table_header), Paragraph("<b>Preoperative Linear Measurements</b>", table_header)],
        [Paragraph("<br/>".join(targets_text), body_style), Paragraph("<br/>".join(meas_text), body_style)],
    ]
    t_annot = Table(combined_annot_data, colWidths=[260, 263])
    t_annot.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f1f5f9")),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("PADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    story.append(t_annot)
    story.append(Spacer(1, 6))

    # ── SECTION 7: PLANNING SESSION NOTES ─────────────────────────────────────
    story.append(Paragraph("6. User Planning Session Notes [USER ANNOTATION]", section_heading))
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#cbd5e1"), spaceAfter=4))

    notes_str = (report.planning_session_notes.content or "").strip()
    if not notes_str:
        story.append(Paragraph("<i>No planning notes entered in active session.</i>", body_style))
    else:
        story.append(
            Paragraph(
                f"<b>Session ID:</b> {report.planning_session_notes.session_id or 'default'}<br/>"
                f"<b>Author Notes:</b> {notes_str}",
                body_style,
            )
        )
    story.append(Spacer(1, 6))

    # ── SECTION 8: MANDATORY CLINICAL REVIEW ITEMS ────────────────────────────
    story.append(Paragraph("7. Mandatory Clinical Review Items [CLINICAL BOUNDARIES]", section_heading))
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#cbd5e1"), spaceAfter=4))
    story.append(
        Paragraph(
            "The following elements <b>CANNOT</b> be determined by this computational imaging prototype "
            "and require direct clinician / urologist evaluation:",
            meta_style,
        )
    )
    story.append(Spacer(1, 2))

    cr_rows = [
        [Paragraph("<b>Category</b>", table_header), Paragraph("<b>Non-Computational Clinical Boundary Statement</b>", table_header)]
    ]
    for cr in report.clinical_review_items:
        cr_rows.append(
            [
                Paragraph(cr.category.replace("_", " ").title(), table_cell),
                Paragraph(cr.statement, body_style),
            ]
        )
    t_cr = Table(cr_rows, colWidths=[110, 413])
    t_cr.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f1f5f9")),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("PADDING", (0, 0), (-1, -1), 3),
            ]
        )
    )
    story.append(t_cr)
    story.append(Spacer(1, 6))

    # ── SECTION 9: TECHNICAL LIMITATIONS & PROVENANCE ─────────────────────────
    story.append(Paragraph("8. Technical Limitations & Pipeline Provenance [AUDIT TRAIL]", section_heading))
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#cbd5e1"), spaceAfter=4))

    lim_items = [f"• <b>[{lim.domain.upper()}]</b> {lim.description}" for lim in report.system_limitations]
    p = report.provenance
    prov_text = (
        f"<b>CT Source:</b> {p.ct_source or 'Validated NIfTI volume'}<br/>"
        f"<b>Segmentation Model:</b> {p.segmentation_source}<br/>"
        f"<b>Lesion Model:</b> {p.lesion_model_source}<br/>"
        f"<b>Coordinate Engine:</b> {p.coordinate_system_source}<br/>"
        f"<b>Measurement Engine:</b> {p.measurement_source}<br/>"
        f"<b>Spatial Distance Engine:</b> {p.spatial_relationship_source}<br/>"
        f"<b>Generation Method:</b> {p.generation_method}"
    )

    prov_table_data = [
        [Paragraph("<b>Technical Limitations</b>", table_header), Paragraph("<b>Pipeline Provenance</b>", table_header)],
        [Paragraph("<br/>".join(lim_items), meta_style), Paragraph(prov_text, meta_style)],
    ]
    t_prov = Table(prov_table_data, colWidths=[260, 263])
    t_prov.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f1f5f9")),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("PADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    story.append(t_prov)

    # Compile document
    doc.build(story, canvasmaker=NumberedCanvas)
    return buf.getvalue()


# Singleton
preoperative_report_service = PreoperativeReportService()
report_service = preoperative_report_service
