import React, { useRef } from 'react';
import { getCaseList } from './api';

/**
 * A short, human-readable label for a case in the delete-confirmation
 * dialog — never invents or infers clinical metadata, just echoes the
 * filename/case_id already shown in the list.
 */
function describeCaseForConfirm(caseSummary) {
  return caseSummary.filename || caseSummary.case_id;
}

/**
 * Formats an ISO 8601 timestamp for display; falls back to the raw string
 * if parsing fails rather than showing nothing.
 */
function formatLastModified(iso) {
  if (!iso) return 'Unknown date';
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleString();
}

/**
 * UploadPanel — CT scan file selection and upload UI.
 *
 * Renders when appState === 'initial'.
 * Calls onUpload(file) which is handled by App.jsx.
 *
 * Accepts only .nii and .nii.gz files.
 * Does NOT perform the actual upload — that is App's responsibility.
 *
 * Day 27: also surfaces a read-only "Resume a Previous Case" list, fetched
 * from the existing case-history endpoint. Selecting a case calls
 * onResumeCase(caseId), which App.jsx wires to the existing startPolling()
 * path already used by a successful upload — no second case-loading
 * mechanism is introduced here.
 *
 * Day 28: each case in that list can also be permanently deleted via
 * onDeleteCase(caseId), which App.jsx wires to the existing deleteCase()
 * API helper. Deletion requires an explicit user confirmation dialog before
 * the API call is made; the local list is optimistically updated on success.
 *
 * ⚠️ Medical Safety Disclaimer is always visible.
 */
const UploadPanel = ({ onUpload, isUploading, uploadError, onResumeCase, onDeleteCase }) => {
  const fileInputRef = useRef(null);
  const [selectedFile, setSelectedFile] = React.useState(null);

  // ── Case History (Day 27) ────────────────────────────────────────────────
  const [caseList, setCaseList] = React.useState([]);
  const [loadingCases, setLoadingCases] = React.useState(true);
  const [casesError, setCasesError] = React.useState(null);

  // ── Case Deletion (Day 28) ───────────────────────────────────────────────
  const [deletingCaseId, setDeletingCaseId] = React.useState(null);
  const [deleteError, setDeleteError] = React.useState(null);

  React.useEffect(() => {
    let cancelled = false;

    async function loadCases() {
      setLoadingCases(true);
      setCasesError(null);
      try {
        const data = await getCaseList();
        if (!cancelled) setCaseList(data.cases || []);
      } catch (err) {
        if (!cancelled) setCasesError(err.message || 'Failed to load case history.');
      } finally {
        if (!cancelled) setLoadingCases(false);
      }
    }

    loadCases();
    return () => {
      cancelled = true;
    };
  }, []);

  const handleDeleteCaseClick = async (caseSummary) => {
    if (!onDeleteCase) return;
    const confirmed = window.confirm(
      `Permanently delete this case (${describeCaseForConfirm(caseSummary)})? ` +
        'This removes all of its scan data, segmentation, and planning data. This cannot be undone.'
    );
    if (!confirmed) return;

    setDeleteError(null);
    setDeletingCaseId(caseSummary.case_id);
    try {
      await onDeleteCase(caseSummary.case_id);
      setCaseList((prev) => prev.filter((c) => c.case_id !== caseSummary.case_id));
    } catch (err) {
      setDeleteError(err.message || 'Failed to delete case.');
    } finally {
      setDeletingCaseId(null);
    }
  };

  const handleFileChange = (e) => {
    const file = e.target.files[0];
    if (!file) return;

    // Client-side extension check
    const name = file.name;
    if (!name.endsWith('.nii') && !name.endsWith('.nii.gz')) {
      setSelectedFile(null);
      return;
    }
    setSelectedFile(file);
  };

  const handleUpload = () => {
    if (!selectedFile || isUploading) return;
    onUpload(selectedFile);
  };

  const handleBrowseClick = () => {
    fileInputRef.current?.click();
  };

  const handleDrop = (e) => {
    e.preventDefault();
    const file = e.dataTransfer.files[0];
    if (!file) return;
    const name = file.name;
    if (!name.endsWith('.nii') && !name.endsWith('.nii.gz')) return;
    setSelectedFile(file);
  };

  const handleDragOver = (e) => {
    e.preventDefault();
  };

  return (
    <div className="upload-screen">
      <div className="upload-card">
        {/* Header */}
        <div className="upload-card-header">
          <div className="upload-icon-wrapper">
            <svg className="upload-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
              <path strokeLinecap="round" strokeLinejoin="round" d="M9 13h6m-3-3v6m5.25-10.5H6.75A2.25 2.25 0 004.5 7.5v9a2.25 2.25 0 002.25 2.25h10.5A2.25 2.25 0 0019.5 16.5v-9a2.25 2.25 0 00-2.25-2.25z" />
            </svg>
          </div>
          <h2 className="upload-title">Upload CT Scan</h2>
          <p className="upload-subtitle">
            Select a NIfTI scan file to begin AI-assisted anatomical analysis.
          </p>
        </div>

        {/* Drop Zone */}
        <div
          className={`drop-zone ${selectedFile ? 'drop-zone--has-file' : ''}`}
          onDrop={handleDrop}
          onDragOver={handleDragOver}
          onClick={handleBrowseClick}
          role="button"
          tabIndex={0}
          aria-label="Click or drag to select a CT scan file"
          onKeyDown={(e) => e.key === 'Enter' && handleBrowseClick()}
        >
          <input
            ref={fileInputRef}
            id="ct-file-input"
            type="file"
            accept=".nii,.nii.gz"
            onChange={handleFileChange}
            className="file-input-hidden"
            aria-label="CT scan file input"
          />

          {selectedFile ? (
            <div className="file-selected-info">
              <svg className="file-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m0 12.75h7.5m-7.5 3H12M10.5 2.25H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z" />
              </svg>
              <span className="file-name">{selectedFile.name}</span>
              <span className="file-size">({(selectedFile.size / (1024 * 1024)).toFixed(1)} MB)</span>
              <span className="file-change-hint">Click to change file</span>
            </div>
          ) : (
            <div className="drop-zone-prompt">
              <svg className="drop-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                <path strokeLinecap="round" strokeLinejoin="round" d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5m-13.5-9L12 3m0 0l4.5 4.5M12 3v13.5" />
              </svg>
              <p className="drop-text">Drag & drop or <span className="drop-link">browse</span></p>
              <p className="drop-formats">Accepted formats: <code>.nii</code>, <code>.nii.gz</code></p>
            </div>
          )}
        </div>

        {/* Error Message */}
        {uploadError && (
          <div className="upload-error" role="alert" id="upload-error-message">
            <svg viewBox="0 0 20 20" fill="currentColor" className="error-icon">
              <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.28 7.22a.75.75 0 00-1.06 1.06L8.94 10l-1.72 1.72a.75.75 0 101.06 1.06L10 11.06l1.72 1.72a.75.75 0 101.06-1.06L11.06 10l1.72-1.72a.75.75 0 00-1.06-1.06L10 8.94 8.28 7.22z" clipRule="evenodd" />
            </svg>
            {uploadError}
          </div>
        )}

        {/* Upload Button */}
        <button
          id="upload-button"
          className={`btn-upload ${!selectedFile || isUploading ? 'btn-upload--disabled' : ''}`}
          onClick={handleUpload}
          disabled={!selectedFile || isUploading}
          aria-busy={isUploading}
        >
          {isUploading ? (
            <>
              <span className="btn-spinner" aria-hidden="true" />
              Uploading…
            </>
          ) : (
            <>
              <svg className="btn-icon" viewBox="0 0 20 20" fill="currentColor">
                <path fillRule="evenodd" d="M10 1a.75.75 0 01.75.75v6.5h6.5a.75.75 0 010 1.5h-6.5v6.5a.75.75 0 01-1.5 0v-6.5H2.75a.75.75 0 010-1.5h6.5v-6.5A.75.75 0 0110 1z" clipRule="evenodd" />
              </svg>
              Begin Analysis
            </>
          )}
        </button>

        {/* Medical Safety Disclaimer */}
        <div className="disclaimer" role="note">
          <svg className="disclaimer-icon" viewBox="0 0 20 20" fill="currentColor">
            <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a.75.75 0 000 1.5h.253a.25.25 0 01.244.304l-.459 2.066A1.75 1.75 0 0010.747 15H11a.75.75 0 000-1.5h-.253a.25.25 0 01-.244-.304l.459-2.066A1.75 1.75 0 009.253 9H9z" clipRule="evenodd" />
          </svg>
          <span>
            <strong>AI-Assisted Preoperative Planning Prototype.</strong>{' '}
            Outputs are decision-support information requiring clinical review by a qualified medical professional.
            This system does not provide autonomous diagnosis or autonomous surgical planning.
          </span>
        </div>
      </div>

      {/* Case History / Resume (Day 27) */}
      <div className="case-history-card" id="case-history-card">
        <div className="case-history-header">
          <h3 className="case-history-title">📂 Resume a Previous Case</h3>
          {!loadingCases && !casesError && (
            <span className="case-history-count">{caseList.length}</span>
          )}
        </div>

        {loadingCases && (
          <div className="case-history-state" id="case-history-loading">
            <span className="btn-spinner" aria-hidden="true" />
            Loading case history…
          </div>
        )}

        {!loadingCases && casesError && (
          <div className="case-history-state case-history-state--error" role="alert" id="case-history-error">
            Could not load case history: {casesError}
          </div>
        )}

        {!loadingCases && !casesError && caseList.length === 0 && (
          <div className="case-history-state" id="case-history-empty">
            No previous cases found on this server.
          </div>
        )}

        {deleteError && (
          <div className="case-history-state case-history-state--error" role="alert" id="case-history-delete-error">
            Could not delete case: {deleteError}
          </div>
        )}

        {!loadingCases && !casesError && caseList.length > 0 && (
          <ul className="case-history-list" aria-label="Previous cases">
            {caseList.map((c) => (
              <li key={c.case_id} className="case-history-item" id={`case-history-item-${c.case_id}`}>
                <div className="case-history-item-info">
                  <span className="case-history-filename" title={c.filename || 'Unknown filename'}>
                    {c.filename || 'Unknown filename'}
                  </span>
                  <span className="case-history-meta">
                    <span className={`case-status-badge case-status-badge--${c.status}`}>
                      {c.status}
                    </span>
                    <span className="case-history-date">{formatLastModified(c.last_modified)}</span>
                  </span>
                </div>
                <div className="case-history-actions">
                  <button
                    type="button"
                    className="btn-resume-case"
                    onClick={() => onResumeCase && onResumeCase(c.case_id)}
                    disabled={!onResumeCase || deletingCaseId === c.case_id}
                    id={`btn-resume-${c.case_id}`}
                    title={`Resume case ${c.case_id}`}
                  >
                    Resume
                  </button>
                  <button
                    type="button"
                    className="btn-delete-case"
                    onClick={() => handleDeleteCaseClick(c)}
                    disabled={!onDeleteCase || deletingCaseId === c.case_id}
                    id={`btn-delete-${c.case_id}`}
                    title={`Delete case ${c.case_id}`}
                    aria-label={`Delete case ${c.filename || c.case_id}`}
                  >
                    {deletingCaseId === c.case_id ? '…' : '🗑️'}
                  </button>
                </div>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
};

export default UploadPanel;
