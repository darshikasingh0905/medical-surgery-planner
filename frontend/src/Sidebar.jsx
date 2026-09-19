import React from 'react';
import { ORGAN_DATA, LESION_VISUAL_CONFIG, ANATOMICAL_STRUCTURE_STYLES } from './data';

/**
 * Sidebar — Supports Standard View and Preoperative Planning View.
 *
 * In Planning View:
 *  - Displays registered anatomical structures with genuine availability status
 *  - Controls structure visibility, highlighting, and camera focus
 *  - Displays explicit "Not available in this case" notice for non-segmented anatomy
 *  - Adjusts organ transparency and lesion opacity
 *
 * Day 16 additions:
 *  - View mode switcher: 3D | MPR | Split
 *  - MPR preset selector and lesion overlay toggle
 */
const Sidebar = ({
  // Mode
  isPlanningView = false,
  onTogglePlanningView,

  // Organs
  selectedOrgan,
  onSelectOrgan,
  visibility = {},
  onToggleVisibility,

  // Anatomical structures (Day 15)
  structures = [],
  structureVisibility = {},
  onToggleStructureVisibility,
  selectedStructure,
  onSelectStructure,
  onFocusStructure,

  // Lesions
  lesions = [],
  lesionVisibility = {},
  onToggleLesion,
  selectedLesion,
  onSelectLesion,
  onFocusLesion,

  // Opacity controls
  organOpacity = 0.85,
  onChangeOrganOpacity,
  lesionOpacity = 1.0,
  onChangeLesionOpacity,

  // Reset / Scan
  onReset,

  // Day 16: MPR view mode controls
  viewMode = '3d',
  onSetViewMode,
  mprMetadata = null,
  mprLoading = false,
  mprError = null,
  mprWindowPreset = 'soft_tissue',
  mprWindowWidth = 400,
  mprWindowLevel = 40,
  mprShowLesionOverlay = true,
  onMprPresetSelect,
  onToggleMprLesionOverlay,

  // Day 17: Planning Targets & Markers layer
  planningTargets = [],
  targetVisibility = {},
  onToggleTargetVisibility,
  selectedTarget = null,
  onSelectTarget,
  onFocusTarget,
  onDeleteTarget,
  isAnnotationMode = false,
  onToggleAnnotationMode,
}) => {
  return (
    <div className="sidebar">
      {/* ── View Mode Switcher (Standard vs Planning) ── */}
      <div className="sidebar-mode-switcher">
        <button
          id="btn-view-normal"
          className={`mode-tab-btn ${!isPlanningView ? 'active' : ''}`}
          onClick={() => onTogglePlanningView && onTogglePlanningView(false)}
          type="button"
        >
          Normal View
        </button>
        <button
          id="btn-view-planning"
          className={`mode-tab-btn ${isPlanningView ? 'active' : ''}`}
          onClick={() => onTogglePlanningView && onTogglePlanningView(true)}
          type="button"
        >
          Planning View
        </button>
      </div>

      {/* ── MPR View Mode Switcher (Day 16) ── */}
      <div className="sidebar-mpr-mode">
        <span className="mpr-mode-label">Viewer:</span>
        <div className="mpr-mode-tabs">
          <button
            id="btn-viewmode-3d"
            className={`mpr-mode-tab ${viewMode === '3d' ? 'active' : ''}`}
            onClick={() => onSetViewMode && onSetViewMode('3d')}
            title="3D anatomical viewer"
            type="button"
          >
            3D
          </button>
          <button
            id="btn-viewmode-mpr"
            className={`mpr-mode-tab ${viewMode === 'mpr' ? 'active' : ''}`}
            onClick={() => onSetViewMode && onSetViewMode('mpr')}
            title="Multi-Planar Reconstruction (Axial, Coronal, Sagittal)"
            type="button"
          >
            MPR
          </button>
          <button
            id="btn-viewmode-split"
            className={`mpr-mode-tab ${viewMode === 'split' ? 'active' : ''}`}
            onClick={() => onSetViewMode && onSetViewMode('split')}
            title="Split view: 3D + MPR side-by-side"
            type="button"
          >
            Split
          </button>
        </div>
      </div>

      {/* ── Planning View Header Banner ── */}
      {isPlanningView && (
        <div className="planning-banner">
          <div className="planning-banner-title">Preoperative Planning View</div>
          <div className="planning-banner-subtitle">
            Computational visualization for research/educational use. Clinical interpretation required.
          </div>
        </div>
      )}

      {/* ── Section: Anatomical Structures (Planning View) OR Standard Organ Panel (Normal View) ── */}
      {isPlanningView ? (
        <div className="sidebar-section">
          <h2 className="sidebar-heading sidebar-heading--planning">
            Anatomical Structures
            <span className="sidebar-count-badge">
              {structures.filter((s) => s.available).length} / {structures.length}
            </span>
          </h2>

          <ul className="organ-list" aria-label="Anatomical structures list">
            {structures.map((struct) => {
              const isAvail = struct.available;
              const isVisible = structureVisibility[struct.structure_id] !== false;
              const isSelected = selectedStructure === struct.structure_id;
              const style = ANATOMICAL_STRUCTURE_STYLES[struct.structure_id] || {
                color: struct.color || '#64748B',
              };

              if (!isAvail) {
                return (
                  <li
                    key={struct.structure_id}
                    className="organ-item organ-item--unavailable"
                    id={`struct-item-${struct.structure_id}`}
                    title={struct.status_reason || 'Not available in this case'}
                  >
                    <span className="organ-color-swatch swatch-unavailable" aria-hidden="true" />
                    <div className="struct-name-col">
                      <span className="organ-name text-muted">{struct.display_name}</span>
                      <span className="struct-status-label">Not available in this case</span>
                    </div>
                  </li>
                );
              }

              return (
                <li
                  key={struct.structure_id}
                  className={`organ-item ${isSelected ? 'selected' : ''}`}
                  onClick={() => onSelectStructure && onSelectStructure(struct.structure_id)}
                  aria-selected={isSelected}
                  role="option"
                  tabIndex={0}
                  onKeyDown={(e) =>
                    e.key === 'Enter' && onSelectStructure && onSelectStructure(struct.structure_id)
                  }
                  id={`struct-item-${struct.structure_id}`}
                >
                  <span
                    className="organ-color-swatch"
                    style={{ backgroundColor: style.color }}
                    aria-hidden="true"
                  />
                  <div className="struct-name-col">
                    <span className="organ-name">{struct.display_name}</span>
                    <span className="struct-category-badge">{struct.category}</span>
                  </div>

                  <div className="struct-controls">
                    <button
                      id={`visibility-toggle-${struct.structure_id}`}
                      className="visibility-toggle"
                      onClick={(e) => {
                        e.stopPropagation();
                        onToggleStructureVisibility &&
                          onToggleStructureVisibility(struct.structure_id);
                      }}
                      title={isVisible ? `Hide ${struct.display_name}` : `Show ${struct.display_name}`}
                      aria-label={
                        isVisible ? `Hide ${struct.display_name}` : `Show ${struct.display_name}`
                      }
                      aria-pressed={isVisible}
                    >
                      {isVisible ? '👁️' : '👁️‍🗨️'}
                    </button>

                    <button
                      id={`focus-btn-${struct.structure_id}`}
                      className="lesion-focus-btn"
                      onClick={(e) => {
                        e.stopPropagation();
                        onFocusStructure && onFocusStructure(struct.structure_id);
                      }}
                      title={`Focus camera on ${struct.display_name}`}
                      aria-label={`Focus camera on ${struct.display_name}`}
                    >
                      🎯
                    </button>
                  </div>
                </li>
              );
            })}
          </ul>
        </div>
      ) : (
        /* ── Normal View: Standard Organ List ── */
        <div className="sidebar-section">
          <h2 className="sidebar-heading">Organ Panel</h2>
          <ul className="organ-list" aria-label="Organ list">
            {Object.keys(ORGAN_DATA).map((key) => {
              const organ = ORGAN_DATA[key];
              const isVisible = visibility[key];
              return (
                <li
                  key={key}
                  className={`organ-item ${selectedOrgan === key ? 'selected' : ''}`}
                  onClick={() => onSelectOrgan(key)}
                  aria-selected={selectedOrgan === key}
                  role="option"
                  tabIndex={0}
                  onKeyDown={(e) => e.key === 'Enter' && onSelectOrgan(key)}
                  id={`organ-item-${key}`}
                >
                  <span
                    className="organ-color-swatch"
                    style={{ backgroundColor: organ.color }}
                    aria-hidden="true"
                  />
                  <span className="organ-name">{organ.name}</span>
                  <button
                    id={`visibility-toggle-${key}`}
                    className="visibility-toggle"
                    onClick={(e) => {
                      e.stopPropagation();
                      onToggleVisibility(key);
                    }}
                    title={isVisible ? `Hide ${organ.name}` : `Show ${organ.name}`}
                    aria-label={isVisible ? `Hide ${organ.name}` : `Show ${organ.name}`}
                    aria-pressed={isVisible}
                  >
                    {isVisible ? '👁️' : '👁️‍🗨️'}
                  </button>
                </li>
              );
            })}
          </ul>
        </div>
      )}

      {/* ── Model-Predicted Lesions Section ── */}
      {lesions.length > 0 && (
        <div className="sidebar-section">
          <h2 className="sidebar-heading sidebar-heading--lesion">
            Model-Predicted Lesions
            <span className="sidebar-lesion-count">{lesions.length}</span>
          </h2>

          <ul className="organ-list lesion-list" aria-label="Lesion list">
            {lesions.map((lesion) => {
              const classType = lesion.class_name ?? 'cyst';
              const config = LESION_VISUAL_CONFIG[classType] ?? LESION_VISUAL_CONFIG.cyst;
              const isVisible = lesionVisibility[lesion.lesion_id] !== false;
              const isSelected = selectedLesion?.lesion_id === lesion.lesion_id;

              return (
                <li
                  key={lesion.lesion_id}
                  className={`organ-item lesion-item ${isSelected ? 'selected' : ''}`}
                  onClick={() => onSelectLesion(lesion)}
                  aria-selected={isSelected}
                  role="option"
                  tabIndex={0}
                  onKeyDown={(e) => e.key === 'Enter' && onSelectLesion(lesion)}
                  id={`lesion-item-${lesion.lesion_id}`}
                >
                  <span
                    className="organ-color-swatch lesion-swatch"
                    style={{ backgroundColor: config.color, boxShadow: `0 0 6px ${config.color}55` }}
                    aria-hidden="true"
                  />
                  <div className="struct-name-col">
                    <span className="organ-name lesion-name">
                      {lesion.lesion_id.replace(/_/g, ' ')}
                    </span>
                    <span className="lesion-volume-pill">
                      {lesion.volume_ml != null ? `${lesion.volume_ml.toFixed(2)} mL` : '?'}
                    </span>
                  </div>

                  <div className="lesion-controls">
                    <button
                      id={`lesion-visibility-${lesion.lesion_id}`}
                      className="visibility-toggle"
                      onClick={(e) => {
                        e.stopPropagation();
                        onToggleLesion && onToggleLesion(lesion.lesion_id);
                      }}
                      title={isVisible ? 'Hide lesion' : 'Show lesion'}
                      aria-label={isVisible ? 'Hide lesion' : 'Show lesion'}
                      aria-pressed={isVisible}
                    >
                      {isVisible ? '👁️' : '👁️‍🗨️'}
                    </button>

                    {lesion.centroid_mm && (
                      <button
                        id={`lesion-focus-${lesion.lesion_id}`}
                        className="lesion-focus-btn"
                        onClick={(e) => {
                          e.stopPropagation();
                          onFocusLesion && onFocusLesion(lesion);
                        }}
                        title="Focus camera on lesion"
                        aria-label="Focus camera on lesion"
                      >
                        🎯
                      </button>
                    )}
                  </div>
                </li>
              );
            })}
          </ul>
        </div>
      )}

      {/* ── Planning Targets & Markers Section (Planning View) ── */}
      {isPlanningView && (
        <div className="sidebar-section planning-targets-section">
          <div className="planning-targets-header">
            <h2 className="sidebar-heading sidebar-heading--planning">
              Planning Targets
              <span className="sidebar-count-badge">
                {planningTargets.length}
              </span>
            </h2>
            {onToggleAnnotationMode && (
              <button
                id="btn-sidebar-add-point"
                className={`sidebar-add-point-btn ${isAnnotationMode ? 'active' : ''}`}
                onClick={() => onToggleAnnotationMode(!isAnnotationMode)}
                title={isAnnotationMode ? 'Exit point creation mode' : 'Enable click-to-annotate mode on CT slices'}
                type="button"
              >
                {isAnnotationMode ? '✕ Mode Active' : '➕ Add Point'}
              </button>
            )}
          </div>

          {planningTargets.length === 0 ? (
            <div className="planning-targets-empty">
              No planning targets defined yet. Click "Add Point" to create one on the CT slices.
            </div>
          ) : (
            <ul className="organ-list planning-targets-list" aria-label="Planning targets list">
              {planningTargets.map((target) => {
                const isModel = target.source === 'model';
                const isVisible = targetVisibility[target.target_id] !== false;
                const isSelected = selectedTarget?.target_id === target.target_id;
                const badgeClass = isModel ? 'target-badge--model' : 'target-badge--user';
                const badgeText = isModel ? 'MODEL FINDING' : 'USER ANNOTATION';
                const markerColor = isModel ? '#00e5ff' : '#f59e0b';

                return (
                  <li
                    key={target.target_id}
                    className={`organ-item planning-target-item ${isSelected ? 'selected' : ''}`}
                    onClick={() => onSelectTarget && onSelectTarget(target)}
                    aria-selected={isSelected}
                    role="option"
                    tabIndex={0}
                    id={`target-item-${target.target_id}`}
                  >
                    <span
                      className="organ-color-swatch target-swatch"
                      style={{ backgroundColor: markerColor, boxShadow: `0 0 6px ${markerColor}66` }}
                      aria-hidden="true"
                    />

                    <div className="struct-name-col">
                      <div className="target-title-row">
                        <span className="organ-name target-name">{target.label}</span>
                        <span className={`target-type-badge ${badgeClass}`}>{badgeText}</span>
                      </div>
                      <div className="target-coords-row">
                        <span className="target-coords-text">
                          Voxel: [{target.voxel_coordinate ? target.voxel_coordinate.join(', ') : '?'}]
                        </span>
                        {target.volume_ml != null && (
                          <span className="target-volume-pill">{target.volume_ml.toFixed(2)} mL</span>
                        )}
                      </div>
                    </div>

                    <div className="struct-controls">
                      <button
                        id={`target-visibility-${target.target_id}`}
                        className="visibility-toggle"
                        onClick={(e) => {
                          e.stopPropagation();
                          onToggleTargetVisibility && onToggleTargetVisibility(target.target_id);
                        }}
                        title={isVisible ? 'Hide marker' : 'Show marker'}
                        aria-label={isVisible ? 'Hide marker' : 'Show marker'}
                      >
                        {isVisible ? '👁️' : '👁️‍🗨️'}
                      </button>

                      <button
                        id={`target-focus-${target.target_id}`}
                        className="lesion-focus-btn"
                        onClick={(e) => {
                          e.stopPropagation();
                          onFocusTarget && onFocusTarget(target);
                        }}
                        title="Focus camera and center MPR cursor on target"
                        aria-label="Focus on target"
                      >
                        🎯
                      </button>

                      {!isModel && onDeleteTarget && (
                        <button
                          id={`target-delete-${target.target_id}`}
                          className="target-delete-btn"
                          onClick={(e) => {
                            e.stopPropagation();
                            onDeleteTarget(target.target_id);
                          }}
                          title="Delete user annotation"
                          aria-label="Delete annotation"
                        >
                          🗑️
                        </button>
                      )}
                    </div>
                  </li>
                );
              })}
            </ul>
          )}
        </div>
      )}

      {/* ── Opacity Controls (Visible in Planning View) ── */}
      {isPlanningView && (
        <div className="sidebar-section planning-controls-box">
          <div className="planning-control-row">
            <label htmlFor="organ-opacity-slider" className="planning-control-label">
              Organ Transparency
            </label>
            <span className="planning-control-val">{Math.round(organOpacity * 100)}%</span>
          </div>
          <input
            id="organ-opacity-slider"
            type="range"
            min="0.1"
            max="1.0"
            step="0.05"
            value={organOpacity}
            onChange={(e) =>
              onChangeOrganOpacity && onChangeOrganOpacity(parseFloat(e.target.value))
            }
            className="lesion-opacity-slider"
            aria-label="Organ transparency"
          />

          {lesions.length > 0 && (
            <>
              <div className="planning-control-row" style={{ marginTop: '0.6rem' }}>
                <label htmlFor="lesion-opacity-slider" className="planning-control-label">
                  Lesion Opacity
                </label>
                <span className="planning-control-val">{Math.round(lesionOpacity * 100)}%</span>
              </div>
              <input
                id="lesion-opacity-slider"
                type="range"
                min="0.1"
                max="1.0"
                step="0.05"
                value={lesionOpacity}
                onChange={(e) =>
                  onChangeLesionOpacity && onChangeLesionOpacity(parseFloat(e.target.value))
                }
                className="lesion-opacity-slider"
                aria-label="Lesion opacity"
              />
            </>
          )}
        </div>
      )}

      {/* ── MPR Controls Panel (visible in MPR and Split modes) ── */}
      {(viewMode === 'mpr' || viewMode === 'split') && (
        <div className="sidebar-section mpr-controls-section">
          <h2 className="sidebar-heading sidebar-heading--mpr">MPR Controls</h2>

          {mprLoading && (
            <div className="mpr-sidebar-loading">
              <span className="mpr-spinner-sm" />  Loading CT volume…
            </div>
          )}

          {mprError && (
            <div className="mpr-sidebar-error">{mprError}</div>
          )}

          {mprMetadata && !mprLoading && (
            <>
              {/* Window Presets */}
              <div className="mpr-sidebar-presets">
                <span className="mpr-sidebar-presets-label">Window Preset:</span>
                <div className="mpr-sidebar-preset-pills">
                  {Object.entries(mprMetadata.presets || {}).map(([key, defn]) => (
                    <button
                      key={key}
                      id={`sidebar-preset-${key}`}
                      className={`mpr-sidebar-preset-pill ${mprWindowPreset === key ? 'active' : ''}`}
                      onClick={() => onMprPresetSelect && onMprPresetSelect(key)}
                      type="button"
                      title={`WW: ${defn.ww}, WL: ${defn.wl}`}
                    >
                      {defn.name}
                    </button>
                  ))}
                </div>
              </div>

              {/* WW / WL readout */}
              <div className="mpr-sidebar-wl-row">
                <span className="mpr-sidebar-wl-item">
                  <span className="mpr-sidebar-wl-label">WW:</span>
                  <span className="mpr-sidebar-wl-val">{Math.round(mprWindowWidth)}</span>
                </span>
                <span className="mpr-sidebar-wl-item">
                  <span className="mpr-sidebar-wl-label">WL:</span>
                  <span className="mpr-sidebar-wl-val">{Math.round(mprWindowLevel)}</span>
                </span>
              </div>

              {/* Lesion overlay toggle */}
              <button
                id="sidebar-mpr-lesion-overlay-toggle"
                className={`mpr-sidebar-overlay-btn ${mprShowLesionOverlay ? 'active' : ''}`}
                onClick={() => onToggleMprLesionOverlay && onToggleMprLesionOverlay(!mprShowLesionOverlay)}
                type="button"
              >
                {mprShowLesionOverlay ? '🔬 Lesion Overlay On' : '🔬 Lesion Overlay Off'}
              </button>

              {/* Volume info */}
              <div className="mpr-sidebar-vol-info">
                <span className="mpr-sidebar-vol-label">Volume:</span>
                <span className="mpr-sidebar-vol-val">
                  {mprMetadata.shape[0]} × {mprMetadata.shape[1]} × {mprMetadata.shape[2]}
                </span>
              </div>
              <div className="mpr-sidebar-vol-info">
                <span className="mpr-sidebar-vol-label">Spacing:</span>
                <span className="mpr-sidebar-vol-val">
                  {mprMetadata.voxel_spacing_mm[0]} × {mprMetadata.voxel_spacing_mm[1]} × {mprMetadata.voxel_spacing_mm[2]} mm
                </span>
              </div>
            </>
          )}
        </div>
      )}

      {/* ── Footer / New Scan Button ── */}
      <div className="sidebar-footer">
        <button
          id="sidebar-new-scan-button"
          className="btn-sidebar-reset"
          onClick={onReset}
          title="Upload a new CT scan"
        >
          ↩ New Scan
        </button>
      </div>
    </div>
  );
};

export default Sidebar;
