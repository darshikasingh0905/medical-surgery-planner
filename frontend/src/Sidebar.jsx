import React from 'react';
import { ORGAN_DATA } from './data';

/**
 * Sidebar — Organ list with visibility toggles and selection.
 *
 * Props:
 *   selectedOrgan       {string|null}   — currently selected organ key
 *   onSelectOrgan       {function}      — called with organ key on click
 *   visibility          {object}        — map of organId → boolean
 *   onToggleVisibility  {function}      — called with organ key to toggle
 *   onReset             {function}      — called to return to the upload screen
 */
const Sidebar = ({ selectedOrgan, onSelectOrgan, visibility, onToggleVisibility, onReset }) => {
  return (
    <div className="sidebar">
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

      {/* Upload new scan button */}
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
