import React from 'react';
import { ORGAN_DATA, LESION_VISUAL_CONFIG } from './data';

/**
 * Sidebar — Organ list with visibility toggles, plus lesion section when available.
 *
 * Day 14 additions:
 *  - Lesion section rendered below organs when lesions are present
 *  - Lesion visibility toggle
 *  - "Focus" button to trigger camera zoom to lesion centroid
 *  - Active lesion selection highlight
 *
 * Props:
 *   selectedOrgan       {string|null}    — currently selected organ key
 *   onSelectOrgan       {function}       — called with organ key on click
 *   visibility          {object}         — map of organId → boolean
 *   onToggleVisibility  {function}       — called with organ key to toggle
 *   lesions             {Array}          — lesion objects from API
 *   lesionVisibility    {object}         — map of lesionId → boolean
 *   onToggleLesion      {function}       — called with lesionId to toggle visibility
 *   selectedLesion      {object|null}    — currently selected lesion object
 *   onSelectLesion      {function}       — called with lesion object on click
 *   onFocusLesion       {function}       — called with lesion object to trigger camera focus
 *   onReset             {function}       — called to return to the upload screen
 */
const Sidebar = ({
  selectedOrgan,
  onSelectOrgan,
  visibility,
  onToggleVisibility,
  lesions = [],
  lesionVisibility = {},
  onToggleLesion,
  selectedLesion,
  onSelectLesion,
  onFocusLesion,
  onReset,
}) => {
  return (
    <div className="sidebar">
      {/* ── Organ section ── */}
      <h2 className="sidebar-heading">Organ Panel</h2>

      <ul className="organ-list" aria-label="Organ list">
        {Object.keys(ORGAN_DATA).map(key => {
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

      {/* ── Lesion section (only rendered when lesions present) ── */}
      {lesions.length > 0 && (
        <>
          <h2 className="sidebar-heading sidebar-heading--lesion">
            Model-Predicted Lesions
            <span className="sidebar-lesion-count">{lesions.length}</span>
          </h2>

          <ul className="organ-list lesion-list" aria-label="Lesion list">
            {lesions.map(lesion => {
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
                  <span className="organ-name lesion-name">
                    {lesion.lesion_id.replace(/_/g, ' ')}
                  </span>
                  <span className="lesion-volume-pill">
                    {lesion.volume_ml != null ? `${lesion.volume_ml.toFixed(2)} mL` : '?'}
                  </span>

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
        </>
      )}

      {/* ── Upload new scan button ── */}
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
