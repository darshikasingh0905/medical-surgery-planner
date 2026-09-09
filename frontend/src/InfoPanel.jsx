import React from 'react';
import { ORGAN_DATA } from './data';

/**
 * InfoPanel — Displays live measurement data for the selected organ.
 *
 * Props:
 *   selectedOrgan  {string|null}  — key of the selected organ in ORGAN_DATA
 *   organResults   {object|null}  — measurement data from GET /api/cases/{id}/results
 *                                   Structure (from measurement_engine):
 *                                   {
 *                                     mask_volume_ml: number,
 *                                     mesh_volume_ml: number,
 *                                     bounding_box: { x_mm, y_mm, z_mm } or object,
 *                                     ...
 *                                   }
 *
 * All values come from the live backend. If a field is missing, "Not available" is shown.
 * Hardcoded Day 4 values are no longer used.
 *
 * ⚠️ Medical Safety: Values shown are computational estimates for decision support only.
 */

/**
 * Format a measurement value safely.
 * Returns the value as a string, or 'Not available' if null/undefined.
 */
function fmt(value, suffix = '') {
  if (value === null || value === undefined) return 'Not available';
  if (typeof value === 'number') return `${value.toFixed(2)}${suffix}`;
  return `${value}${suffix}`;
}

/**
 * Format a bounding box object into a human-readable string.
 * Handles both { x_mm, y_mm, z_mm } and { width, height, depth } or similar shapes.
 */
function formatBoundingBox(bbox) {
  if (!bbox) return 'Not available';
  // Try common key patterns from the measurement engine
  const dims = [
    bbox.x_mm ?? bbox.width_mm ?? bbox.x ?? bbox.width,
    bbox.y_mm ?? bbox.height_mm ?? bbox.y ?? bbox.height,
    bbox.z_mm ?? bbox.depth_mm ?? bbox.z ?? bbox.depth,
  ];
  if (dims.every(d => d !== undefined && d !== null)) {
    return dims.map(d => `${Number(d).toFixed(1)} mm`).join(' × ');
  }
  // Fallback: stringify the whole object
  return JSON.stringify(bbox);
}

const InfoPanel = ({ selectedOrgan, organResults }) => {
  if (!selectedOrgan) {
    return (
      <div className="info-panel empty">
        <p>Select an organ from the panel to view measurements.</p>
      </div>
    );
  }

  const organ = ORGAN_DATA[selectedOrgan];

  return (
    <div className="info-panel">
      <h2 className="info-panel-heading">Selected Organ Information</h2>
      <div className="info-content">
        {/* Organ name with color swatch */}
        <div className="info-organ-identity">
          <span className="info-organ-swatch" style={{ backgroundColor: organ.color }} />
          <h3 className="info-organ-name">{organ.name}</h3>
        </div>

        {/* Measurement fields */}
        <div className="info-measurements">
          <div className="info-measurement-item">
            <span className="info-measurement-label">Mask Volume</span>
            <span className="info-measurement-value" id={`${selectedOrgan}-mask-volume`}>
              {fmt(organResults?.mask_volume_ml, ' mL')}
            </span>
          </div>

          <div className="info-measurement-item">
            <span className="info-measurement-label">Mesh Volume</span>
            <span className="info-measurement-value" id={`${selectedOrgan}-mesh-volume`}>
              {fmt(organResults?.mesh_volume_ml, ' mL')}
            </span>
          </div>

          <div className="info-measurement-item">
            <span className="info-measurement-label">Bounding Box</span>
            <span className="info-measurement-value" id={`${selectedOrgan}-bounding-box`}>
              {formatBoundingBox(organResults?.bounding_box)}
            </span>
          </div>
        </div>

        {/* Medical disclaimer note */}
        <p className="note info-disclaimer-note">
          <em>Computational estimates for decision support. Requires clinical review.</em>
        </p>
      </div>
    </div>
  );
};

export default InfoPanel;
