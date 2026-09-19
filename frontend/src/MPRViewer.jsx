import React, { useState, useRef, useCallback, useEffect } from 'react';
import { getMPRSliceUrl } from './api';

/**
 * MPRViewer — Synchronized Multi-Planar Reconstruction Viewer.
 *
 * Displays three orthogonal planes (Axial, Coronal, Sagittal) derived from the genuine CT volume.
 * Crosshairs and slice positions are fully synchronized across all 3 planes and with 3D space.
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
  onSliceChange,
  onPanelClick,
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
    if (isDraggingRef.current) {
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
    <div className="mpr-panel" id={`mpr-panel-${plane}`}>
      <div className="mpr-panel-header">
        <span className="mpr-plane-name">{label}</span>
        <span className="mpr-slice-badge">
          Slice {sliceIndex + 1} / {totalSlices}
        </span>
      </div>

      <div
        ref={containerRef}
        className="mpr-slice-viewport"
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
}) => {
  const [showCrosshairs, setShowCrosshairs] = useState(true);

  if (!mprMetadata || !caseId) {
    return (
      <div className="mpr-loading-state">
        <div className="mpr-spinner" />
        <p>Loading CT Multi-Planar Reconstruction...</p>
      </div>
    );
  }

  const shape = mprMetadata.shape; // [Nx, Ny, Nz] = [293, 293, 344]
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
    if (plane === 'axial') {
      const newX = (nx - 1) - u;
      const newY = (ny - 1) - v;
      onCursorChange([newX, newY, vz]);
    } else if (plane === 'coronal') {
      const newX = (nx - 1) - u;
      const newZ = (nz - 1) - v;
      onCursorChange([newX, vy, newZ]);
    } else if (plane === 'sagittal') {
      const newY = (ny - 1) - u;
      const newZ = (nz - 1) - v;
      onCursorChange([vx, newY, newZ]);
    }
  };

  // Build slice URLs with current WW/WL and overlay option
  const axialUrl = getMPRSliceUrl(caseId, 'axial', vz, windowWidth, windowLevel, showLesionOverlay);
  const coronalUrl = getMPRSliceUrl(caseId, 'coronal', vy, windowWidth, windowLevel, showLesionOverlay);
  const sagittalUrl = getMPRSliceUrl(caseId, 'sagittal', vx, windowWidth, windowLevel, showLesionOverlay);

  const presets = mprMetadata.presets || {};

  return (
    <div className="mpr-container">
      {/* ── Top Controls Bar: Presets, Windowing, Options ── */}
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
        </div>
      </div>

      {/* ── Three Orthogonal Panels Grid ── */}
      <div className="mpr-grid">
        {/* Panel 1: Axial (Top or Main) */}
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
          onSliceChange={handleAxialSliceChange}
          onPanelClick={handlePanelClick}
        />

        {/* Panel 2: Coronal */}
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
          onSliceChange={handleCoronalSliceChange}
          onPanelClick={handlePanelClick}
        />

        {/* Panel 3: Sagittal */}
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
          onSliceChange={handleSagittalSliceChange}
          onPanelClick={handlePanelClick}
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
      </div>
    </div>
  );
};

export default MPRViewer;
