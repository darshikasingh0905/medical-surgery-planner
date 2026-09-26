import React, { useState, useEffect, useCallback, useRef, useMemo } from 'react';
import Viewer3D from './Viewer3D';
import MPRViewer from './MPRViewer';
import ProcedureExplanation from './ProcedureExplanation';
import PreoperativeReportModal from './PreoperativeReportModal';
import { ORGAN_DATA, LESION_VISUAL_CONFIG, ANATOMICAL_STRUCTURE_STYLES } from './data';
import {
  getPlanningSummary,
  getPlanningSession,
  updatePlanningSession,
  deletePlanningAnnotation,
  deletePlanningMeasurement,
  createPointToPointMeasurement,
  createPlanningAnnotation,
} from './api';

/**
 * PlanningWorkspace — Unified Preoperative Planning Workspace.
 *
 * Dedicated workstation integrating:
 *  - Case & CT scan overview
 *  - Model-predicted findings
 *  - Relevant anatomical structures
 *  - Computational spatial relationships
 *  - Preoperative measurements
 *  - Planning targets & annotations
 *  - Synchronized 3D + MPR visualization
 *  - Persistent planning notes and session state
 *
 * ⚠️ Medical Safety Governance:
 * Research and educational exploration prototype. Not a diagnostic device or autonomous surgical planner.
 */
const PlanningWorkspace = ({
  caseId,
  onExitWorkspace,
  // 3D viewer state & handlers from App.jsx
  meshUrls = {},
  lesions = [],
  structures = [],
  relationships = [],
  planningTargets = [],
  setPlanningTargets,
  measurements = [],
  setMeasurements,
  mprMetadata = null,
  voxelCursor = [146, 146, 172],
  setVoxelCursor,
  visibility = {},
  setVisibility,
  organOpacities = {},
  setOrganOpacities,
  lesionVisibility = {},
  setLesionVisibility,
  targetVisibility = {},
  setTargetVisibility,
  selectedTarget = null,
  setSelectedTarget,
  selectedMeasurement = null,
  setSelectedMeasurement,
  selectedLesion = null,
  setSelectedLesion,
  selectedStructure = null,
  setSelectedStructure,
  focusedTarget = null,
  setFocusedTarget,
  viewMode = 'split',
  setViewMode,
  mprWindowPreset = 'soft_tissue',
  setMprWindowPreset,
  mprWindowWidth = 400,
  setMprWindowWidth,
  mprWindowLevel = 40,
  setMprWindowLevel,
  mprShowLesionOverlay = true,
  setMprShowLesionOverlay,
  onResetCamera,
}) => {
  // ── Session & Summary state ──────────────────────────────────────────────
  const [summaryData, setSummaryData] = useState(null);
  const [loadingSummary, setLoadingSummary] = useState(true);
  const [planningNotes, setPlanningNotes] = useState('');
  const [saveStatus, setSaveStatus] = useState('saved'); // 'saving' | 'saved' | 'error'
  const [activeTab, setActiveTab] = useState('findings'); // 'findings' | 'anatomy' | 'relationships' | 'notes' | 'explanation'

  // Measurement interactive mode within workspace
  const [isMeasurementMode, setIsMeasurementMode] = useState(false);
  const [measurementStep, setMeasurementStep] = useState(null);
  const [measurementDraftStart, setMeasurementDraftStart] = useState(null);

  // Annotation creation mode
  const [isAnnotationMode, setIsAnnotationMode] = useState(false);

  // Preoperative report modal state (Day 22)
  const [showReportModal, setShowReportModal] = useState(false);

  // Debounce ref for session persistence
  const saveTimerRef = useRef(null);

  // ── Load Planning Session and Summary on Mount ───────────────────────────
  useEffect(() => {
    if (!caseId) return;
    let isCancelled = false;

    async function loadWorkspaceData() {
      setLoadingSummary(true);
      try {
        const [summary, session] = await Promise.all([
          getPlanningSummary(caseId),
          getPlanningSession(caseId),
        ]);

        if (!isCancelled) {
          setSummaryData(summary);
          if (session) {
            setPlanningNotes(session.planning_notes || '');
            if (session.view_mode) setViewMode(session.view_mode);
            if (session.voxel_cursor && session.voxel_cursor.length === 3) {
              setVoxelCursor(session.voxel_cursor);
            }
            if (session.mpr_window_preset) setMprWindowPreset(session.mpr_window_preset);
            if (session.mpr_window_width) setMprWindowWidth(session.mpr_window_width);
            if (session.mpr_window_level) setMprWindowLevel(session.mpr_window_level);
            if (session.mpr_show_lesion_overlay != null) {
              setMprShowLesionOverlay(session.mpr_show_lesion_overlay);
            }
          }
        }
      } catch (err) {
        console.warn('Error loading planning summary/session:', err.message);
      } finally {
        if (!isCancelled) setLoadingSummary(false);
      }
    }

    loadWorkspaceData();

    return () => {
      isCancelled = true;
    };
  }, [caseId, setViewMode, setVoxelCursor, setMprWindowPreset, setMprWindowWidth, setMprWindowLevel, setMprShowLesionOverlay]);

  // ── Sync Session Updates to Backend ──────────────────────────────────────
  const triggerSessionSave = useCallback(
    (updates) => {
      if (!caseId) return;
      setSaveStatus('saving');
      if (saveTimerRef.current) clearTimeout(saveTimerRef.current);

      saveTimerRef.current = setTimeout(async () => {
        try {
          await updatePlanningSession(caseId, updates);
          setSaveStatus('saved');
        } catch (err) {
          console.warn('Failed to update planning session:', err.message);
          setSaveStatus('error');
        }
      }, 600);
    },
    [caseId]
  );

  // ── Notes Change Handler ─────────────────────────────────────────────────
  const handleNotesChange = (e) => {
    const text = e.target.value;
    setPlanningNotes(text);
    triggerSessionSave({ planning_notes: text });
  };

  // ── View Mode Switcher ───────────────────────────────────────────────────
  const handleViewModeSelect = (mode) => {
    setViewMode(mode);
    triggerSessionSave({ view_mode: mode });
  };

  // ── Cursor Synchronization ───────────────────────────────────────────────
  const handleCursorChange = useCallback(
    (newCursor) => {
      setVoxelCursor(newCursor);
      triggerSessionSave({ voxel_cursor: newCursor });
    },
    [setVoxelCursor, triggerSessionSave]
  );

  // ── Lesion Selection & Focus ─────────────────────────────────────────────
  const handleSelectFinding = useCallback(
    (finding) => {
      setSelectedLesion(finding);
      setSelectedTarget(null);
      setSelectedStructure(finding.lesion_id);
      setSelectedMeasurement(null);

      // Dim host kidney to highlight lesion
      const host = finding.lesion_id?.includes('right') ? 'kidney_right' : 'kidney_left';
      setOrganOpacities({ [host]: 0.25 });
      setFocusedTarget(finding);

      // Navigate MPR to centroid voxel
      if (finding.centroid_mm && mprMetadata) {
        const spacing = mprMetadata.voxel_spacing_mm || [1.5, 1.5, 1.5];
        const cx = Math.round(finding.centroid_mm[0] / spacing[0]);
        const cy = Math.round(finding.centroid_mm[1] / spacing[1]);
        const cz = Math.round(finding.centroid_mm[2] / spacing[2]);
        const shape = mprMetadata.shape;
        const vx = Math.max(0, Math.min(cx, shape[0] - 1));
        const vy = Math.max(0, Math.min(cy, shape[1] - 1));
        const vz = Math.max(0, Math.min(cz, shape[2] - 1));
        handleCursorChange([vx, vy, vz]);
      }

      triggerSessionSave({
        selected_lesion_id: finding.lesion_id,
        selected_target_id: `model_${finding.lesion_id}`,
      });
    },
    [mprMetadata, setOrganOpacities, setFocusedTarget, setSelectedLesion, setSelectedStructure, setSelectedTarget, setSelectedMeasurement, handleCursorChange, triggerSessionSave]
  );

  // ── Structure Selection & Focus ──────────────────────────────────────────
  const handleSelectStructureItem = useCallback(
    (structId) => {
      setSelectedStructure(structId);
      setSelectedLesion(null);
      setSelectedTarget(null);
      setSelectedMeasurement(null);
      setFocusedTarget(structId);

      // Dim other anatomy
      const dims = {};
      structures.forEach((s) => {
        if (s.structure_id !== structId) dims[s.structure_id] = 0.35;
      });
      setOrganOpacities(dims);

      triggerSessionSave({ selected_structure_id: structId });
    },
    [structures, setOrganOpacities, setFocusedTarget, setSelectedStructure, setSelectedLesion, setSelectedTarget, setSelectedMeasurement, triggerSessionSave]
  );

  // ── Planning Target Selection ────────────────────────────────────────────
  const handleSelectTargetItem = useCallback(
    (target) => {
      setSelectedTarget(target);
      setSelectedMeasurement(null);
      setSelectedLesion(null);
      if (target.voxel_coordinate) {
        handleCursorChange(target.voxel_coordinate);
        setFocusedTarget(target);
      }
      triggerSessionSave({ selected_target_id: target.target_id });
    },
    [setSelectedTarget, setSelectedMeasurement, setSelectedLesion, setFocusedTarget, handleCursorChange, triggerSessionSave]
  );

  // ── Measurement Selection ────────────────────────────────────────────────
  const handleSelectMeasurementItem = useCallback(
    (m) => {
      setSelectedMeasurement(m);
      setSelectedTarget(null);
      setSelectedLesion(null);
      setFocusedTarget(m);
      if (m.start_voxel) {
        handleCursorChange(m.start_voxel);
      }
      triggerSessionSave({ selected_measurement_id: m.measurement_id });
    },
    [setSelectedMeasurement, setSelectedTarget, setSelectedLesion, setFocusedTarget, handleCursorChange, triggerSessionSave]
  );

  // ── Structure Visibility Toggle ──────────────────────────────────────────
  const handleToggleStructureVisibility = (structId) => {
    setVisibility((prev) => {
      const next = { ...prev, [structId]: !(prev[structId] !== false) };
      triggerSessionSave({ visible_structures: next });
      return next;
    });
  };

  // ── Delete Target ────────────────────────────────────────────────────────
  const handleDeleteTarget = async (targetId) => {
    if (!caseId) return;
    try {
      await deletePlanningAnnotation(caseId, targetId);
      setPlanningTargets((prev) => prev.filter((t) => t.target_id !== targetId));
      if (selectedTarget?.target_id === targetId) setSelectedTarget(null);
    } catch (err) {
      console.error('Failed to delete target:', err);
    }
  };

  // ── Delete Measurement ───────────────────────────────────────────────────
  const handleDeleteMeasurement = async (measurementId) => {
    if (!caseId) return;
    try {
      await deletePlanningMeasurement(caseId, measurementId);
      setMeasurements((prev) => prev.filter((m) => m.measurement_id !== measurementId));
      if (selectedMeasurement?.measurement_id === measurementId) setSelectedMeasurement(null);
    } catch (err) {
      console.error('Failed to delete measurement:', err);
    }
  };

  // ── Interactive Measurement Click Handlers on MPR ────────────────────────
  const handleMeasurementPointPick = useCallback(
    async (voxelCoord) => {
      if (!isMeasurementMode || !caseId) return;

      if (measurementStep === 'pick_start') {
        setMeasurementDraftStart(voxelCoord);
        setMeasurementStep('pick_end');
      } else if (measurementStep === 'pick_end' && measurementDraftStart) {
        try {
          const created = await createPointToPointMeasurement(caseId, {
            start_voxel: measurementDraftStart,
            end_voxel: voxelCoord,
          });
          setMeasurements((prev) => [...prev, created]);
          setSelectedMeasurement(created);
        } catch (err) {
          console.error('Failed to create measurement:', err);
        } finally {
          setMeasurementStep('pick_start');
          setMeasurementDraftStart(null);
        }
      }
    },
    [isMeasurementMode, measurementStep, measurementDraftStart, caseId, setMeasurements, setSelectedMeasurement]
  );

  const handleAddPlanningPoint = useCallback(
    async (voxelCoord) => {
      if (!caseId) return;
      const userCount = planningTargets.filter((t) => t.source === 'user').length;
      try {
        const created = await createPlanningAnnotation(caseId, {
          label: `Planning Point ${userCount + 1}`,
          voxel_coordinate: voxelCoord,
          notes: 'Created via interactive workspace MPR slice click.',
        });
        setPlanningTargets((prev) => [...prev, created]);
        setSelectedTarget(created);
        setTargetVisibility((prev) => ({ ...prev, [created.target_id]: true }));
      } catch (err) {
        console.error('Failed to create planning point:', err);
      }
    },
    [caseId, planningTargets, setPlanningTargets, setSelectedTarget, setTargetVisibility]
  );

  // ── CT Scan Info Formatting ──────────────────────────────────────────────
  const scanMeta = summaryData?.scan_info || mprMetadata;
  const shapeStr = scanMeta?.shape ? `${scanMeta.shape[0]} × ${scanMeta.shape[1]} × ${scanMeta.shape[2]}` : '293 × 293 × 344';
  const spacingStr = scanMeta?.voxel_spacing_mm
    ? `${scanMeta.voxel_spacing_mm.map((s) => s.toFixed(1)).join(' × ')} mm`
    : '1.5 × 1.5 × 1.5 mm';
  const orientStr = scanMeta?.orientation ? scanMeta.orientation.join('') : 'RAS';
  const findingsList = summaryData?.findings || lesions;

  return (
    <div className="planning-workspace" id="preoperative-planning-workspace">
      {/* ────────────────────────────────────────────────────────── */}
      {/* CASE HEADER BAR                                            */}
      {/* ────────────────────────────────────────────────────────── */}
      <header className="workspace-header">
        <div className="workspace-header-left">
          <div className="workspace-title-group">
            <span className="workspace-badge-glow">WORKSTATION</span>
            <h1 className="workspace-title">Preoperative Planning Workspace</h1>
          </div>
          <div className="workspace-case-meta">
            <span className="meta-pill">
              <strong className="meta-label">Case:</strong>
              <span className="meta-value font-mono" title={caseId}>{caseId?.slice(0, 8)}…</span>
            </span>
            <span className="meta-pill">
              <strong className="meta-label">Status:</strong>
              <span className="meta-badge-completed">Completed</span>
            </span>
            <span className="meta-pill">
              <strong className="meta-label">CT Dimensions:</strong>
              <span className="meta-value font-mono">{shapeStr}</span>
            </span>
            <span className="meta-pill">
              <strong className="meta-label">Spacing:</strong>
              <span className="meta-value font-mono">{spacingStr}</span>
            </span>
            <span className="meta-pill">
              <strong className="meta-label">Orientation:</strong>
              <span className="meta-value font-mono">{orientStr}</span>
            </span>
          </div>
        </div>

        <div className="workspace-header-right">
          <div className="save-indicator" title="Automatic session state persistence">
            <span className={`save-dot save-dot--${saveStatus}`} />
            <span className="save-text">
              {saveStatus === 'saving' ? 'Saving session…' : saveStatus === 'saved' ? 'Session saved' : 'Save warning'}
            </span>
          </div>
          <div className="workspace-governance-badge" title="Educational & Research Prototype">
            <span className="gov-icon">⚖️</span>
            Research Prototype — Educational Use
          </div>
          <button
            id="btn-open-preoperative-report"
            className="workspace-report-btn"
            onClick={() => setShowReportModal(true)}
            type="button"
            title="Open Preoperative Planning Report (JSON/PDF Preview & Export)"
          >
            📄 Preoperative Report
          </button>
          {onExitWorkspace && (
            <button
              id="btn-exit-workspace"
              className="workspace-exit-btn"
              onClick={onExitWorkspace}
              type="button"
              title="Return to standard viewer screen"
            >
              ✕ Exit Workspace
            </button>
          )}
        </div>
      </header>

      {/* ────────────────────────────────────────────────────────── */}
      {/* 3-COLUMN MAIN WORKSPACE AREA                               */}
      {/* ────────────────────────────────────────────────────────── */}
      <div className="workspace-body">
        {/* ── LEFT COLUMN: Planning Navigator & Summary ───────────── */}
        <aside className="workspace-col workspace-col--left">
          <nav className="workspace-nav-tabs">
            <button
              className={`workspace-tab-btn ${activeTab === 'findings' ? 'active' : ''}`}
              onClick={() => setActiveTab('findings')}
              type="button"
            >
              Findings ({findingsList.length})
            </button>
            <button
              className={`workspace-tab-btn ${activeTab === 'anatomy' ? 'active' : ''}`}
              onClick={() => setActiveTab('anatomy')}
              type="button"
            >
              Anatomy ({structures.length})
            </button>
            <button
              className={`workspace-tab-btn ${activeTab === 'relationships' ? 'active' : ''}`}
              onClick={() => setActiveTab('relationships')}
              type="button"
            >
              Spatial
            </button>
            <button
              className={`workspace-tab-btn ${activeTab === 'explanation' ? 'active' : ''}`}
              onClick={() => setActiveTab('explanation')}
              type="button"
              id="btn-open-explanation-tab"
              title="Open structured procedure explanation"
            >
              📋 Explanation
            </button>
            <button
              className={`workspace-tab-btn ${activeTab === 'notes' ? 'active' : ''}`}
              onClick={() => setActiveTab('notes')}
              type="button"
            >
              Notes {planningNotes ? '●' : ''}
            </button>
          </nav>

          <div className="workspace-tab-content">
            {/* Tab 1: Model-Predicted Findings */}
            {activeTab === 'findings' && (
              <div className="findings-section">
                <div className="section-intro">
                  <h3 className="section-heading">Model-Predicted Findings</h3>
                  <span className="section-subtext">Verified KiTS23 model inference segmentations</span>
                </div>

                {findingsList.length === 0 ? (
                  <div className="empty-panel-notice">No computational findings detected in this case.</div>
                ) : (
                  findingsList.map((f) => {
                    const isSelected = selectedLesion?.lesion_id === f.lesion_id;
                    const classConfig = LESION_VISUAL_CONFIG[f.class_name] || LESION_VISUAL_CONFIG.cyst;
                    return (
                      <div
                        key={f.lesion_id}
                        className={`finding-card ${isSelected ? 'finding-card--selected' : ''}`}
                        onClick={() => handleSelectFinding(f)}
                      >
                        <div className="finding-card-header">
                          <span className="finding-swatch" style={{ backgroundColor: classConfig.color }} />
                          <div className="finding-title-box">
                            <h4 className="finding-name">
                              {f.computational_interpretation || f.lesion_id}
                            </h4>
                            <span className="finding-host">Host: {f.host_organ?.replace('_', ' ') || 'Kidney'}</span>
                          </div>
                          <button
                            className="finding-focus-btn"
                            onClick={(e) => {
                              e.stopPropagation();
                              handleSelectFinding(f);
                            }}
                            title="Focus 3D camera & MPR cursor on this finding"
                          >
                            🎯 Focus
                          </button>
                        </div>

                        <div className="finding-metrics-grid">
                          <div className="metric-cell">
                            <span className="metric-label">Estimated Volume</span>
                            <span className="metric-val">{f.volume_ml ? `${f.volume_ml.toFixed(4)} mL` : 'N/A'}</span>
                          </div>
                          <div className="metric-cell">
                            <span className="metric-label">Bounding Box</span>
                            <span className="metric-val">
                              {f.dimensions_mm ? `${f.dimensions_mm.map((d) => d.toFixed(1)).join(' × ')} mm` : 'N/A'}
                            </span>
                          </div>
                          <div className="metric-cell" style={{ gridColumn: 'span 2' }}>
                            <span className="metric-label">Centroid (Physical mm)</span>
                            <span className="metric-val font-mono">
                              {f.centroid_mm ? `[${f.centroid_mm.map((c) => c.toFixed(1)).join(', ')}] mm` : 'N/A'}
                            </span>
                          </div>
                        </div>
                      </div>
                    );
                  })
                )}
              </div>
            )}

            {/* Tab 2: Relevant Anatomy */}
            {activeTab === 'anatomy' && (
              <div className="anatomy-section">
                <div className="section-intro">
                  <h3 className="section-heading">Relevant Anatomical Structures</h3>
                  <span className="section-subtext">TotalSegmentator AI segmentation masks</span>
                </div>

                <div className="structure-list">
                  {structures.map((s) => {
                    const isVisible = visibility[s.structure_id] !== false;
                    const isSelected = selectedStructure === s.structure_id;
                    const style = ANATOMICAL_STRUCTURE_STYLES[s.structure_id] || ORGAN_DATA[s.structure_id] || { color: '#94a3b8' };

                    return (
                      <div
                        key={s.structure_id}
                        className={`structure-row ${isSelected ? 'structure-row--selected' : ''} ${!s.available ? 'structure-row--unavailable' : ''}`}
                        onClick={() => s.available && handleSelectStructureItem(s.structure_id)}
                      >
                        <input
                          type="checkbox"
                          checked={isVisible && s.available}
                          disabled={!s.available}
                          onChange={(e) => {
                            e.stopPropagation();
                            handleToggleStructureVisibility(s.structure_id);
                          }}
                          className="structure-checkbox"
                          title="Toggle visibility"
                        />
                        <span className="structure-swatch" style={{ backgroundColor: s.available ? style.color : '#475569' }} />
                        <span className="structure-name">{s.name}</span>

                        <span className={`structure-status-tag ${s.available ? 'tag-avail' : 'tag-unavail'}`}>
                          {s.available ? 'Available' : 'Not Segmented'}
                        </span>

                        {s.available && (
                          <button
                            className="structure-focus-btn"
                            onClick={(e) => {
                              e.stopPropagation();
                              handleSelectStructureItem(s.structure_id);
                            }}
                            title="Focus camera on structure"
                          >
                            🎯
                          </button>
                        )}
                      </div>
                    );
                  })}
                </div>
              </div>
            )}

            {/* Tab 3: Spatial Relationships */}
            {activeTab === 'relationships' && (
              <div className="relationships-section">
                <div className="section-intro">
                  <h3 className="section-heading">Computational Spatial Relationships</h3>
                  <span className="section-subtext">Physical minimum Euclidean distances from lesion mask to available segmented structures</span>
                </div>

                {(() => {
                  const availableRels = relationships.filter((r) => r.available === true);
                  const unavailableCount = relationships.length - availableRels.length;
                  return (
                    <>
                      <div className="relationships-list">
                        {availableRels.length === 0 ? (
                          <div className="empty-panel-notice">
                            No segmented structures available to compute distances against.
                            {unavailableCount > 0 && (
                              <span style={{ display: 'block', marginTop: '6px', color: '#64748b', fontSize: '11px' }}>
                                {unavailableCount} structure(s) not segmented in this case (e.g. renal vessels, ureter).
                              </span>
                            )}
                          </div>
                        ) : (
                          availableRels.map((rel) => {
                            const isOverlap = rel.overlap;
                            const distMm = rel.computational_minimum_distance_mm ?? rel.distance_mm;
                            return (
                              <div key={rel.structure_id} className={`rel-card ${isOverlap ? 'rel-card--overlap' : ''}`}>
                                <div className="rel-card-header">
                                  <span className="rel-struct-name">{rel.display_name || rel.structure_name || rel.structure_id.replace(/_/g, ' ')}</span>
                                  <span className={`rel-badge ${isOverlap ? 'badge-overlap' : 'badge-separated'}`}>
                                    {isOverlap ? '⚠️ Contact' : 'Separated'}
                                  </span>
                                </div>
                                <div className="rel-metric-row">
                                  <span className="rel-metric-label">Computational min. distance:</span>
                                  <span className="rel-metric-value font-mono">
                                    {distMm != null ? `${distMm.toFixed(2)} mm` : 'Not computed'}
                                  </span>
                                </div>
                              </div>
                            );
                          })
                        )}
                      </div>
                      {unavailableCount > 0 && availableRels.length > 0 && (
                        <p style={{ color: '#64748b', fontSize: '11px', margin: '6px 0 0' }}>
                          {unavailableCount} structure(s) not segmented (renal vessels, ureter, renal pelvis) — distances not computable.
                        </p>
                      )}
                    </>
                  );
                })()}

                <p className="gov-disclaimer-note">
                  <em>Computational minimum distance in physical CT space. Does not constitute surgical margins or clinical assessment.</em>
                </p>
              </div>
            )}

            {/* Tab: Structured Preoperative Procedure Explanation (Day 21) */}
            {activeTab === 'explanation' && (
              <div className="explanation-section" style={{ height: '100%', overflowY: 'auto' }}>
                <ProcedureExplanation
                  caseId={caseId}
                  onSelectFinding={handleSelectFinding}
                  onSelectStructure={handleSelectStructureItem}
                  onSelectMeasurement={handleSelectMeasurementItem}
                  onSelectTarget={handleSelectTargetItem}
                  selectedLesion={selectedLesion}
                  selectedStructure={selectedStructure}
                  selectedMeasurement={selectedMeasurement}
                  selectedTarget={selectedTarget}
                />
              </div>
            )}

            {/* Tab 4: User Planning Notes */}
            {activeTab === 'notes' && (
              <div className="notes-section">
                <div className="section-intro">
                  <h3 className="section-heading">Research Planning Notes</h3>
                  <span className="section-subtext">User notes persisted across sessions</span>
                </div>

                <textarea
                  className="planning-notes-textarea"
                  placeholder="Enter preoperative planning observations, target landmarks, or research notes..."
                  value={planningNotes}
                  onChange={handleNotesChange}
                  rows={14}
                />

                <div className="notes-footer">
                  <span className="char-count">{planningNotes.length} characters</span>
                  <span className="save-status-text">
                    {saveStatus === 'saving' ? 'Auto-saving…' : 'Saved to session'}
                  </span>
                </div>

                <p className="gov-disclaimer-note">
                  <em>Planning notes are user-authored annotations. They do not generate medical diagnoses or autonomous surgical plans.</em>
                </p>
              </div>
            )}
          </div>
        </aside>

        {/* ── CENTER COLUMN: Synchronized 3D + MPR Visualizer ──────── */}
        <main className="workspace-col workspace-col--center">
          {/* Workspace Visualization Toolbar */}
          <div className="visualizer-toolbar">
            <div className="view-mode-tabs">
              <button
                className={`view-tab-btn ${viewMode === '3d' ? 'active' : ''}`}
                onClick={() => handleViewModeSelect('3d')}
                type="button"
              >
                🧊 3D Model View
              </button>
              <button
                className={`view-tab-btn ${viewMode === 'mpr' ? 'active' : ''}`}
                onClick={() => handleViewModeSelect('mpr')}
                type="button"
              >
                🔬 2D CT MPR
              </button>
              <button
                className={`view-tab-btn ${viewMode === 'split' ? 'active' : ''}`}
                onClick={() => handleViewModeSelect('split')}
                type="button"
              >
                🪟 Split (3D + MPR)
              </button>
            </div>

            <div className="toolbar-tools">
              <button
                className={`tool-pill ${isMeasurementMode ? 'active' : ''}`}
                onClick={() => setIsMeasurementMode(!isMeasurementMode)}
                type="button"
                title="Measure distance on MPR slice clicks"
              >
                📏 Measure Mode
              </button>

              <button
                className={`tool-pill ${isAnnotationMode ? 'active' : ''}`}
                onClick={() => setIsAnnotationMode(!isAnnotationMode)}
                type="button"
                title="Add planning point on MPR slice click"
              >
                📍 Add Point Mode
              </button>

              <button
                className="tool-pill"
                onClick={onResetCamera}
                type="button"
                title="Reset 3D camera to home position"
              >
                🔄 Reset Camera
              </button>
            </div>
          </div>

          {/* Visualization Container */}
          <div className={`visualizer-viewport visualizer-viewport--${viewMode}`}>
            {(viewMode === '3d' || viewMode === 'split') && (
              <div className="viewer-pane viewer-pane--3d">
                <Viewer3D
                  visibility={visibility}
                  meshUrls={meshUrls}
                  lesions={lesions}
                  lesionVisibility={lesionVisibility}
                  organOpacities={organOpacities}
                  selectedStructure={selectedStructure}
                  focusedTarget={focusedTarget}
                  isPlanningView={true}
                  planningTargets={planningTargets}
                  targetVisibility={targetVisibility}
                  selectedTarget={selectedTarget}
                  onSelectTarget={handleSelectTargetItem}
                  measurements={measurements}
                  selectedMeasurement={selectedMeasurement}
                  onSelectMeasurement={handleSelectMeasurementItem}
                  onFocusDone={() => setFocusedTarget(null)}
                  onResetCamera={onResetCamera}
                />
              </div>
            )}

            {(viewMode === 'mpr' || viewMode === 'split') && (
              <div className="viewer-pane viewer-pane--mpr">
                <MPRViewer
                  caseId={caseId}
                  mprMetadata={mprMetadata}
                  voxelCursor={voxelCursor}
                  onCursorChange={handleCursorChange}
                  showLesionOverlay={mprShowLesionOverlay}
                  onToggleLesionOverlay={setMprShowLesionOverlay}
                  windowPreset={mprWindowPreset}
                  windowWidth={mprWindowWidth}
                  windowLevel={mprWindowLevel}
                  onPresetSelect={setMprWindowPreset}
                  planningTargets={planningTargets}
                  targetVisibility={targetVisibility}
                  selectedTarget={selectedTarget}
                  onSelectTarget={handleSelectTargetItem}
                  isAnnotationMode={isAnnotationMode}
                  onToggleAnnotationMode={setIsAnnotationMode}
                  onAddPlanningPoint={handleAddPlanningPoint}
                  isMeasurementMode={isMeasurementMode}
                  measurementStep={measurementStep}
                  measurementDraftStart={measurementDraftStart}
                  onMeasurementPointPick={handleMeasurementPointPick}
                />
              </div>
            )}
          </div>
        </main>

        {/* ── RIGHT COLUMN: Inspector, Targets & Measurements ─────── */}
        <aside className="workspace-col workspace-col--right">
          {/* Section A: Selection Inspector */}
          <div className="inspector-card">
            <h3 className="inspector-heading">Selected Object Inspector</h3>
            {selectedTarget ? (
              <div className="inspector-details">
                <div className="inspector-badge-row">
                  <span className="item-type-badge item-type-badge--target">Planning Target</span>
                  <span className="item-source-badge">{selectedTarget.source?.toUpperCase()}</span>
                </div>
                <h4 className="inspector-title">{selectedTarget.label}</h4>
                <div className="inspector-meta-table">
                  <div className="meta-row">
                    <span className="meta-k">Target ID:</span>
                    <span className="meta-v font-mono">{selectedTarget.target_id}</span>
                  </div>
                  <div className="meta-row">
                    <span className="meta-k">Voxel Coord:</span>
                    <span className="meta-v font-mono">
                      {selectedTarget.voxel_coordinate ? `[${selectedTarget.voxel_coordinate.join(', ')}]` : 'N/A'}
                    </span>
                  </div>
                  <div className="meta-row">
                    <span className="meta-k">Physical (mm):</span>
                    <span className="meta-v font-mono">
                      {selectedTarget.physical_coordinate ? `[${selectedTarget.physical_coordinate.join(', ')}] mm` : 'N/A'}
                    </span>
                  </div>
                  {selectedTarget.notes && (
                    <div className="meta-row" style={{ gridColumn: 'span 2' }}>
                      <span className="meta-k">Notes:</span>
                      <span className="meta-v">{selectedTarget.notes}</span>
                    </div>
                  )}
                </div>
              </div>
            ) : selectedMeasurement ? (
              <div className="inspector-details">
                <div className="inspector-badge-row">
                  <span className="item-type-badge item-type-badge--meas">Measurement</span>
                  <span className="item-source-badge">{selectedMeasurement.source?.toUpperCase()}</span>
                </div>
                <h4 className="inspector-title">{selectedMeasurement.label}</h4>
                <div className="highlight-distance-badge">
                  {selectedMeasurement.distance_mm.toFixed(2)} mm ({selectedMeasurement.distance_cm.toFixed(3)} cm)
                </div>
                <div className="inspector-meta-table">
                  <div className="meta-row">
                    <span className="meta-k">Point A:</span>
                    <span className="meta-v font-mono">
                      {selectedMeasurement.start_physical ? `[${selectedMeasurement.start_physical.join(', ')}] mm` : 'N/A'}
                    </span>
                  </div>
                  <div className="meta-row">
                    <span className="meta-k">Point B:</span>
                    <span className="meta-v font-mono">
                      {selectedMeasurement.end_physical ? `[${selectedMeasurement.end_physical.join(', ')}] mm` : 'N/A'}
                    </span>
                  </div>
                </div>
              </div>
            ) : selectedLesion ? (
              <div className="inspector-details">
                <div className="inspector-badge-row">
                  <span className="item-type-badge item-type-badge--lesion">Computational Finding</span>
                  <span className="item-source-badge">KiTS23 AI</span>
                </div>
                <h4 className="inspector-title">{selectedLesion.computational_interpretation || selectedLesion.lesion_id}</h4>
                <div className="inspector-meta-table">
                  <div className="meta-row">
                    <span className="meta-k">Volume:</span>
                    <span className="meta-v">{selectedLesion.volume_ml ? `${selectedLesion.volume_ml.toFixed(4)} mL` : 'N/A'}</span>
                  </div>
                  <div className="meta-row">
                    <span className="meta-k">Centroid:</span>
                    <span className="meta-v font-mono">
                      {selectedLesion.centroid_mm ? `[${selectedLesion.centroid_mm.map((c) => c.toFixed(1)).join(', ')}]` : 'N/A'}
                    </span>
                  </div>
                </div>
              </div>
            ) : (
              <div className="empty-panel-notice">Select any finding, target, structure, or measurement to inspect details.</div>
            )}
          </div>

          {/* Section B: Planning Targets List */}
          <div className="layer-card">
            <div className="layer-card-header">
              <h3 className="layer-heading">Planning Targets ({planningTargets.length})</h3>
            </div>
            <div className="items-scroll-list">
              {planningTargets.map((t) => {
                const isSelected = selectedTarget?.target_id === t.target_id;
                const isModel = t.source === 'model';
                return (
                  <div
                    key={t.target_id}
                    className={`list-item-row ${isSelected ? 'list-item-row--selected' : ''}`}
                    onClick={() => handleSelectTargetItem(t)}
                  >
                    <span className={`target-dot ${isModel ? 'dot-cyan' : 'dot-amber'}`} />
                    <div className="item-info-col">
                      <span className="item-main-text">{t.label}</span>
                      <span className="item-sub-text font-mono">
                        {t.voxel_coordinate ? `[${t.voxel_coordinate.join(', ')}]` : ''}
                      </span>
                    </div>
                    {!isModel && (
                      <button
                        className="item-delete-btn"
                        onClick={(e) => {
                          e.stopPropagation();
                          handleDeleteTarget(t.target_id);
                        }}
                        title="Delete annotation"
                      >
                        🗑️
                      </button>
                    )}
                  </div>
                );
              })}
            </div>
          </div>

          {/* Section C: Preoperative Measurements List */}
          <div className="layer-card">
            <div className="layer-card-header">
              <h3 className="layer-heading">Preoperative Measurements ({measurements.length})</h3>
            </div>
            <div className="items-scroll-list">
              {measurements.length === 0 ? (
                <div className="empty-panel-notice">No measurements created yet. Use Measure Mode to add.</div>
              ) : (
                measurements.map((m) => {
                  const isSelected = selectedMeasurement?.measurement_id === m.measurement_id;
                  return (
                    <div
                      key={m.measurement_id}
                      className={`list-item-row ${isSelected ? 'list-item-row--selected' : ''}`}
                      onClick={() => handleSelectMeasurementItem(m)}
                    >
                      <span className="meas-pill-val">{m.distance_mm.toFixed(1)} mm</span>
                      <div className="item-info-col">
                        <span className="item-main-text">{m.label}</span>
                        <span className="item-sub-text font-mono">{m.distance_cm.toFixed(2)} cm</span>
                      </div>
                      <button
                        className="item-delete-btn"
                        onClick={(e) => {
                          e.stopPropagation();
                          handleDeleteMeasurement(m.measurement_id);
                        }}
                        title="Delete measurement"
                      >
                        🗑️
                      </button>
                    </div>
                  );
                })
              )}
            </div>
          </div>
        </aside>
      </div>

      {/* Preoperative Report Review & Export Modal (Day 22) */}
      {showReportModal && (
        <PreoperativeReportModal
          caseId={caseId}
          onClose={() => setShowReportModal(false)}
        />
      )}
    </div>
  );
};

export default PlanningWorkspace;
