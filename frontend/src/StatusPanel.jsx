import React from 'react';

/**
 * StatusPanel — Displays the current processing state after a scan is uploaded.
 *
 * Shown during: uploading | processing | failed
 * Hidden when: initial (UploadPanel shown) | completed (Viewer3D shown)
 *
 * Does NOT display fake progress percentages.
 * Status messages are derived from the actual backend `status` field.
 */

const STATUS_CONFIG = {
  uploading: {
    phase: 'Uploading',
    message: 'Uploading scan to server…',
    subMessage: 'Please wait while your file is transferred.',
    showSpinner: true,
    isError: false,
  },
  uploaded: {
    phase: 'Queued',
    message: 'Scan received. Queued for processing…',
    subMessage: 'The pipeline will begin shortly.',
    showSpinner: true,
    isError: false,
  },
  processing: {
    phase: 'Processing',
    message: 'Processing scan…',
    subMessage: 'Running AI segmentation and generating 3D anatomical models. This may take several minutes.',
    showSpinner: true,
    isError: false,
  },
  failed: {
    phase: 'Failed',
    message: 'Processing failed.',
    subMessage: null, // Error detail shown separately
    showSpinner: false,
    isError: true,
  },
};

const PIPELINE_STEPS = [
  { id: 'upload', label: 'Scan uploaded', statuses: ['uploaded', 'processing', 'completed'] },
  { id: 'segmentation', label: 'AI organ segmentation', statuses: ['processing', 'completed'] },
  { id: 'meshes', label: 'Generating 3D meshes', statuses: ['processing', 'completed'] },
  { id: 'measurements', label: 'Calculating measurements', statuses: ['processing', 'completed'] },
];

const StatusPanel = ({ appState, backendStatus, caseId, errorMessage, onReset }) => {
  // Use backendStatus for processing sub-states, fall back to appState for uploading
  const statusKey = appState === 'uploading' ? 'uploading' : (backendStatus || appState);
  const config = STATUS_CONFIG[statusKey] || STATUS_CONFIG.processing;

  return (
    <div className="status-screen">
      <div className="status-card">
        {/* Animated Icon */}
        <div className={`status-icon-wrapper ${config.isError ? 'status-icon-wrapper--error' : ''}`}>
          {config.isError ? (
            <svg className="status-icon-svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
              <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z" />
            </svg>
          ) : (
            <div className="status-spinner-ring" aria-label="Processing" role="status">
              <div className="status-spinner-inner" />
            </div>
          )}
        </div>

        {/* Phase Badge */}
        <span className={`status-phase-badge ${config.isError ? 'status-phase-badge--error' : ''}`}>
          {config.phase}
        </span>

        {/* Main Message */}
        <h2 className="status-message">{config.message}</h2>

        {/* Sub-message */}
        {config.subMessage && (
          <p className="status-sub-message">{config.subMessage}</p>
        )}

        {/* Error detail */}
        {config.isError && errorMessage && (
          <div className="status-error-detail" role="alert">
            {errorMessage}
          </div>
        )}

        {/* Case ID badge (shown when we have one) */}
        {caseId && (
          <div className="status-case-id">
            <span className="status-case-id-label">Case ID</span>
            <code className="status-case-id-value">{caseId}</code>
          </div>
        )}

        {/* Pipeline Steps — visual only, driven by actual backend status */}
        {!config.isError && (
          <div className="pipeline-steps" aria-label="Pipeline progress">
            {PIPELINE_STEPS.map((step) => {
              const isDone = step.statuses.includes(backendStatus) || step.id === 'upload';
              const isActive = statusKey === 'processing' && step.id === 'segmentation';
              return (
                <div
                  key={step.id}
                  className={`pipeline-step ${isDone ? 'pipeline-step--done' : ''} ${isActive ? 'pipeline-step--active' : ''}`}
                >
                  <span className="pipeline-step-dot" aria-hidden="true" />
                  <span className="pipeline-step-label">{step.label}</span>
                </div>
              );
            })}
          </div>
        )}

        {/* Reset Button (only on failure) */}
        {config.isError && (
          <button
            id="reset-after-failure-button"
            className="btn-reset"
            onClick={onReset}
          >
            Try Again
          </button>
        )}

        {/* Disclaimer */}
        <p className="status-disclaimer">
          AI-Assisted Preoperative Planning Prototype — outputs require clinical review.
        </p>
      </div>
    </div>
  );
};

export default StatusPanel;
