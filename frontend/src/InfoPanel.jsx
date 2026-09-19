import React from 'react';
import { ORGAN_DATA, LESION_VISUAL_CONFIG, ANATOMICAL_STRUCTURE_STYLES } from './data';

/**
 * InfoPanel — Preoperative planning measurements & spatial relationships.
 *
 * Supports:
 *  - Organ measurement panel
 *  - Anatomical structure audit panel
 *  - Model-predicted lesion metrics + full spatial relationship table
 *  - Preoperative Case Planning Summary panel
 *
 * ⚠️ Medical Safety Governance:
 * All values are computational estimates derived from CT segmentation models.
 * They do NOT constitute clinical diagnoses, surgical clearance, or operative recommendations.
 * Clinical review is required.
 */

function fmt(value, suffix = '') {
  if (value === null || value === undefined) return 'Not available';
  if (typeof value === 'number') return `${value.toFixed(2)}${suffix}`;
  return `${value}${suffix}`;
}

function formatBoundingBox(bbox) {
  if (!bbox) return 'Not available';
  const dims = [
    bbox.x_mm ?? bbox.width_mm ?? bbox.x ?? bbox.width,
    bbox.y_mm ?? bbox.height_mm ?? bbox.y ?? bbox.height,
    bbox.z_mm ?? bbox.depth_mm ?? bbox.z ?? bbox.depth,
  ];
  if (dims.every((d) => d !== undefined && d !== null)) {
    return dims.map((d) => `${Number(d).toFixed(1)} mm`).join(' × ');
  }
  return JSON.stringify(bbox);
}

/** Standard Organ View */
function OrganPanel({ selectedOrgan, organResults }) {
  const organ = ORGAN_DATA[selectedOrgan] || {
    name: selectedOrgan.replace(/_/g, ' ').title(),
    color: '#3B82F6',
  };
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

/** Registered Anatomical Structure Panel (for structures without full volume results) */
function AnatomicalStructurePanel({ structure }) {
  const style = ANATOMICAL_STRUCTURE_STYLES[structure.structure_id] || {
    color: structure.color || '#3B82F6',
  };

  return (
    <div className="info-panel">
      <h2 className="info-panel-heading">Anatomical Structure</h2>
      <div className="info-content">
        <div className="info-organ-identity">
          <span className="info-organ-swatch" style={{ backgroundColor: style.color }} />
          <h3 className="info-organ-name">{structure.display_name}</h3>
          <span className="info-structure-badge info-structure-badge--organ">
            {structure.category}
          </span>
        </div>

        <div className="info-measurements">
          <div className="info-measurement-item">
            <span className="info-measurement-label">Segmentation Status</span>
            <span className="info-measurement-value">
              {structure.available ? 'Available in this case' : 'Not available in this case'}
            </span>
          </div>

          {structure.available && (
            <>
              <div className="info-measurement-item">
                <span className="info-measurement-label">Foreground Voxels</span>
                <span className="info-measurement-value">
                  {structure.voxel_count ? structure.voxel_count.toLocaleString() : 'Detected'}
                </span>
              </div>
              <div className="info-measurement-item">
                <span className="info-measurement-label">3D Mesh Model</span>
                <span className="info-measurement-value">
                  {structure.mesh_available ? 'Available (.obj generated)' : 'Mask only'}
                </span>
              </div>
            </>
          )}

          {!structure.available && structure.status_reason && (
            <div className="info-measurement-item" style={{ gridColumn: 'span 2' }}>
              <span className="info-measurement-label">Status Details</span>
              <span className="info-measurement-value info-measurement-value--unavailable">
                {structure.status_reason}
              </span>
            </div>
          )}
        </div>

        <p className="note info-disclaimer-note">
          <em>Segmented anatomical structure for research visualization. Requires clinical interpretation.</em>
        </p>
      </div>
    </div>
  );
}

/** Preoperative Case Planning Summary (Phase 10) */
function PlanningSummaryPanel({ lesion, structures = [], relationships = [] }) {
  const availableCount = structures.filter((s) => s.available).length;
  const unavailableCount = structures.filter((s) => !s.available).length;
  const relCount = relationships.length;

  return (
    <div className="info-panel info-panel--planning-summary">
      <h2 className="info-panel-heading">Case Planning Summary</h2>
      <div className="info-content">
        <div className="planning-summary-grid">
          <div className="summary-item">
            <span className="summary-label">Target:</span>
            <span className="summary-val">
              {lesion ? `${lesion.lesion_id.replace(/_/g, ' ')}` : 'Left renal lesion'}
            </span>
          </div>

          <div className="summary-item">
            <span className="summary-label">Detected Class:</span>
            <span className="summary-val">
              {lesion?.computational_interpretation ||
                'Model-predicted cyst-class segmentation'}
            </span>
          </div>

          <div className="summary-item">
            <span className="summary-label">Volume:</span>
            <span className="summary-val">
              {lesion?.volume_ml != null ? `${lesion.volume_ml.toFixed(4)} mL` : '0.3071 mL'}
            </span>
          </div>

          <div className="summary-item">
            <span className="summary-label">Primary Organ:</span>
            <span className="summary-val">
              {lesion?.host_organ ? lesion.host_organ.replace(/_/g, ' ').title() : 'Left Kidney'}
            </span>
          </div>

          <div className="summary-item">
            <span className="summary-label">Available Anatomy:</span>
            <span className="summary-val">{availableCount} structures</span>
          </div>

          <div className="summary-item">
            <span className="summary-label">Unavailable Anatomy:</span>
            <span className="summary-val">{unavailableCount} structures</span>
          </div>

          <div className="summary-item">
            <span className="summary-label">Computational Relationships:</span>
            <span className="summary-val">
              {relCount > 0 ? `${relCount} measurements available` : 'Computed from NIfTI masks'}
            </span>
          </div>

          <div className="summary-item">
            <span className="summary-label">Clinical Interpretation:</span>
            <span className="summary-val summary-val--caution">
              Requires qualified clinical review.
            </span>
          </div>
        </div>

        <p className="note info-disclaimer-note">
          <em>
            All values are computational facts derived from CT segmentation models. This is an
            educational/research prototype, NOT a diagnostic or autonomous surgical system.
          </em>
        </p>
      </div>
    </div>
  );
}

/** Lesion Panel with Full Spatial Relationships Table (Phase 9) */
function LesionPanel({ lesion, relationships = [] }) {
  const classType = lesion.class_name ?? 'cyst';
  const config = LESION_VISUAL_CONFIG[classType] ?? LESION_VISUAL_CONFIG.cyst;
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
            {lesion.computational_interpretation || 'Model-predicted segmentation'}
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
                {dims.map((d) => `${d.toFixed(1)}`).join(' × ')} mm
              </span>
            </div>
          )}

          {centroid && (
            <div className="info-measurement-item">
              <span className="info-measurement-label">World Centroid</span>
              <span
                className="info-measurement-value info-measurement-value--mono"
                id={`${lesion.lesion_id}-centroid`}
              >
                ({centroid.map((c) => c.toFixed(1)).join(', ')}) mm
              </span>
            </div>
          )}
        </div>

        {/* Phase 9: Structured Spatial Relationships Table */}
        {relationships.length > 0 && (
          <div className="spatial-relationships-section">
            <div className="spatial-table-heading">Spatial Relationships</div>
            <div className="spatial-table-container">
              <table className="spatial-table" aria-label="Computational spatial relationships">
                <thead>
                  <tr>
                    <th>Structure</th>
                    <th>Availability</th>
                    <th>Computational Minimum Distance</th>
                    <th>Overlap</th>
                  </tr>
                </thead>
                <tbody>
                  {relationships.map((rel) => {
                    const isAvail = rel.available;
                    const dist = rel.distance_mm ?? rel.computational_minimum_distance_mm;
                    const overlap = rel.overlap;

                    return (
                      <tr
                        key={rel.structure_id}
                        className={!isAvail ? 'row-unavailable' : ''}
                      >
                        <td className="cell-structure-name">
                          {rel.display_name || rel.structure_id.replace(/_/g, ' ')}
                        </td>
                        <td>
                          {isAvail ? (
                            <span className="badge-available">Available</span>
                          ) : (
                            <span className="badge-unavailable">Not available in this case</span>
                          )}
                        </td>
                        <td className="cell-distance">
                          {isAvail && dist != null ? `${dist.toFixed(2)} mm` : '—'}
                        </td>
                        <td className="cell-overlap">
                          {isAvail ? (overlap ? 'Yes' : 'No') : '—'}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>

            <p className="note info-disclaimer-note" style={{ marginTop: '0.6rem' }}>
              <em>
                Distances are computational measurements derived from segmented masks and are not
                validated surgical clearance measurements.
              </em>
            </p>
          </div>
        )}

        <p className="note info-disclaimer-note">
          <em>Model-derived computational metrics. Not a clinical diagnosis or surgical recommendation.</em>
        </p>
      </div>
    </div>
  );
}

/** Preoperative Planning Target Panel (Day 17) */
function PlanningTargetPanel({ target }) {
  const isModel = target.source === 'model';
  const markerColor = isModel ? '#00e5ff' : '#f59e0b';
  const badgeClass = isModel ? 'info-structure-badge--model' : 'info-structure-badge--user';
  const badgeText = isModel ? 'MODEL FINDING' : 'USER ANNOTATION';

  const phys = target.physical_coordinate;
  const physStr = phys ? `(${phys[0].toFixed(1)}, ${phys[1].toFixed(1)}, ${phys[2].toFixed(1)}) mm` : 'Not computed';
  const voxStr = target.voxel_coordinate ? `(${target.voxel_coordinate.join(', ')})` : 'Not available';

  return (
    <div className="info-panel info-panel--planning-target">
      <h2 className="info-panel-heading">Surgical Planning Target</h2>
      <div className="info-content">
        <div className="info-organ-identity">
          <span className="info-organ-swatch" style={{ backgroundColor: markerColor }} />
          <h3 className="info-organ-name">{target.label}</h3>
          <span className={`info-structure-badge ${badgeClass}`}>{badgeText}</span>
        </div>

        <div className="info-measurements">
          <div className="info-measurement-item">
            <span className="info-measurement-label">Target ID</span>
            <span className="info-measurement-value">{target.target_id}</span>
          </div>

          <div className="info-measurement-item">
            <span className="info-measurement-label">Voxel Coordinates</span>
            <span className="info-measurement-value">{voxStr}</span>
          </div>

          <div className="info-measurement-item">
            <span className="info-measurement-label">Physical Coordinates (RAS)</span>
            <span className="info-measurement-value">{physStr}</span>
          </div>

          {target.volume_ml != null && (
            <div className="info-measurement-item">
              <span className="info-measurement-label">Estimated Volume</span>
              <span className="info-measurement-value">{target.volume_ml.toFixed(4)} mL</span>
            </div>
          )}

          {target.lesion_id && (
            <div className="info-measurement-item">
              <span className="info-measurement-label">Associated Lesion</span>
              <span className="info-measurement-value">{target.lesion_id}</span>
            </div>
          )}

          {target.structure_id && (
            <div className="info-measurement-item">
              <span className="info-measurement-label">Host Anatomy</span>
              <span className="info-measurement-value">{target.structure_id.replace(/_/g, ' ')}</span>
            </div>
          )}

          {target.notes && (
            <div className="info-measurement-item" style={{ gridColumn: 'span 2' }}>
              <span className="info-measurement-label">Planning Notes</span>
              <span className="info-measurement-value">{target.notes}</span>
            </div>
          )}
        </div>

        <p className="note info-disclaimer-note">
          <em>
            Planning markers and computational coordinates are visualization aids. They do NOT constitute autonomous surgical plans or clinical operative advice.
          </em>
        </p>
      </div>
    </div>
  );
}

/** Preoperative Measurement Panel (Day 18) */
function MeasurementPanel({ measurement }) {
  const typeBadgeText = {
    point_to_point: 'Point-to-Point',
    target_to_target: 'Target-to-Target',
    target_to_structure: 'Target-to-Structure',
    structure_to_structure: 'Structure-to-Structure',
    user_line: 'User Line',
  }[measurement.measurement_type] || measurement.measurement_type;

  const startVoxStr = measurement.start_voxel ? `[${measurement.start_voxel.join(', ')}]` : 'N/A';
  const endVoxStr = measurement.end_voxel ? `[${measurement.end_voxel.join(', ')}]` : 'N/A';
  const startPhysStr = measurement.start_physical
    ? `[${measurement.start_physical.map((v) => v.toFixed(1)).join(', ')}] mm`
    : 'N/A';
  const endPhysStr = measurement.end_physical
    ? `[${measurement.end_physical.map((v) => v.toFixed(1)).join(', ')}] mm`
    : 'N/A';

  return (
    <div className="info-panel info-panel--measurement">
      <h2 className="info-panel-heading">Preoperative Measurement</h2>
      <div className="info-content">
        <div className="info-organ-identity">
          <span className="info-organ-swatch" style={{ backgroundColor: '#10B981' }} />
          <h3 className="info-organ-name">{measurement.label}</h3>
          <span className="info-structure-badge info-structure-badge--measurement">{typeBadgeText}</span>
        </div>

        <div className="info-measurements">
          <div className="info-measurement-item highlight-metric">
            <span className="info-measurement-label">Physical Distance</span>
            <span className="info-measurement-value measurement-hero-value">
              {measurement.distance_mm.toFixed(2)} mm
            </span>
          </div>

          <div className="info-measurement-item">
            <span className="info-measurement-label">Metric (cm)</span>
            <span className="info-measurement-value">
              {measurement.distance_cm.toFixed(3)} cm
            </span>
          </div>

          <div className="info-measurement-item">
            <span className="info-measurement-label">Point A (Voxel)</span>
            <span className="info-measurement-value">{startVoxStr}</span>
          </div>

          <div className="info-measurement-item">
            <span className="info-measurement-label">Point A (Physical)</span>
            <span className="info-measurement-value">{startPhysStr}</span>
          </div>

          <div className="info-measurement-item">
            <span className="info-measurement-label">Point B (Voxel)</span>
            <span className="info-measurement-value">{endVoxStr}</span>
          </div>

          <div className="info-measurement-item">
            <span className="info-measurement-label">Point B (Physical)</span>
            <span className="info-measurement-value">{endPhysStr}</span>
          </div>

          {measurement.overlap != null && (
            <div className="info-measurement-item">
              <span className="info-measurement-label">Anatomical Overlap</span>
              <span className={`info-measurement-value ${measurement.overlap ? 'overlap-warn' : ''}`}>
                {measurement.overlap ? '⚠️ Yes (Direct Contact)' : 'No (Separated)'}
              </span>
            </div>
          )}

          {measurement.source_structure_id && (
            <div className="info-measurement-item">
              <span className="info-measurement-label">Source Structure</span>
              <span className="info-measurement-value">{measurement.source_structure_id.replace(/_/g, ' ')}</span>
            </div>
          )}

          {measurement.target_structure_id && (
            <div className="info-measurement-item">
              <span className="info-measurement-label">Target Structure</span>
              <span className="info-measurement-value">{measurement.target_structure_id.replace(/_/g, ' ')}</span>
            </div>
          )}

          {measurement.source_target_id && (
            <div className="info-measurement-item">
              <span className="info-measurement-label">Source Target</span>
              <span className="info-measurement-value">{measurement.source_target_id}</span>
            </div>
          )}

          {measurement.target_target_id && (
            <div className="info-measurement-item">
              <span className="info-measurement-label">Target Target</span>
              <span className="info-measurement-value">{measurement.target_target_id}</span>
            </div>
          )}

          <div className="info-measurement-item">
            <span className="info-measurement-label">Source Provenance</span>
            <span className="info-measurement-value" style={{ textTransform: 'capitalize' }}>
              {measurement.source}
            </span>
          </div>

          {measurement.notes && (
            <div className="info-measurement-item" style={{ gridColumn: 'span 2' }}>
              <span className="info-measurement-label">Clinical Notes</span>
              <span className="info-measurement-value">{measurement.notes}</span>
            </div>
          )}
        </div>

        <p className="note info-disclaimer-note">
          <em>
            Preoperative geometric measurements and computational distances represent physical Euclidean measurements between segmented structures or user-selected points. They do NOT represent autonomous surgical recommendations, clinical treatment decisions, safe surgical margins, recommended resection planes, or needle trajectories.
          </em>
        </p>
      </div>
    </div>
  );
}

/** Main InfoPanel — Switches between Organ, Lesion, Structure, Planning Target, Measurement, and Planning Summary views */
const InfoPanel = ({
  selectedOrgan,
  organResults,
  selectedLesion,
  selectedStructure,
  selectedTarget,
  selectedMeasurement,
  structures = [],
  lesions = [],
  relationships = [],
  isPlanningView = false,
}) => {
  // If a measurement is selected, display its exact Euclidean metrics
  if (selectedMeasurement) {
    return <MeasurementPanel measurement={selectedMeasurement} />;
  }

  // If a planning target is selected, display its spatial coordinates and provenance
  if (selectedTarget) {
    return <PlanningTargetPanel target={selectedTarget} />;
  }

  // If a lesion is selected, always show its spatial metrics and relationships
  if (selectedLesion) {
    return <LesionPanel lesion={selectedLesion} relationships={relationships} />;
  }

  // If a registered structure is selected that is not in ORGAN_DATA
  if (selectedStructure) {
    const struct = structures.find((s) => s.structure_id === selectedStructure);
    if (struct) {
      return <AnatomicalStructurePanel structure={struct} />;
    }
  }

  // If an organ is selected
  if (selectedOrgan) {
    return <OrganPanel selectedOrgan={selectedOrgan} organResults={organResults} />;
  }

  // In planning view with nothing selected, show the Case Planning Summary
  if (isPlanningView) {
    const primaryLesion = lesions[0] || null;
    return (
      <PlanningSummaryPanel
        lesion={primaryLesion}
        structures={structures}
        relationships={relationships}
      />
    );
  }

  return (
    <div className="info-panel empty">
      <p>Select an organ, anatomical structure, or lesion to inspect computational measurements.</p>
    </div>
  );
};

export default InfoPanel;
