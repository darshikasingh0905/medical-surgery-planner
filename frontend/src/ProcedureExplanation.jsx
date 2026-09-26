import React, { useState, useEffect, useCallback } from 'react';
import { getProcedureExplanation } from './api';

/**
 * ProcedureExplanation — Day 21 Procedure Explanation Panel
 *
 * Renders the structured procedure explanation for a case.
 * Sections are interactive: clicking a finding, anatomy item,
 * measurement, or target delegates to existing workspace handlers.
 *
 * MEDICAL SAFETY:
 * This panel organizes computational imaging findings and provides
 * general procedural context ONLY. It does not diagnose disease,
 * recommend a procedure, or constitute clinical advice.
 */
const ProcedureExplanation = ({
  caseId,
  // Handlers from PlanningWorkspace (reuse existing)
  onSelectFinding,
  onSelectStructure,
  onSelectMeasurement,
  onSelectTarget,
  // Currently selected items (for highlighting)
  selectedLesion,
  selectedStructure,
  selectedMeasurement,
  selectedTarget,
}) => {
  const [explanation, setExplanation] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [audience, setAudience] = useState('technical');
  const [activeSection, setActiveSection] = useState('overview');
  const [provenanceExpanded, setProvenanceExpanded] = useState(false);

  const loadExplanation = useCallback(
    async (aud) => {
      if (!caseId) return;
      setLoading(true);
      setError(null);
      try {
        const data = await getProcedureExplanation(caseId, aud);
        setExplanation(data);
      } catch (err) {
        setError(err.message || 'Failed to load procedure explanation');
      } finally {
        setLoading(false);
      }
    },
    [caseId]
  );

  useEffect(() => {
    loadExplanation(audience);
  }, [caseId, audience, loadExplanation]);

  const handleAudienceChange = (aud) => {
    setAudience(aud);
  };

  if (loading) {
    return (
      <div className="proc-exp-loading" id="procedure-explanation-loading">
        <div className="proc-exp-spinner" />
        <span>Generating procedure explanation…</span>
      </div>
    );
  }

  if (error) {
    return (
      <div className="proc-exp-error" id="procedure-explanation-error">
        <span className="proc-exp-error-icon">⚠️</span>
        <span>{error}</span>
      </div>
    );
  }

  if (!explanation) return null;

  const {
    case_overview,
    computational_findings,
    relevant_anatomy,
    spatial_relationships,
    measurements,
    planning_targets,
    procedural_context,
    clinical_review_items,
    limitations,
    provenance,
    governance_statement,
    generated_at,
  } = explanation;

  const availableAnatomy = (relevant_anatomy || []).filter((a) => a.available);
  const unavailableAnatomy = (relevant_anatomy || []).filter((a) => !a.available);
  const availableRels = (spatial_relationships || []).filter((r) => r.available);

  const SECTIONS = [
    { id: 'overview', label: 'Case Overview' },
    { id: 'finding', label: 'Computational Finding' },
    { id: 'location', label: 'Location' },
    { id: 'anatomy', label: 'Relevant Anatomy' },
    { id: 'relationships', label: 'Spatial Relationships' },
    { id: 'measurements', label: 'Measurements' },
    { id: 'targets', label: 'Planning Targets' },
    { id: 'context', label: 'Procedural Context' },
    { id: 'clinical_review', label: 'Clinical Review' },
    { id: 'limitations', label: 'Limitations' },
  ];

  return (
    <div className="proc-exp-root" id="procedure-explanation-panel">
      {/* Header */}
      <div className="proc-exp-header">
        <div className="proc-exp-title-row">
          <h2 className="proc-exp-title">Preoperative Case Explanation</h2>
          <div className="proc-exp-meta">
            <span className="proc-exp-timestamp" title={generated_at}>
              Generated {new Date(generated_at).toLocaleTimeString()}
            </span>
            <span className="proc-exp-method-badge" title={provenance?.generation_method}>
              Deterministic · No AI Generation
            </span>
          </div>
        </div>

        {/* Audience switcher */}
        <div className="proc-exp-audience-switcher">
          <span className="audience-label">Audience:</span>
          <button
            id="btn-audience-technical"
            className={`audience-btn ${audience === 'technical' ? 'active' : ''}`}
            onClick={() => handleAudienceChange('technical')}
            type="button"
          >
            Technical
          </button>
          <button
            id="btn-audience-general"
            className={`audience-btn ${audience === 'general' ? 'active' : ''}`}
            onClick={() => handleAudienceChange('general')}
            type="button"
          >
            General
          </button>
        </div>

        {/* Section navigation */}
        <nav className="proc-exp-nav" aria-label="Explanation sections">
          {SECTIONS.map((sec) => (
            <button
              key={sec.id}
              id={`proc-exp-nav-${sec.id}`}
              className={`proc-exp-nav-btn ${activeSection === sec.id ? 'active' : ''}`}
              onClick={() => setActiveSection(sec.id)}
              type="button"
            >
              {sec.label}
            </button>
          ))}
        </nav>
      </div>

      {/* Content */}
      <div className="proc-exp-content">

        {/* ── CASE OVERVIEW ─────────────────────────────────────── */}
        {activeSection === 'overview' && (
          <section className="proc-exp-section" id="proc-exp-section-overview">
            <h3 className="proc-exp-section-heading">Case Overview</h3>
            <p className="proc-exp-section-subtext">CT-based computational planning case</p>

            <div className="proc-exp-card">
              <div className="proc-exp-kv-grid">
                <div className="proc-exp-kv">
                  <span className="proc-exp-k">Case ID</span>
                  <span className="proc-exp-v font-mono" title={caseId}>{caseId?.slice(0, 8)}…</span>
                </div>
                <div className="proc-exp-kv">
                  <span className="proc-exp-k">Status</span>
                  <span className="proc-exp-v">
                    <span className="proc-exp-status-badge">{case_overview?.status || 'completed'}</span>
                  </span>
                </div>
                <div className="proc-exp-kv">
                  <span className="proc-exp-k">CT Dimensions</span>
                  <span className="proc-exp-v font-mono">
                    {case_overview?.scan_dimensions
                      ? case_overview.scan_dimensions.join(' × ')
                      : '—'} voxels
                  </span>
                </div>
                <div className="proc-exp-kv">
                  <span className="proc-exp-k">Voxel Spacing</span>
                  <span className="proc-exp-v font-mono">
                    {case_overview?.voxel_spacing_mm
                      ? case_overview.voxel_spacing_mm.map((s) => s.toFixed(2)).join(' × ')
                      : '—'} mm
                  </span>
                </div>
                <div className="proc-exp-kv">
                  <span className="proc-exp-k">Orientation</span>
                  <span className="proc-exp-v font-mono">
                    {case_overview?.orientation ? case_overview.orientation.join('') : '—'}
                  </span>
                </div>
                <div className="proc-exp-kv">
                  <span className="proc-exp-k">HU Range</span>
                  <span className="proc-exp-v font-mono">
                    {case_overview?.intensity_range_hu
                      ? `${case_overview.intensity_range_hu[0]} – ${case_overview.intensity_range_hu[1]}`
                      : '—'}
                  </span>
                </div>
              </div>
            </div>
          </section>
        )}

        {/* ── COMPUTATIONAL FINDING ─────────────────────────────── */}
        {activeSection === 'finding' && (
          <section className="proc-exp-section" id="proc-exp-section-finding">
            <h3 className="proc-exp-section-heading">Computational Finding</h3>
            <p className="proc-exp-section-subtext">
              Model-predicted segmentation output — KiTS23 renal class inference
            </p>

            {computational_findings.length === 0 ? (
              <div className="proc-exp-empty">No computational findings for this case.</div>
            ) : (
              computational_findings.map((f) => {
                const isSelected = selectedLesion?.lesion_id === f.finding_id;
                return (
                  <div
                    key={f.finding_id}
                    id={`proc-exp-finding-${f.finding_id}`}
                    className={`proc-exp-card proc-exp-card--finding ${isSelected ? 'proc-exp-card--selected' : ''}`}
                    onClick={() => onSelectFinding && onSelectFinding({
                      lesion_id: f.finding_id,
                      computational_interpretation: f.computational_interpretation,
                      centroid_mm: f.centroid_physical_mm,
                      volume_ml: f.volume_ml,
                      host_organ: f.host_organ,
                    })}
                    title="Click to focus 3D viewer and MPR on this finding"
                    role="button"
                    tabIndex={0}
                    onKeyDown={(e) => e.key === 'Enter' && onSelectFinding && onSelectFinding({
                      lesion_id: f.finding_id,
                      computational_interpretation: f.computational_interpretation,
                      centroid_mm: f.centroid_physical_mm,
                    })}
                  >
                    <div className="proc-exp-finding-header">
                      <span className="proc-exp-finding-class-badge">{f.model_class?.toUpperCase()}</span>
                      <span className="proc-exp-finding-id font-mono">{f.finding_id}</span>
                      <button
                        className="proc-exp-focus-btn"
                        onClick={(e) => {
                          e.stopPropagation();
                          onSelectFinding && onSelectFinding({
                            lesion_id: f.finding_id,
                            computational_interpretation: f.computational_interpretation,
                            centroid_mm: f.centroid_physical_mm,
                            volume_ml: f.volume_ml,
                          });
                        }}
                        title="Focus 3D + MPR on this finding"
                      >
                        🎯 Focus
                      </button>
                    </div>

                    <p className="proc-exp-interp">{f.computational_interpretation}</p>

                    <div className="proc-exp-kv-grid">
                      <div className="proc-exp-kv">
                        <span className="proc-exp-k">Host Organ</span>
                        <span className="proc-exp-v">{f.host_organ_display || f.host_organ || '—'}</span>
                      </div>
                      <div className="proc-exp-kv">
                        <span className="proc-exp-k">Volume</span>
                        <span className="proc-exp-v font-mono">
                          {f.volume_ml != null ? `${f.volume_ml.toFixed(4)} mL` : '—'}
                        </span>
                      </div>
                      <div className="proc-exp-kv">
                        <span className="proc-exp-k">Bounding Box</span>
                        <span className="proc-exp-v font-mono">
                          {f.dimensions_mm
                            ? `${f.dimensions_mm.map((d) => d.toFixed(1)).join(' × ')} mm`
                            : '—'}
                        </span>
                      </div>
                    </div>

                    <div className="proc-exp-provenance-note">
                      <span className="proc-exp-prov-label">Source:</span>
                      <span className="proc-exp-prov-text">{f.source_provenance}</span>
                    </div>
                  </div>
                );
              })
            )}
          </section>
        )}

        {/* ── WHERE IT IS (LOCATION) ────────────────────────────── */}
        {activeSection === 'location' && (
          <section className="proc-exp-section" id="proc-exp-section-location">
            <h3 className="proc-exp-section-heading">Location</h3>
            <p className="proc-exp-section-subtext">Centroid coordinates in CT coordinate space</p>

            {computational_findings.length === 0 ? (
              <div className="proc-exp-empty">No finding location data available.</div>
            ) : (
              computational_findings.map((f) => (
                <div key={f.finding_id} className="proc-exp-card" id={`proc-exp-location-${f.finding_id}`}>
                  <h4 className="proc-exp-subheading">{f.finding_id}</h4>

                  <div className="proc-exp-kv-grid">
                    <div className="proc-exp-kv">
                      <span className="proc-exp-k">Voxel Centroid</span>
                      <span className="proc-exp-v font-mono">
                        {f.centroid_voxel
                          ? `[${f.centroid_voxel.join(', ')}]`
                          : '—'}
                      </span>
                    </div>
                    <div className="proc-exp-kv">
                      <span className="proc-exp-k">Physical Centroid (mm)</span>
                      <span className="proc-exp-v font-mono">
                        {f.centroid_physical_mm
                          ? `[${f.centroid_physical_mm.map((c) => c.toFixed(1)).join(', ')}]`
                          : '—'}
                      </span>
                    </div>
                    <div className="proc-exp-kv">
                      <span className="proc-exp-k">Host Organ</span>
                      <span className="proc-exp-v">{f.host_organ_display || f.host_organ || '—'}</span>
                    </div>
                    <div className="proc-exp-kv">
                      <span className="proc-exp-k">MPR Navigation</span>
                      <span className="proc-exp-v">
                        <button
                          className="proc-exp-nav-to-btn"
                          onClick={() => onSelectFinding && onSelectFinding({
                            lesion_id: f.finding_id,
                            centroid_mm: f.centroid_physical_mm,
                            computational_interpretation: f.computational_interpretation,
                            volume_ml: f.volume_ml,
                          })}
                        >
                          Navigate to centroid →
                        </button>
                      </span>
                    </div>
                  </div>

                  <div className="proc-exp-provenance-note">
                    <span className="proc-exp-prov-label">Coordinate system:</span>
                    <span className="proc-exp-prov-text">{provenance?.coordinate_system_source}</span>
                  </div>
                </div>
              ))
            )}
          </section>
        )}

        {/* ── RELEVANT ANATOMY ─────────────────────────────────── */}
        {activeSection === 'anatomy' && (
          <section className="proc-exp-section" id="proc-exp-section-anatomy">
            <h3 className="proc-exp-section-heading">Relevant Anatomy</h3>
            <p className="proc-exp-section-subtext">
              TotalSegmentator anatomical segmentation — availability verified on disk
            </p>

            <div className="proc-exp-anatomy-grid">
              {availableAnatomy.map((a) => {
                const isSelected = selectedStructure === a.structure_id;
                return (
                  <div
                    key={a.structure_id}
                    id={`proc-exp-anatomy-${a.structure_id}`}
                    className={`proc-exp-anatomy-card proc-exp-anatomy-card--available ${isSelected ? 'proc-exp-card--selected' : ''}`}
                    onClick={() => onSelectStructure && onSelectStructure(a.structure_id)}
                    role="button"
                    tabIndex={0}
                    onKeyDown={(e) => e.key === 'Enter' && onSelectStructure && onSelectStructure(a.structure_id)}
                    title="Click to focus this structure in 3D viewer"
                  >
                    <div className="proc-exp-anatomy-header">
                      <span className="proc-exp-color-dot" style={{ backgroundColor: a.color || '#94a3b8' }} />
                      <span className="proc-exp-anatomy-name">{a.display_name}</span>
                      <span className="proc-exp-avail-tag proc-exp-avail-tag--yes">Available</span>
                      <button
                        className="proc-exp-focus-btn"
                        onClick={(e) => { e.stopPropagation(); onSelectStructure && onSelectStructure(a.structure_id); }}
                        title="Focus structure"
                      >🎯</button>
                    </div>
                    <div className="proc-exp-anatomy-meta">
                      <span className="proc-exp-k">Category:</span>
                      <span className="proc-exp-v">{a.category}</span>
                      {a.relationship_to_finding && (
                        <>
                          <span className="proc-exp-k">Relationship:</span>
                          <span className="proc-exp-v proc-exp-rel-text">{a.relationship_to_finding}</span>
                        </>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>

            {unavailableAnatomy.length > 0 && (
              <details className="proc-exp-unavailable-details">
                <summary className="proc-exp-unavailable-summary">
                  {unavailableAnatomy.length} structure(s) not segmented in this case
                </summary>
                <div className="proc-exp-unavailable-list">
                  {unavailableAnatomy.map((a) => (
                    <div key={a.structure_id} className="proc-exp-anatomy-card proc-exp-anatomy-card--unavailable">
                      <span className="proc-exp-anatomy-name">{a.display_name}</span>
                      <span className="proc-exp-avail-tag proc-exp-avail-tag--no">Not Segmented</span>
                      <p className="proc-exp-unavail-reason">{a.unavailability_reason}</p>
                    </div>
                  ))}
                </div>
              </details>
            )}

            <div className="proc-exp-provenance-note">
              <span className="proc-exp-prov-label">Source:</span>
              <span className="proc-exp-prov-text">{provenance?.anatomy_registry_source}</span>
            </div>
          </section>
        )}

        {/* ── SPATIAL RELATIONSHIPS ─────────────────────────────── */}
        {activeSection === 'relationships' && (
          <section className="proc-exp-section" id="proc-exp-section-relationships">
            <h3 className="proc-exp-section-heading">Computational Spatial Relationships</h3>
            <p className="proc-exp-section-subtext">
              Physical minimum Euclidean distances between primary finding and segmented structures
            </p>
            <p className="proc-exp-disclaimer-inline">
              Terminology: "Computational minimum distance" — not surgical margin or clinical clearance.
            </p>

            <div className="proc-exp-rel-list">
              {availableRels.length === 0 ? (
                <div className="proc-exp-empty">No spatial relationships computed for this case.</div>
              ) : (
                availableRels.map((rel) => {
                  const isOverlap = rel.overlap === true;
                  return (
                    <div
                      key={rel.target_id}
                      id={`proc-exp-rel-${rel.target_id}`}
                      className={`proc-exp-rel-card ${isOverlap ? 'proc-exp-rel-card--overlap' : ''}`}
                      onClick={() => onSelectStructure && onSelectStructure(rel.target_id)}
                      role="button"
                      tabIndex={0}
                      title="Click to focus this structure"
                    >
                      <div className="proc-exp-rel-header">
                        <span className="proc-exp-rel-name">{rel.target_display_name}</span>
                        <span className={`proc-exp-rel-badge ${isOverlap ? 'badge-overlap' : 'badge-sep'}`}>
                          {isOverlap ? 'Overlap' : 'Separated'}
                        </span>
                      </div>
                      <div className="proc-exp-rel-metric">
                        <span className="proc-exp-k">Computational minimum distance</span>
                        <span className="proc-exp-v font-mono proc-exp-dist-val">
                          {isOverlap
                            ? '0.00 mm (overlap)'
                            : rel.distance_mm != null
                            ? `${rel.distance_mm.toFixed(2)} mm`
                            : '—'}
                        </span>
                      </div>
                    </div>
                  );
                })
              )}
            </div>

            <div className="proc-exp-provenance-note">
              <span className="proc-exp-prov-label">Source:</span>
              <span className="proc-exp-prov-text">{provenance?.spatial_relationship_source}</span>
            </div>
          </section>
        )}

        {/* ── MEASUREMENTS ─────────────────────────────────────── */}
        {activeSection === 'measurements' && (
          <section className="proc-exp-section" id="proc-exp-section-measurements">
            <h3 className="proc-exp-section-heading">Measurements</h3>
            <p className="proc-exp-section-subtext">
              Preoperative geometric measurements — Euclidean distance in physical CT space
            </p>

            {measurements.length === 0 ? (
              <div className="proc-exp-empty">
                No measurements recorded. Use Measure Mode in the Planning Workspace to add measurements.
              </div>
            ) : (
              measurements.map((m) => {
                const isSelected = selectedMeasurement?.measurement_id === m.measurement_id;
                return (
                  <div
                    key={m.measurement_id}
                    id={`proc-exp-meas-${m.measurement_id}`}
                    className={`proc-exp-card ${isSelected ? 'proc-exp-card--selected' : ''}`}
                    onClick={() => onSelectMeasurement && onSelectMeasurement({
                      measurement_id: m.measurement_id,
                      label: m.label,
                      distance_mm: m.value_mm,
                      distance_cm: m.value_cm,
                    })}
                    role="button"
                    tabIndex={0}
                    title="Click to focus this measurement"
                  >
                    <div className="proc-exp-meas-header">
                      <span className="proc-exp-meas-label">{m.label}</span>
                      <span className="proc-exp-meas-val font-mono">{m.value_mm.toFixed(2)} mm</span>
                    </div>
                    <div className="proc-exp-meas-meta">
                      <span className="proc-exp-k">Type</span>
                      <span className="proc-exp-v">{m.measurement_type.replace('_', ' ')}</span>
                      <span className="proc-exp-k">In cm</span>
                      <span className="proc-exp-v font-mono">{m.value_cm.toFixed(3)} cm</span>
                    </div>
                    <div className="proc-exp-provenance-note">
                      <span className="proc-exp-prov-label">Source:</span>
                      <span className="proc-exp-prov-text">{m.source_service}</span>
                    </div>
                  </div>
                );
              })
            )}

            <div className="proc-exp-provenance-note" style={{ marginTop: '8px' }}>
              <span className="proc-exp-prov-label">Measurement service:</span>
              <span className="proc-exp-prov-text">{provenance?.measurement_source}</span>
            </div>
          </section>
        )}

        {/* ── PLANNING TARGETS ─────────────────────────────────── */}
        {activeSection === 'targets' && (
          <section className="proc-exp-section" id="proc-exp-section-targets">
            <h3 className="proc-exp-section-heading">Planning Targets</h3>
            <p className="proc-exp-section-subtext">
              Model-derived and user-created planning reference points
            </p>

            {planning_targets.length === 0 ? (
              <div className="proc-exp-empty">No planning targets for this case.</div>
            ) : (
              planning_targets.map((t) => {
                const isSelected = selectedTarget?.target_id === t.target_id;
                const isModel = t.source === 'model';
                return (
                  <div
                    key={t.target_id}
                    id={`proc-exp-target-${t.target_id}`}
                    className={`proc-exp-card ${isSelected ? 'proc-exp-card--selected' : ''}`}
                    onClick={() => onSelectTarget && onSelectTarget({
                      target_id: t.target_id,
                      label: t.label,
                      voxel_coordinate: t.voxel_coordinate,
                      physical_coordinate: t.physical_coordinate,
                      source: t.source,
                      target_type: t.target_type,
                    })}
                    role="button"
                    tabIndex={0}
                    title="Click to navigate to this planning target"
                  >
                    <div className="proc-exp-target-header">
                      <span className={`proc-exp-target-dot ${isModel ? 'dot-cyan' : 'dot-amber'}`} />
                      <span className="proc-exp-target-label">{t.label}</span>
                      <span className="proc-exp-source-badge">{isModel ? 'MODEL' : 'USER'}</span>
                    </div>
                    <div className="proc-exp-kv-grid">
                      <div className="proc-exp-kv">
                        <span className="proc-exp-k">Voxel</span>
                        <span className="proc-exp-v font-mono">[{t.voxel_coordinate.join(', ')}]</span>
                      </div>
                      <div className="proc-exp-kv">
                        <span className="proc-exp-k">Physical (mm)</span>
                        <span className="proc-exp-v font-mono">
                          [{t.physical_coordinate.map((c) => c.toFixed(1)).join(', ')}]
                        </span>
                      </div>
                    </div>
                  </div>
                );
              })
            )}
          </section>
        )}

        {/* ── GENERAL PROCEDURAL CONTEXT ────────────────────────── */}
        {activeSection === 'context' && (
          <section className="proc-exp-section" id="proc-exp-section-context">
            <h3 className="proc-exp-section-heading">General Procedural Context</h3>
            <div className="proc-exp-context-disclaimer">
              {procedural_context?.disclaimer}
            </div>

            <div className="proc-exp-context-list">
              {(procedural_context?.items || []).map((item, idx) => (
                <div key={idx} className="proc-exp-context-item">
                  <h4 className="proc-exp-context-heading">{item.heading}</h4>
                  <p className="proc-exp-context-text">{item.text}</p>
                </div>
              ))}
            </div>
          </section>
        )}

        {/* ── CLINICAL REVIEW ──────────────────────────────────── */}
        {activeSection === 'clinical_review' && (
          <section className="proc-exp-section" id="proc-exp-section-clinical-review">
            <h3 className="proc-exp-section-heading">Clinical Review Items</h3>
            <p className="proc-exp-section-subtext">
              Items that cannot be determined by this computational system and require clinical review
            </p>

            <div className="proc-exp-review-list">
              {(clinical_review_items || []).map((item) => (
                <div
                  key={item.item_id}
                  id={`proc-exp-review-${item.item_id}`}
                  className="proc-exp-review-item"
                >
                  <span className="proc-exp-review-category">{item.category.replace('_', ' ')}</span>
                  <p className="proc-exp-review-statement">{item.statement}</p>
                </div>
              ))}
            </div>
          </section>
        )}

        {/* ── LIMITATIONS ──────────────────────────────────────── */}
        {activeSection === 'limitations' && (
          <section className="proc-exp-section" id="proc-exp-section-limitations">
            <h3 className="proc-exp-section-heading">System Limitations</h3>
            <p className="proc-exp-section-subtext">
              Technical and methodological limitations of this research prototype
            </p>

            <div className="proc-exp-limitations-list">
              {(limitations || []).map((lim) => (
                <div key={lim.limitation_id} className="proc-exp-limitation-item">
                  <div className="proc-exp-lim-header">
                    <span className="proc-exp-lim-domain">{lim.domain}</span>
                    <span className="proc-exp-lim-id font-mono">{lim.limitation_id}</span>
                  </div>
                  <p className="proc-exp-lim-description">{lim.description}</p>
                </div>
              ))}
            </div>

            {/* Provenance expandable */}
            <details
              className="proc-exp-provenance-details"
              open={provenanceExpanded}
              onToggle={(e) => setProvenanceExpanded(e.target.open)}
            >
              <summary className="proc-exp-provenance-summary">
                Explanation Provenance — Source Traceability
              </summary>
              <div className="proc-exp-provenance-content">
                {provenance && Object.entries(provenance).map(([key, val]) => {
                  if (key === 'lesion_class_mapping' && val) {
                    return (
                      <div key={key} className="proc-exp-prov-row">
                        <span className="proc-exp-prov-key">Lesion class mapping</span>
                        <span className="proc-exp-prov-val font-mono">
                          {Object.entries(val).map(([k, v]) => `${k}=${v}`).join(', ')}
                        </span>
                      </div>
                    );
                  }
                  return (
                    <div key={key} className="proc-exp-prov-row">
                      <span className="proc-exp-prov-key">{key.replace(/_/g, ' ')}</span>
                      <span className="proc-exp-prov-val">{val ?? '—'}</span>
                    </div>
                  );
                })}
              </div>
            </details>
          </section>
        )}
      </div>

      {/* Footer governance statement */}
      <div className="proc-exp-footer">
        <p className="proc-exp-governance">{governance_statement}</p>
      </div>
    </div>
  );
};

export default ProcedureExplanation;
