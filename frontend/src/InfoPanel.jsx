import React from 'react';
import { ORGAN_DATA, LESION_VISUAL_CONFIG } from './data';

/**
 * InfoPanel — Displays live measurement data for the selected organ or lesion.
 *
 * Day 14: Extended with lesion spatial metrics panel:
 *   - Volume, bounding box, centroid
 *   - Computational distances to anatomical structures (kd-tree derived)
 *   - Safety disclaimer and computational interpretation labels
 *
 * ⚠️ Medical Safety: All values are computational estimates derived from CT
 *    segmentation models. They do not constitute clinical diagnoses, surgical
 *    margins, or operative recommendations. Requires clinical review.
 */

/** Format a numeric value safely with a unit suffix. */
function fmt(value, suffix = '') {
  if (value === null || value === undefined) return 'Not available';
  if (typeof value === 'number') return `${value.toFixed(2)}${suffix}`;
  return `${value}${suffix}`;
}

/** Format a bounding box object. */
function formatBoundingBox(bbox) {
  if (!bbox) return 'Not available';
  const dims = [
    bbox.x_mm ?? bbox.width_mm ?? bbox.x ?? bbox.width,
    bbox.y_mm ?? bbox.height_mm ?? bbox.y ?? bbox.height,
    bbox.z_mm ?? bbox.depth_mm ?? bbox.z ?? bbox.depth,
  ];
  if (dims.every(d => d !== undefined && d !== null)) {
    return dims.map(d => `${Number(d).toFixed(1)} mm`).join(' × ');
  }
  return JSON.stringify(bbox);
}

/** Format a distance entry from computational_distances. */
function DistanceRow({ name, entry }) {
  const label = name.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());

  if (!entry || entry.status === 'unavailable') {
    return (
      <div className="info-measurement-item">
        <span className="info-measurement-label">{label}</span>
        <span className="info-measurement-value info-measurement-value--unavailable">Not segmented</span>
      </div>
    );
  }

  const dist = entry.minimum_distance_mm;
  const isInside = entry.is_within_organ_parenchyma;
  const tag = isInside !== undefined ? (isInside ? ' (inside)' : '') : '';
  return (
    <div className="info-measurement-item">
      <span className="info-measurement-label">{label}</span>
      <span className="info-measurement-value">
        {dist != null ? `${dist.toFixed(2)} mm${tag}` : 'N/A'}
      </span>
    </div>
  );
}

/** Organ panel: shows mask volume, mesh volume, bounding box */
function OrganPanel({ selectedOrgan, organResults }) {
  const organ = ORGAN_DATA[selectedOrgan];
  return (
    <div className="info-panel">
      <h2 className="info-panel-heading">Selected Structure</h2>
      <div className="info-content">
        <div className="info-organ-identity">
          <span className="info-organ-swatch" style={{ backgroundColor: organ.color }} />
          <h3 className="info-organ-name">{organ.name}</h3>
          <span className="info-structure-badge info-structure-badge--organ">Organ</span>
        </div>

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

        <p className="note info-disclaimer-note">
          <em>Computational estimates for decision support. Requires clinical review.</em>
        </p>
      </div>
    </div>
  );
}

/** Lesion panel: shows volume, bbox, centroid, and spatial distances */
function LesionPanel({ lesion }) {
  const classType = lesion.class_name ?? 'cyst';
  const config = LESION_VISUAL_CONFIG[classType] ?? LESION_VISUAL_CONFIG.cyst;
  const distances = lesion.computational_distances ?? {};
  const centroid = lesion.centroid_mm;
  const dims = lesion.dimensions_mm;

  return (
    <div className="info-panel info-panel--lesion">
      <h2 className="info-panel-heading">Model-Predicted Lesion</h2>
      <div className="info-content">
        {/* Identity */}
        <div className="info-organ-identity">
          <span className="info-organ-swatch" style={{ backgroundColor: config.color }} />
          <h3 className="info-organ-name" style={{ color: config.color }}>
            {config.name}
          </h3>
          <span className="info-structure-badge info-structure-badge--lesion">
            Class {lesion.class_label ?? '?'}
          </span>
        </div>

        {/* Volumetric metrics */}
        <div className="info-measurements">
          <div className="info-measurement-item">
            <span className="info-measurement-label">Volume</span>
            <span className="info-measurement-value" id={`${lesion.lesion_id}-volume`}>
              {lesion.volume_ml != null ? `${lesion.volume_ml.toFixed(4)} mL` : 'Not available'}
            </span>
          </div>

          {dims && (
            <div className="info-measurement-item">
              <span className="info-measurement-label">Dimensions</span>
              <span className="info-measurement-value" id={`${lesion.lesion_id}-dims`}>
                {dims.map(d => `${d.toFixed(1)}`).join(' × ')} mm
              </span>
            </div>
          )}

          {centroid && (
            <div className="info-measurement-item">
              <span className="info-measurement-label">World Centroid</span>
              <span className="info-measurement-value info-measurement-value--mono" id={`${lesion.lesion_id}-centroid`}>
                ({centroid.map(c => c.toFixed(1)).join(', ')}) mm
              </span>
            </div>
          )}
        </div>

        {/* Spatial distances — only shown if any are available */}
        {Object.keys(distances).length > 0 && (
          <>
            <div className="info-distances-section">
              <div className="info-distances-heading">Computational Distances</div>
              <div className="info-distances-grid">
                {Object.entries(distances).map(([name, entry]) => (
                  <DistanceRow key={name} name={name} entry={entry} />
                ))}
              </div>
            </div>
          </>
        )}

        <p className="note info-disclaimer-note">
          <em>Model-derived computational metrics. Not a clinical diagnosis or surgical recommendation.</em>
        </p>
      </div>
    </div>
  );
}

/** Main InfoPanel — switches between organ and lesion views */
const InfoPanel = ({ selectedOrgan, organResults, selectedLesion }) => {
  if (selectedLesion) {
    return <LesionPanel lesion={selectedLesion} />;
  }

  if (!selectedOrgan) {
    return (
      <div className="info-panel empty">
        <p>Select an organ or lesion to view measurements.</p>
      </div>
    );
  }

  return <OrganPanel selectedOrgan={selectedOrgan} organResults={organResults} />;
};

export default InfoPanel;
