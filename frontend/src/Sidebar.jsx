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
}) => {
  return (
    <div className="sidebar">
      {/* ── View Mode Switcher ── */}
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
