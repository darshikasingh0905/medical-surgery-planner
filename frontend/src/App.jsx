import React, { useState, useEffect, useRef, useCallback } from 'react';
import Sidebar from './Sidebar';
import Viewer3D from './Viewer3D';
import InfoPanel from './InfoPanel';
import UploadPanel from './UploadPanel';
import StatusPanel from './StatusPanel';
import { ORGAN_DATA } from './data';
import { healthCheck, uploadCase, getCaseStatus, getCaseResults, getMeshUrl } from './api';
import './index.css';

/**
 * App — Root component and application state machine.
 *
 * Application states:
 *   'initial'    → Upload screen
 *   'uploading'  → File is being sent to the backend
 *   'processing' → Backend pipeline is running; polling active
 *   'completed'  → Results ready; 3D viewer shown
 *   'failed'     → Pipeline or upload error
 *
 * ⚠️ Medical Safety: This is an AI-assisted preoperative planning prototype.
 *    Outputs require clinical review by a qualified medical professional.
 */

const POLL_INTERVAL_MS = 2000;

const initialVisibility = Object.keys(ORGAN_DATA).reduce((acc, key) => {
  acc[key] = true;
  return acc;
}, {});

function App() {
  // ── Application state machine ──────────────────────────────────────────────
  const [appState, setAppState] = useState('initial'); // initial | uploading | processing | completed | failed
  const [backendStatus, setBackendStatus] = useState(null); // uploaded | processing | completed | failed
  const [caseId, setCaseId] = useState(null);
  const [results, setResults] = useState(null);       // organ measurement data from /results
  const [errorMessage, setErrorMessage] = useState(null);
  const [uploadError, setUploadError] = useState(null);
  const [isUploading, setIsUploading] = useState(false);

  // ── Backend health ─────────────────────────────────────────────────────────
  const [backendAvailable, setBackendAvailable] = useState(null); // null=checking, true, false

  // ── Viewer state ───────────────────────────────────────────────────────────
  const [selectedOrgan, setSelectedOrgan] = useState(null);
  const [visibility, setVisibility] = useState(initialVisibility);

  // ── Polling ref ────────────────────────────────────────────────────────────
  const pollIntervalRef = useRef(null);

  // ── Health check on mount ──────────────────────────────────────────────────
  useEffect(() => {
    let cancelled = false;
    healthCheck()
      .then(() => { if (!cancelled) setBackendAvailable(true); })
      .catch(() => { if (!cancelled) setBackendAvailable(false); });
    return () => { cancelled = true; };
  }, []);

  // ── Stop polling helper ────────────────────────────────────────────────────
  const stopPolling = useCallback(() => {
    if (pollIntervalRef.current) {
      clearInterval(pollIntervalRef.current);
      pollIntervalRef.current = null;
    }
  }, []);

  // ── Cleanup on unmount ─────────────────────────────────────────────────────
  useEffect(() => stopPolling, [stopPolling]);

  // ── Start polling after a caseId is set ───────────────────────────────────
  const startPolling = useCallback((id) => {
    stopPolling();

    const poll = async () => {
      try {
        const data = await getCaseStatus(id);
        setBackendStatus(data.status);

        if (data.status === 'completed') {
          stopPolling();
          setAppState('completed');
          // Fetch results
          try {
            const resultData = await getCaseResults(id);
            setResults(resultData.organs || {});
          } catch (err) {
            // Results fetch failed — viewer still shows meshes, InfoPanel shows "Not available"
            console.error('Results fetch failed:', err);
            setResults({});
          }
        } else if (data.status === 'failed') {
          stopPolling();
          setAppState('failed');
          setErrorMessage(data.error || 'The backend pipeline encountered an error. Please try again.');
        }
        // else 'uploaded' | 'processing' → keep polling
      } catch (err) {
        // Network error during polling — don't crash the app, just log
        console.error('Polling error:', err);
      }
    };

    poll(); // immediate first call
    pollIntervalRef.current = setInterval(poll, POLL_INTERVAL_MS);
  }, [stopPolling]);

  // ── Upload handler ─────────────────────────────────────────────────────────
  const handleUpload = useCallback(async (file) => {
    setUploadError(null);
    setIsUploading(true);
    setAppState('uploading');

    try {
      const data = await uploadCase(file);
      setCaseId(data.case_id);
      setBackendStatus(data.status);
      setAppState('processing');
      startPolling(data.case_id);
    } catch (err) {
      setUploadError(err.message || 'Upload failed. Please check your connection and try again.');
      setAppState('initial');
    } finally {
      setIsUploading(false);
    }
  }, [startPolling]);

  // ── Reset to initial state ─────────────────────────────────────────────────
  const handleReset = useCallback(() => {
    stopPolling();
    setCaseId(null);
    setResults(null);
    setBackendStatus(null);
    setErrorMessage(null);
    setUploadError(null);
    setSelectedOrgan(null);
    setVisibility(initialVisibility);
    setAppState('initial');
  }, [stopPolling]);

  // ── Organ visibility toggle ────────────────────────────────────────────────
  const handleToggleVisibility = useCallback((key) => {
    setVisibility(prev => ({ ...prev, [key]: !prev[key] }));
  }, []);

  // ── Derived mesh URLs (only when completed) ────────────────────────────────
  const meshUrls = React.useMemo(() => {
    if (!caseId || appState !== 'completed') return null;
    return Object.keys(ORGAN_DATA).reduce((acc, key) => {
      acc[key] = getMeshUrl(caseId, key);
      return acc;
    }, {});
  }, [caseId, appState]);

  // ── Render ─────────────────────────────────────────────────────────────────
  const showViewer = appState === 'completed';
  const showStatus = appState === 'uploading' || appState === 'processing' || appState === 'failed';
  const showUpload = appState === 'initial';

  return (
    <div className="app-container">
      {/* ── Header ── */}
      <header className="app-header">
        <div className="app-header-inner">
          <div className="app-header-left">
            <svg className="app-logo-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
              <path strokeLinecap="round" strokeLinejoin="round" d="M21 8.25c0-2.485-2.099-4.5-4.688-4.5-1.935 0-3.597 1.126-4.312 2.733-.715-1.607-2.377-2.733-4.313-2.733C5.1 3.75 3 5.765 3 8.25c0 7.22 9 12 9 12s9-4.78 9-12z" />
            </svg>
            <h1 className="app-header-title">Medical Surgery Planner</h1>
          </div>

          <div className="app-header-right">
            {/* Backend status indicator */}
            {backendAvailable === false && (
              <div className="backend-badge backend-badge--offline" role="alert">
                <span className="backend-dot" />
                Backend offline
              </div>
            )}
            {backendAvailable === true && (
              <div className="backend-badge backend-badge--online">
                <span className="backend-dot" />
                Backend connected
              </div>
            )}

            {/* Reset button — only visible when not on initial screen */}
            {!showUpload && (
              <button
                id="upload-new-scan-button"
                className="btn-new-scan"
                onClick={handleReset}
                title="Upload a new scan"
              >
                ↩ New Scan
              </button>
            )}
          </div>
        </div>
      </header>

      {/* ── Upload Screen ── */}
      {showUpload && (
        <main className="upload-main">
          <UploadPanel
            onUpload={handleUpload}
            isUploading={isUploading}
            uploadError={uploadError}
          />
        </main>
      )}

      {/* ── Status Screen ── */}
      {showStatus && (
        <main className="status-main">
          <StatusPanel
            appState={appState}
            backendStatus={backendStatus}
            caseId={caseId}
            errorMessage={errorMessage}
            onReset={handleReset}
          />
        </main>
      )}

      {/* ── Main Viewer (completed state) ── */}
      {showViewer && (
        <>
          <div className="app-content">
            <aside className="app-sidebar">
              <Sidebar
                selectedOrgan={selectedOrgan}
                onSelectOrgan={setSelectedOrgan}
                visibility={visibility}
                onToggleVisibility={handleToggleVisibility}
                onReset={handleReset}
              />
            </aside>

            <main className="app-main">
              <Viewer3D
                visibility={visibility}
                meshUrls={meshUrls}
              />
            </main>
          </div>

          <footer className="app-footer">
            <InfoPanel
              selectedOrgan={selectedOrgan}
              organResults={selectedOrgan && results ? results[selectedOrgan] : null}
            />
          </footer>
        </>
      )}
    </div>
  );
}

export default App;
