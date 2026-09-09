import React, { useRef } from 'react';

/**
 * UploadPanel — CT scan file selection and upload UI.
 *
 * Renders when appState === 'initial'.
 * Calls onUpload(file) which is handled by App.jsx.
 *
 * Accepts only .nii and .nii.gz files.
 * Does NOT perform the actual upload — that is App's responsibility.
 *
 * ⚠️ Medical Safety Disclaimer is always visible.
 */
const UploadPanel = ({ onUpload, isUploading, uploadError }) => {
  const fileInputRef = useRef(null);
  const [selectedFile, setSelectedFile] = React.useState(null);

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
    </div>
  );
};

export default UploadPanel;
