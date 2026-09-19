import React, { useState, useRef, useCallback, useEffect } from 'react';
import { getMPRSliceUrl } from './api';

/**
 * MPRViewer — Synchronized Multi-Planar Reconstruction Viewer with Planning Markers.
 *
 * Displays three orthogonal planes (Axial, Coronal, Sagittal) derived from the genuine CT volume.
 * Crosshairs, slice positions, and surgical planning markers are fully synchronized across
 * all 3 planes and with 3D space.
 *
 * Coordinate Mapping:
 * - Voxel Coordinate: [x, y, z] within [0..Nx-1, 0..Ny-1, 0..Nz-1]
 * - Axial Slice: along Z. Display: cols = (Nx-1) - x, rows = (Ny-1) - y
 * - Coronal Slice: along Y. Display: cols = (Nx-1) - x, rows = (Nz-1) - z
 * - Sagittal Slice: along X. Display: cols = (Ny-1) - y, rows = (Nz-1) - z
 */

function clamp(val, min, max) {
  return Math.max(min, Math.min(max, val));
}

const MPRPanel = ({
  plane,
  label,
  sliceIndex,
  totalSlices,
  imageUrl,
  crosshairU,
  crosshairV,
  displayDim, // { width, height }
  showCrosshairs,
  markers = [],
  showPlanningMarkers = true,
  isAnnotationMode = false,
  selectedTarget = null,
  onSliceChange,
  onPanelClick,
  onSelectTarget,
}) => {
  const containerRef = useRef(null);
  const isDraggingRef = useRef(false);

  // Mouse wheel scrolling advances/recedes slices
  const handleWheel = useCallback(
    (e) => {
      e.preventDefault();
      const delta = e.deltaY > 0 ? -1 : 1;
      const nextSlice = clamp(sliceIndex + delta, 0, totalSlices - 1);
      if (nextSlice !== sliceIndex) {
        onSliceChange(nextSlice);
      }
    },
    [sliceIndex, totalSlices, onSliceChange]
  );

  // Calculate click/drag coordinates relative to native image pixels
  const handlePointerAction = useCallback(
    (e) => {
      if (!containerRef.current || !displayDim) return;
      const rect = containerRef.current.getBoundingClientRect();
      const clickX = e.clientX - rect.left;
      const clickY = e.clientY - rect.top;

      // Scale from container rendered size to native slice pixel coordinates
      const scaleX = displayDim.width / rect.width;
      const scaleY = displayDim.height / rect.height;

      const u = clamp(Math.round(clickX * scaleX), 0, displayDim.width - 1);
      const v = clamp(Math.round(clickY * scaleY), 0, displayDim.height - 1);

      onPanelClick(plane, u, v);
    },
    [containerRef, displayDim, onPanelClick, plane]
  );

  const handlePointerDown = (e) => {
    isDraggingRef.current = true;
    handlePointerAction(e);
  };

  const handlePointerMove = (e) => {
    if (isDraggingRef.current && !isAnnotationMode) {
      handlePointerAction(e);
    }
  };

  const handlePointerUp = () => {
    isDraggingRef.current = false;
  };

  // Convert native pixel coordinates to percentage for SVG/crosshair overlay
  const crosshairXPct = displayDim ? (crosshairU / displayDim.width) * 100 : 50;
  const crosshairYPct = displayDim ? (crosshairV / displayDim.height) * 100 : 50;

  return (
    <div className={`mpr-panel ${isAnnotationMode ? 'mpr-panel--annotating' : ''}`} id={`mpr-panel-${plane}`}>
      <div className="mpr-panel-header">
        <span className="mpr-plane-name">{label}</span>
        <span className="mpr-slice-badge">
          Slice {sliceIndex + 1} / {totalSlices}
        </span>
      </div>

      <div
        ref={containerRef}
        className={`mpr-slice-viewport ${isAnnotationMode ? 'cursor-crosshair' : ''}`}
        onWheel={handleWheel}
        onPointerDown={handlePointerDown}
        onPointerMove={handlePointerMove}
        onPointerUp={handlePointerUp}
        onPointerLeave={handlePointerUp}
      >
        <img
          src={imageUrl}
          alt={`${label} CT Slice ${sliceIndex}`}
          className="mpr-slice-image"
          draggable={false}
        />

        {showCrosshairs && displayDim && (
          <div className="mpr-crosshair-overlay" aria-hidden="true">
            {/* Vertical crosshair line */}
            <div
              className="mpr-crosshair-v"
              style={{ left: `${crosshairXPct}%` }}
            />
            {/* Horizontal crosshair line */}
            <div
              className="mpr-crosshair-h"
              style={{ top: `${crosshairYPct}%` }}
            />
            {/* Center target indicator */}
            <div
              className="mpr-crosshair-center"
              style={{ left: `${crosshairXPct}%`, top: `${crosshairYPct}%` }}
            />
          </div>
        )}

        {/* ── Surgical Planning Markers Overlay (Day 17) ── */}
        {showPlanningMarkers && displayDim && (
          <div className="mpr-markers-overlay">
            {markers.map((m) => {
              const isModel = m.source === 'model';
              const markerColor = isModel ? '#00e5ff' : '#f59e0b';
              const isSelected = selectedTarget?.target_id === m.target_id;

              return (
                <div
                  key={m.target_id}
                  className={`mpr-planning-marker ${isSelected ? 'mpr-planning-marker--selected' : ''}`}
                  style={{
                    left: `${m.xPct}%`,
                    top: `${m.yPct}%`,
                    opacity: m.opacity,
                    borderColor: markerColor,
                    boxShadow: `0 0 ${m.dist === 0 ? '8px' : '4px'} ${markerColor}`,
                  }}
                  onClick={(e) => {
                    e.stopPropagation();
                    if (onSelectTarget) onSelectTarget(m);
                  }}
                  title={`${m.label}\nCoord: [${m.voxel_coordinate.join(', ')}]\n${isModel ? 'Computational Model Finding' : 'User Planning Marker'}`}
                >
                  <span
                    className="mpr-marker-dot"
                    style={{ backgroundColor: markerColor }}
                  />
                  {m.dist === 0 && (
                    <span className="mpr-marker-label" style={{ color: markerColor }}>
                      {m.label.length > 20 ? `${m.label.slice(0, 18)}…` : m.label}
                    </span>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Slider scrubber */}
      <div className="mpr-slider-bar">
        <input
          id={`mpr-slider-${plane}`}
          type="range"
          min="0"
          max={totalSlices - 1}
          value={sliceIndex}
          onChange={(e) => onSliceChange(parseInt(e.target.value, 10))}
          className="mpr-slice-slider"
          aria-label={`${label} slice scrubber`}
        />
      </div>
    </div>
  );
};

const MPRViewer = ({
  caseId,
  mprMetadata,
  voxelCursor = [146, 146, 172],
  onCursorChange,
  showLesionOverlay = true,
  onToggleLesionOverlay,
  windowPreset = 'soft_tissue',
  windowWidth = 400,
  windowLevel = 40,
  onWindowChange,
  onPresetSelect,
  // Planning Marker Layer props (Day 17)
  planningTargets = [],
  targetVisibility = {},
  selectedTarget = null,
  onSelectTarget,
  isAnnotationMode = false,
  onToggleAnnotationMode,
  onAddPlanningPoint,
}) => {
  const [showCrosshairs, setShowCrosshairs] = useState(true);
  const [showPlanningMarkers, setShowPlanningMarkers] = useState(true);

  if (!mprMetadata || !caseId) {
    return (
      <div className="mpr-loading-state">
        <div className="mpr-spinner" />
        <p>Loading CT Multi-Planar Reconstruction...</p>
      </div>
    );
  }

  const shape = mprMetadata.shape; // [Nx, Ny, Nz]
  const nx = shape[0];
  const ny = shape[1];
  const nz = shape[2];

  const spacing = mprMetadata.voxel_spacing_mm || [1.5, 1.5, 1.5];
  const affine = mprMetadata.affine;

  const vx = clamp(voxelCursor[0], 0, nx - 1);
  const vy = clamp(voxelCursor[1], 0, ny - 1);
  const vz = clamp(voxelCursor[2], 0, nz - 1);

  // Crosshair coordinates on each display plane:
  // Axial: cols = (Nx-1) - x, rows = (Ny-1) - y
  const axialU = (nx - 1) - vx;
  const axialV = (ny - 1) - vy;

  // Coronal: cols = (Nx-1) - x, rows = (Nz-1) - z
  const coronalU = (nx - 1) - vx;
  const coronalV = (nz - 1) - vz;

  // Sagittal: cols = (Ny-1) - y, rows = (Nz-1) - z
  const sagittalU = (ny - 1) - vy;
  const sagittalV = (nz - 1) - vz;

  // Calculate physical coordinates (origin-relative mm)
  const physX = (vx * spacing[0]).toFixed(1);
  const physY = (vy * spacing[1]).toFixed(1);
  const physZ = (vz * spacing[2]).toFixed(1);

  // Calculate scanner world coordinates if affine matrix is available
  let worldCoords = null;
  if (affine && affine.length === 4) {
    const vh = [vx, vy, vz, 1.0];
    const wx = (affine[0][0]*vh[0] + affine[0][1]*vh[1] + affine[0][2]*vh[2] + affine[0][3]).toFixed(1);
    const wy = (affine[1][0]*vh[0] + affine[1][1]*vh[1] + affine[1][2]*vh[2] + affine[1][3]).toFixed(1);
    const wz = (affine[2][0]*vh[0] + affine[2][1]*vh[1] + affine[2][2]*vh[2] + affine[2][3]).toFixed(1);
    worldCoords = `(${wx}, ${wy}, ${wz}) mm`;
  }

  // ── Calculate Visible Planning Markers for each Orthogonal Plane ──
  const activeTargets = planningTargets.filter(
    (t) => targetVisibility[t.target_id] !== false && t.voxel_coordinate && t.voxel_coordinate.length === 3
  );

  const axialMarkers = activeTargets
    .map((t) => {
      const [tx, ty, tz] = t.voxel_coordinate;
      const dist = Math.abs(tz - vz);
      if (dist > 2) return null;
      const u = (nx - 1) - tx;
      const v = (ny - 1) - ty;
      return {
        ...t,
        xPct: (u / nx) * 100,
        yPct: (v / ny) * 100,
        dist,
        opacity: dist === 0 ? 1.0 : dist === 1 ? 0.7 : 0.35,
      };
    })
    .filter(Boolean);

  const coronalMarkers = activeTargets
    .map((t) => {
      const [tx, ty, tz] = t.voxel_coordinate;
      const dist = Math.abs(ty - vy);
      if (dist > 2) return null;
      const u = (nx - 1) - tx;
      const v = (nz - 1) - tz;
      return {
        ...t,
        xPct: (u / nx) * 100,
        yPct: (v / nz) * 100,
        dist,
        opacity: dist === 0 ? 1.0 : dist === 1 ? 0.7 : 0.35,
      };
    })
    .filter(Boolean);

  const sagittalMarkers = activeTargets
    .map((t) => {
      const [tx, ty, tz] = t.voxel_coordinate;
      const dist = Math.abs(tx - vx);
      if (dist > 2) return null;
      const u = (ny - 1) - ty;
      const v = (nz - 1) - tz;
      return {
        ...t,
        xPct: (u / ny) * 100,
        yPct: (v / nz) * 100,
        dist,
        opacity: dist === 0 ? 1.0 : dist === 1 ? 0.7 : 0.35,
      };
    })
    .filter(Boolean);

  // Slice change handlers
  const handleAxialSliceChange = (newZ) => {
    onCursorChange([vx, vy, newZ]);
  };

  const handleCoronalSliceChange = (newY) => {
    onCursorChange([vx, newY, vz]);
  };

  const handleSagittalSliceChange = (newX) => {
    onCursorChange([newX, vy, vz]);
  };

  // Click on panel handlers
  const handlePanelClick = (plane, u, v) => {
    let newVoxel = [vx, vy, vz];
    if (plane === 'axial') {
      const newX = (nx - 1) - u;
      const newY = (ny - 1) - v;
      newVoxel = [newX, newY, vz];
    } else if (plane === 'coronal') {
      const newX = (nx - 1) - u;
      const newZ = (nz - 1) - v;
      newVoxel = [newX, vy, newZ];
    } else if (plane === 'sagittal') {
      const newY = (ny - 1) - u;
      const newZ = (nz - 1) - v;
      newVoxel = [vx, newY, newZ];
    }

    onCursorChange(newVoxel);

    // If explicit annotation mode is active, trigger planning point creation
    if (isAnnotationMode && onAddPlanningPoint) {
      onAddPlanningPoint(newVoxel);
    }
  };

  // Build slice URLs with current WW/WL and overlay option
  const axialUrl = getMPRSliceUrl(caseId, 'axial', vz, windowWidth, windowLevel, showLesionOverlay);
  const coronalUrl = getMPRSliceUrl(caseId, 'coronal', vy, windowWidth, windowLevel, showLesionOverlay);
  const sagittalUrl = getMPRSliceUrl(caseId, 'sagittal', vx, windowWidth, windowLevel, showLesionOverlay);

  const presets = mprMetadata.presets || {};

  return (
    <div className="mpr-container">
      {/* ── Top Controls Bar: Presets, Windowing, Options, Planning ── */}
      <div className="mpr-toolbar">
        <div className="mpr-presets-group">
          <span className="mpr-toolbar-label">Preset:</span>
          {Object.entries(presets).map(([key, defn]) => (
            <button
              key={key}
              id={`btn-preset-${key}`}
              className={`mpr-preset-btn ${windowPreset === key ? 'active' : ''}`}
              onClick={() => onPresetSelect && onPresetSelect(key)}
              type="button"
            >
              {defn.name}
            </button>
          ))}
        </div>

        <div className="mpr-window-inputs">
          <div className="mpr-input-pill">
            <span className="mpr-pill-label">WW:</span>
            <span className="mpr-pill-value">{Math.round(windowWidth)}</span>
          </div>
          <div className="mpr-input-pill">
            <span className="mpr-pill-label">WL:</span>
            <span className="mpr-pill-value">{Math.round(windowLevel)}</span>
          </div>
        </div>

        <div className="mpr-toggles-group">
          <button
            id="btn-toggle-crosshairs"
            className={`mpr-toggle-btn ${showCrosshairs ? 'active' : ''}`}
            onClick={() => setShowCrosshairs(!showCrosshairs)}
            title="Toggle crosshair overlays"
            type="button"
          >
            {showCrosshairs ? '🎯 Crosshair On' : '🎯 Crosshair Off'}
          </button>

          <button
            id="btn-toggle-lesion-overlay"
            className={`mpr-toggle-btn ${showLesionOverlay ? 'active' : ''}`}
            onClick={() => onToggleLesionOverlay && onToggleLesionOverlay(!showLesionOverlay)}
            title="Toggle genuine lesion mask overlay in 2D slices"
            type="button"
          >
            {showLesionOverlay ? '🔬 Lesion Overlay On' : '🔬 Lesion Overlay Off'}
          </button>

          <button
            id="btn-toggle-planning-markers"
            className={`mpr-toggle-btn ${showPlanningMarkers ? 'active' : ''}`}
            onClick={() => setShowPlanningMarkers(!showPlanningMarkers)}
            title="Toggle surgical planning markers on 2D slices"
            type="button"
          >
            {showPlanningMarkers ? '📍 Markers On' : '📍 Markers Off'}
          </button>

          {onToggleAnnotationMode && (
            <button
              id="btn-toggle-annotation-mode"
              className={`mpr-toggle-btn mpr-toggle-btn--annotate ${isAnnotationMode ? 'active' : ''}`}
              onClick={() => onToggleAnnotationMode(!isAnnotationMode)}
              title="Click slice to add a surgical planning reference point"
              type="button"
            >
              {isAnnotationMode ? '✏️ Annotation Mode ON' : '➕ Add Point'}
            </button>
          )}
        </div>
      </div>

      {/* ── Active Annotation Mode Notice ── */}
      {isAnnotationMode && (
        <div className="mpr-annotation-banner" id="mpr-annotation-banner">
          <span className="mpr-annotation-pulse" />
          <span className="mpr-annotation-text">
            <strong>Annotation Mode Active:</strong> Click on any CT slice to place a surgical planning reference point.
          </span>
          <button
            className="mpr-annotation-cancel-btn"
            onClick={() => onToggleAnnotationMode(false)}
            type="button"
          >
            ✕ Exit Mode
          </button>
        </div>
      )}

      {/* ── Three Orthogonal Panels Grid ── */}
      <div className="mpr-grid">
        {/* Panel 1: Axial (Z) */}
        <MPRPanel
          plane="axial"
          label="Axial (Z)"
          sliceIndex={vz}
          totalSlices={nz}
          imageUrl={axialUrl}
          crosshairU={axialU}
          crosshairV={axialV}
          displayDim={{ width: nx, height: ny }}
          showCrosshairs={showCrosshairs}
          markers={axialMarkers}
          showPlanningMarkers={showPlanningMarkers}
          isAnnotationMode={isAnnotationMode}
          selectedTarget={selectedTarget}
          onSliceChange={handleAxialSliceChange}
          onPanelClick={handlePanelClick}
          onSelectTarget={onSelectTarget}
        />

        {/* Panel 2: Coronal (Y) */}
        <MPRPanel
          plane="coronal"
          label="Coronal (Y)"
          sliceIndex={vy}
          totalSlices={ny}
          imageUrl={coronalUrl}
          crosshairU={coronalU}
          crosshairV={coronalV}
          displayDim={{ width: nx, height: nz }}
          showCrosshairs={showCrosshairs}
          markers={coronalMarkers}
          showPlanningMarkers={showPlanningMarkers}
          isAnnotationMode={isAnnotationMode}
          selectedTarget={selectedTarget}
          onSliceChange={handleCoronalSliceChange}
          onPanelClick={handlePanelClick}
          onSelectTarget={onSelectTarget}
        />

        {/* Panel 3: Sagittal (X) */}
        <MPRPanel
          plane="sagittal"
          label="Sagittal (X)"
          sliceIndex={vx}
          totalSlices={nx}
          imageUrl={sagittalUrl}
          crosshairU={sagittalU}
          crosshairV={sagittalV}
          displayDim={{ width: ny, height: nz }}
          showCrosshairs={showCrosshairs}
          markers={sagittalMarkers}
          showPlanningMarkers={showPlanningMarkers}
          isAnnotationMode={isAnnotationMode}
          selectedTarget={selectedTarget}
          onSliceChange={handleSagittalSliceChange}
          onPanelClick={handlePanelClick}
          onSelectTarget={onSelectTarget}
        />
      </div>

      {/* ── Synchronized Status / Coordinate Bar ── */}
      <div className="mpr-status-bar">
        <div className="mpr-status-item">
          <span className="mpr-status-label">Voxel Cursor:</span>
          <span className="mpr-status-value">
            ({vx}, {vy}, {vz})
          </span>
        </div>

        <div className="mpr-status-item">
          <span className="mpr-status-label">Physical mm:</span>
          <span className="mpr-status-value">
            ({physX}, {physY}, {physZ}) mm
          </span>
        </div>

        {worldCoords && (
          <div className="mpr-status-item">
            <span className="mpr-status-label">Scanner World:</span>
            <span className="mpr-status-value">{worldCoords}</span>
          </div>
        )}

        <div className="mpr-status-item">
          <span className="mpr-status-label">CT Spacing:</span>
          <span className="mpr-status-value">
            {spacing[0]} × {spacing[1]} × {spacing[2]} mm
          </span>
        </div>

        {planningTargets.length > 0 && (
          <div className="mpr-status-item">
            <span className="mpr-status-label">Active Targets:</span>
            <span className="mpr-status-value">
              {activeTargets.length} / {planningTargets.length}
            </span>
          </div>
        )}
      </div>
    </div>
  );
};

export default MPRViewer;
