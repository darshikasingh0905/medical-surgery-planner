import React, { useState, useEffect, useCallback } from 'react';
import { getPreoperativeReport, getPreoperativeReportPdf } from './api';

/**
 * PreoperativeReportModal — Day 22 Preoperative Report & Export Layer
 *
 * Provides a structured review modal for preoperative reports aggregated from
 * existing authoritative planning and explanation services.
 *
 * Supports:
 * - Audience toggle: Technical vs General
 * - Structured section rendering across all 15 report domains
 * - Computational provenance badges (model_inference, derived_computation, user_annotation, etc.)
 * - Explicit unavailable anatomical structure indicators
 * - Native PDF export via backend ReportLab generator
 * - Browser A4 print layout via targeted @media print rules
 *
 * ⚠️ Medical Safety: Research/educational prototype only. No clinical diagnoses,
 *    resectability claims, or autonomous operative advice.
 */
export default function PreoperativeReportModal({ caseId, onClose }) {
  const [report, setReport] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [audience, setAudience] = useState('technical');
  const [downloadingPdf, setDownloadingPdf] = useState(false);

  const fetchReport = useCallback(async (aud) => {
    if (!caseId) return;
    setLoading(true);
    setError(null);
    try {
      const data = await getPreoperativeReport(caseId, aud);
      setReport(data);
    } catch (err) {
      setError(err.message || 'Failed to generate preoperative report.');
    } finally {
      setLoading(false);
    }
  }, [caseId]);

  useEffect(() => {
    fetchReport(audience);
  }, [fetchReport, audience]);

  const handleAudienceChange = (newAudience) => {
    if (newAudience !== audience) {
      setAudience(newAudience);
    }
  };

  const handlePrint = () => {
    window.print();
  };

  const handleDownloadPdf = async () => {
    if (!caseId) return;
    setDownloadingPdf(true);
    try {
      const blob = await getPreoperativeReportPdf(caseId, audience);
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      const prefix = caseId.length >= 8 ? caseId.slice(0, 8) : caseId;
      link.download = `preoperative_report_${prefix}.pdf`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);
    } catch (err) {
      alert(`PDF Export Failed: ${err.message}`);
    } finally {
      setDownloadingPdf(false);
    }
  };

  return (
    <div className="report-modal-overlay" id="preoperative-report-modal-overlay">
      <div className="report-modal-container" id="preoperative-report-modal-container">
        {/* Modal Header Controls (Hidden during print) */}
        <div className="report-modal-header no-print">
          <div className="report-modal-title-group">
            <span className="report-modal-badge">REPORT & EXPORT</span>
            <h2 className="report-modal-title">Preoperative Computational Planning Report</h2>
          </div>

          <div className="report-modal-actions">
            <div className="report-audience-toggle" id="report-audience-toggle">
              <button
                type="button"
                className={`audience-btn ${audience === 'technical' ? 'active' : ''}`}
                onClick={() => handleAudienceChange('technical')}
                id="btn-report-audience-technical"
              >
                Technical
              </button>
              <button
                type="button"
                className={`audience-btn ${audience === 'general' ? 'active' : ''}`}
                onClick={() => handleAudienceChange('general')}
                id="btn-report-audience-general"
              >
                General
              </button>
            </div>

            <button
              type="button"
              className="report-btn report-btn--secondary"
              onClick={handlePrint}
              disabled={loading || !report}
              id="btn-print-report"
              title="Print report or save to PDF via browser print"
            >
              🖨️ Print Report
            </button>

            <button
              type="button"
              className="report-btn report-btn--primary"
              onClick={handleDownloadPdf}
              disabled={loading || !report || downloadingPdf}
              id="btn-download-pdf"
              title="Download standardized A4 PDF"
            >
              {downloadingPdf ? 'Generating PDF…' : '📥 Download PDF'}
            </button>

            <button
              type="button"
              className="report-btn report-btn--close"
              onClick={onClose}
              id="btn-close-report-modal"
              title="Close Report"
            >
              ✕
            </button>
          </div>
        </div>

        {/* Modal Scrollable Body */}
        <div className="report-modal-body" id="printable-report-area">
          {loading && (
            <div className="report-loading-state" id="report-loading-state">
              <div className="report-spinner" />
              <p>Aggregating computational findings and planning summary…</p>
            </div>
          )}

          {error && (
            <div className="report-error-state" id="report-error-state">
              <span className="report-error-icon">⚠️</span>
              <p>{error}</p>
              <button type="button" onClick={() => fetchReport(audience)} className="report-btn report-btn--secondary">
                Retry
              </button>
            </div>
          )}

          {!loading && !error && report && (
            <div className="report-document" id="preoperative-report-document">
              {/* Document Banner */}
              <header className="report-doc-header">
                <div className="report-header-top">
                  <div>
                    <h1 className="report-doc-title">Preoperative Planning Report</h1>
                    <div className="report-doc-subtitle">
                      Computational Aggregation & Procedural Context — {report.metadata?.target_audience?.toUpperCase()} AUDIENCE
                    </div>
                  </div>
                  <div className="report-doc-id-box">
                    <div className="report-id-label">REPORT ID</div>
                    <div className="report-id-val font-mono">{report.metadata?.report_id}</div>
                    <div className="report-gen-time">
                      Generated: {new Date(report.metadata?.generated_at_utc).toLocaleString()}
                    </div>
                  </div>
                </div>

                {/* Primary Governance Notice */}
                <div className="report-governance-box">
                  <div className="gov-box-header">
                    <span className="gov-box-icon">⚖️</span>
                    <strong>{report.governance?.statement}</strong>
                  </div>
                  <ul className="gov-box-list">
                    {report.governance?.rules?.map((rule, idx) => (
                      <li key={idx}>{rule}</li>
                    ))}
                  </ul>
                </div>
              </header>

              {/* Section 1: Overview & Imaging Information */}
              <div className="report-two-col-grid">
                <section className="report-card">
                  <h3 className="report-card-heading">Case Overview</h3>
                  <table className="report-data-table">
                    <tbody>
                      <tr>
                        <th>Case ID:</th>
                        <td className="font-mono">{report.case_overview?.case_id}</td>
                      </tr>
                      <tr>
                        <th>Target Anatomy:</th>
                        <td>{report.case_overview?.target_anatomy || 'Not specified'}</td>
                      </tr>
                      <tr>
                        <th>Status:</th>
                        <td><span className="badge-tag badge-tag--completed">{report.case_overview?.status}</span></td>
                      </tr>
                      <tr>
                        <th>Summary:</th>
                        <td>{report.case_overview?.narrative_summary}</td>
                      </tr>
                    </tbody>
                  </table>
                </section>

                <section className="report-card">
                  <h3 className="report-card-heading">Imaging Acquisition</h3>
                  <table className="report-data-table">
                    <tbody>
                      <tr>
                        <th>Modality:</th>
                        <td>{report.imaging_info?.modality}</td>
                      </tr>
                      <tr>
                        <th>Dimensions:</th>
                        <td className="font-mono">
                          {report.imaging_info?.dimensions?.join(' × ') || 'N/A'} voxels
                        </td>
                      </tr>
                      <tr>
                        <th>Voxel Spacing:</th>
                        <td className="font-mono">
                          {report.imaging_info?.spacing_mm?.map(s => s.toFixed(3)).join(' × ') || 'N/A'} mm
                        </td>
                      </tr>
                      <tr>
                        <th>Orientation:</th>
                        <td className="font-mono">{report.imaging_info?.orientation || 'N/A'}</td>
                      </tr>
                      <tr>
                        <th>Source:</th>
                        <td><span className="provenance-tag">{report.imaging_info?.provenance}</span></td>
                      </tr>
                    </tbody>
                  </table>
                </section>
              </div>

              {/* Section 2: Computational Findings (Lesions) */}
              <section className="report-section">
                <div className="section-title-wrap">
                  <h3 className="report-section-title">Computational Findings (Model Segmentations)</h3>
                  <span className="provenance-tag">model_inference</span>
                </div>
                {(!report.computational_findings || report.computational_findings.length === 0) ? (
                  <p className="report-empty-text">No computational findings identified in this dataset.</p>
                ) : (
                  <div className="report-table-scroll">
                    <table className="report-data-table report-data-table--bordered">
                      <thead>
                        <tr>
                          <th>Finding ID</th>
                          <th>Class</th>
                          <th>Volume (mL)</th>
                          <th>Physical Centroid (mm)</th>
                          <th>Bounding Box (mm)</th>
                          <th>Host Organ</th>
                          <th>Clinical Review</th>
                        </tr>
                      </thead>
                      <tbody>
                        {report.computational_findings.map((f) => (
                          <tr key={f.finding_id}>
                            <td className="font-mono font-bold">{f.finding_id}</td>
                            <td><span className="badge-tag badge-tag--finding">{f.class_name}</span></td>
                            <td className="font-mono">{f.volume_ml.toFixed(4)} mL</td>
                            <td className="font-mono">
                              [{f.centroid_physical_mm.map(c => c.toFixed(2)).join(', ')}]
                            </td>
                            <td className="font-mono">
                              {f.bounding_box_mm.map(b => b.toFixed(1)).join(' × ')}
                            </td>
                            <td>{f.host_organ || 'Unassigned'}</td>
                            <td><span className="badge-tag badge-tag--review">{f.review_requirement}</span></td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </section>

              {/* Section 3: Anatomical Structures (Available & Unavailable) */}
              <section className="report-section">
                <div className="section-title-wrap">
                  <h3 className="report-section-title">Segmented & Tracked Anatomical Structures</h3>
                  <span className="provenance-tag">model_inference / derived_computation</span>
                </div>
                <div className="report-table-scroll">
                  <table className="report-data-table report-data-table--bordered">
                    <thead>
                      <tr>
                        <th>Structure</th>
                        <th>Status</th>
                        <th>Volume (mL)</th>
                        <th>Physical Centroid (mm)</th>
                        <th>Computational Availability</th>
                      </tr>
                    </thead>
                    <tbody>
                      {report.anatomical_structures?.map((s) => (
                        <tr key={s.structure_id} className={!s.available ? 'row-unavailable' : ''}>
                          <td className="font-bold">{s.display_name}</td>
                          <td>
                            {s.available ? (
                              <span className="badge-tag badge-tag--available">Available</span>
                            ) : (
                              <span className="badge-tag badge-tag--unavailable">Unavailable</span>
                            )}
                          </td>
                          <td className="font-mono">
                            {s.volume_ml != null ? `${s.volume_ml.toFixed(2)} mL` : '—'}
                          </td>
                          <td className="font-mono">
                            {s.centroid_physical_mm
                              ? `[${s.centroid_physical_mm.map(c => c.toFixed(1)).join(', ')}]`
                              : '—'}
                          </td>
                          <td className="text-muted text-sm">{s.availability_note || 'Segmented structure'}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </section>

              {/* Section 4: Spatial Relationships & Objective Distances */}
              <section className="report-section">
                <div className="section-title-wrap">
                  <h3 className="report-section-title">Objective Spatial Relationships & Distances</h3>
                  <span className="provenance-tag">derived_computation</span>
                </div>
                {(!report.spatial_relationships || report.spatial_relationships.length === 0) ? (
                  <p className="report-empty-text">No spatial relationship metrics calculated.</p>
                ) : (
                  <div className="report-table-scroll">
                    <table className="report-data-table report-data-table--bordered">
                      <thead>
                        <tr>
                          <th>Source Finding</th>
                          <th>Target Structure</th>
                          <th>Min Euclidean Distance</th>
                          <th>Centroid Distance</th>
                          <th>Overlap Detected</th>
                        </tr>
                      </thead>
                      <tbody>
                        {report.spatial_relationships.map((rel, idx) => (
                          <tr key={idx}>
                            <td className="font-mono font-bold">{rel.finding_id}</td>
                            <td>{rel.target_structure}</td>
                            <td className="font-mono font-bold text-accent">
                              {rel.min_distance_mm != null ? `${rel.min_distance_mm.toFixed(3)} mm` : 'N/A'}
                            </td>
                            <td className="font-mono">
                              {rel.centroid_distance_mm != null ? `${rel.centroid_distance_mm.toFixed(3)} mm` : 'N/A'}
                            </td>
                            <td>
                              {rel.overlap_detected ? (
                                <span className="badge-tag badge-tag--overlap">Yes (Geometric Coincidence)</span>
                              ) : (
                                <span className="badge-tag badge-tag--no-overlap">No</span>
                              )}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </section>

              {/* Section 5: Planning Targets & Interactive Measurements */}
              <div className="report-two-col-grid">
                <section className="report-card">
                  <div className="section-title-wrap">
                    <h3 className="report-card-heading">Planning Targets</h3>
                    <span className="provenance-tag">model_inference / user_annotation</span>
                  </div>
                  {(!report.planning_targets || report.planning_targets.length === 0) ? (
                    <p className="report-empty-text">No planning targets recorded.</p>
                  ) : (
                    <ul className="report-target-list">
                      {report.planning_targets.map((tgt) => (
                        <li key={tgt.target_id} className="target-item">
                          <div className="target-item-header">
                            <span className="font-mono font-bold">{tgt.label}</span>
                            <span className="provenance-tag-sm">{tgt.provenance}</span>
                          </div>
                          <div className="target-item-coords font-mono text-xs">
                            Voxel: [{tgt.voxel_coordinate.join(', ')}] | Physical: [{tgt.physical_coordinate_mm.map(p => p.toFixed(1)).join(', ')}] mm
                          </div>
                        </li>
                      ))}
                    </ul>
                  )}
                </section>

                <section className="report-card">
                  <div className="section-title-wrap">
                    <h3 className="report-card-heading">Planning Session Measurements</h3>
                    <span className="provenance-tag">user_annotation</span>
                  </div>
                  {(!report.planning_measurements || report.planning_measurements.length === 0) ? (
                    <p className="report-empty-text">No user caliper measurements recorded in session.</p>
                  ) : (
                    <ul className="report-measurement-list">
                      {report.planning_measurements.map((m) => (
                        <li key={m.measurement_id} className="measurement-item">
                          <div className="measurement-item-header">
                            <span className="font-mono font-bold">{m.measurement_id.slice(0, 8)}</span>
                            <span className="font-mono font-bold text-accent">{m.length_mm.toFixed(2)} mm</span>
                          </div>
                          <div className="text-xs text-muted">
                            Plane: {m.slice_plane} (slice {m.slice_index}) | Label: {m.label || 'Unlabeled'}
                          </div>
                        </li>
                      ))}
                    </ul>
                  )}
                </section>
              </div>

              {/* Section 6: Planning Session Notes */}
              <section className="report-section">
                <div className="section-title-wrap">
                  <h3 className="report-section-title">Planning Session Notes</h3>
                  <span className="provenance-tag">user_annotation</span>
                </div>
                <div className="report-notes-box">
                  {report.planning_session_notes?.content ? (
                    <p className="report-notes-text">{report.planning_session_notes.content}</p>
                  ) : (
                    <p className="report-empty-text">No planner notes recorded for this case session.</p>
                  )}
                  <div className="report-notes-meta">
                    Author: {report.planning_session_notes?.author || 'Unassigned'} | Provenance: {report.planning_session_notes?.provenance}
                  </div>
                </div>
              </section>

              {/* Section 7: Procedural Context & Clinical Review Items */}
              <div className="report-two-col-grid">
                <section className="report-card">
                  <div className="section-title-wrap">
                    <h3 className="report-card-heading">Procedural Context</h3>
                    <span className="provenance-tag">explanatory_context</span>
                  </div>
                  {(!report.procedural_context || report.procedural_context.length === 0) ? (
                    <p className="report-empty-text">No procedural context available.</p>
                  ) : (
                    <ul className="report-context-list">
                      {report.procedural_context.map((ctx, idx) => (
                        <li key={idx} className="context-item">
                          <strong>{ctx.topic}:</strong> {ctx.summary}
                        </li>
                      ))}
                    </ul>
                  )}
                </section>

                <section className="report-card">
                  <div className="section-title-wrap">
                    <h3 className="report-card-heading">Mandatory Clinical Review Items</h3>
                    <span className="provenance-tag">mandatory_clinical_review</span>
                  </div>
                  {(!report.clinical_review_items || report.clinical_review_items.length === 0) ? (
                    <p className="report-empty-text">No clinical review items specified.</p>
                  ) : (
                    <ul className="report-review-list">
                      {report.clinical_review_items.map((item, idx) => (
                        <li key={idx} className="review-item">
                          <span className="review-dot">⚠️</span>
                          <div>
                            <strong>{item.item}:</strong> {item.rationale}
                          </div>
                        </li>
                      ))}
                    </ul>
                  )}
                </section>
              </div>

              {/* Section 8: System Limitations */}
              <section className="report-section">
                <h3 className="report-section-title">System Limitations & Scope Boundaries</h3>
                <div className="limitations-grid">
                  {report.system_limitations?.map((lim, idx) => (
                    <div key={idx} className="limitation-card">
                      <div className="limitation-domain font-bold">{lim.domain}</div>
                      <div className="limitation-detail text-sm">{lim.limitation}</div>
                      <div className="limitation-action text-xs text-muted">Action: {lim.recommended_action}</div>
                    </div>
                  ))}
                </div>
              </section>

              {/* Section 9: Audit Trail & Data Provenance */}
              <footer className="report-doc-footer">
                <h4 className="footer-title">Audit Trail & Computational Lineage</h4>
                <div className="footer-meta-grid">
                  <div><strong>Report Engine:</strong> {report.provenance?.report_generator}</div>
                  <div><strong>Summary Service:</strong> {report.provenance?.summary_service}</div>
                  <div><strong>Explanation Engine:</strong> {report.provenance?.explanation_service}</div>
                  <div><strong>Deterministic Hash:</strong> <span className="font-mono">{report.provenance?.deterministic_hash}</span></div>
                </div>
                <div className="footer-disclaimer">
                  {report.governance?.statement} — {report.governance?.mandatory_disclaimer}
                </div>
              </footer>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
