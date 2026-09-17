import React, { useState, useEffect, useRef, useCallback } from 'react';
import Sidebar from './Sidebar';
import Viewer3D from './Viewer3D';
import InfoPanel from './InfoPanel';
import UploadPanel from './UploadPanel';
import StatusPanel from './StatusPanel';
import { ORGAN_DATA } from './data';
import { healthCheck, uploadCase, getCaseStatus, getCaseResults, getCaseLesions, getMeshUrl } from './api';
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
 * Day 14 additions:
 *   - Lesion state: lesions[], lesionVisibility{}, selectedLesion, focusedLesion
 *   - Organ focus-mode opacity (kidney made translucent when lesion focused)
 *   - lesionOpacity slider state
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
  const [appState, setAppState] = useState('initial');
  const [backendStatus, setBackendStatus] = useState(null);
  const [caseId, setCaseId] = useState(null);
  const [results, setResults] = useState(null);
  const [errorMessage, setErrorMessage] = useState(null);
  const [uploadError, setUploadError] = useState(null);
  const [isUploading, setIsUploading] = useState(false);

  // ── Backend health ─────────────────────────────────────────────────────────
  const [backendAvailable, setBackendAvailable] = useState(null);

  // ── Viewer state ───────────────────────────────────────────────────────────
  const [selectedOrgan, setSelectedOrgan] = useState(null);
  const [visibility, setVisibility] = useState(initialVisibility);

  // ── Day 14: Lesion state ───────────────────────────────────────────────────
  const [lesions, setLesions] = useState([]);                // array of lesion objects
  const [lesionVisibility, setLesionVisibility] = useState({}); // lesionId → bool
  const [selectedLesion, setSelectedLesion] = useState(null);
  const [focusedLesion, setFocusedLesion] = useState(null);   // triggers camera transition
  const [lesionOpacity, setLesionOpacity] = useState(1.0);
  const [organOpacities, setOrganOpacities] = useState({});   // overrides for focus mode

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

          // Fetch organ results
          try {
            const resultData = await getCaseResults(id);
            setResults(resultData.organs || {});
          } catch (err) {
            console.error('Results fetch failed:', err);
            setResults({});
          }

          // Fetch lesion measurements (Day 14)
          try {
            const lesionData = await getCaseLesions(id);
            const lesionList = lesionData.lesions ?? [];
            setLesions(lesionList);
            // Initialize all lesions visible
            const initVis = {};
            lesionList.forEach(l => { initVis[l.lesion_id] = true; });
            setLesionVisibility(initVis);
          } catch (err) {
            // Lesion data unavailable — not an error, just no lesions shown
            console.warn('Lesion data not available:', err.message);
            setLesions([]);
          }
        } else if (data.status === 'failed') {
          stopPolling();
          setAppState('failed');
          setErrorMessage(data.error || 'The backend pipeline encountered an error. Please try again.');
        }
      } catch (err) {
        console.error('Polling error:', err);
      }
    };

    poll();
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
    setLesions([]);
    setLesionVisibility({});
    setSelectedLesion(null);
    setFocusedLesion(null);
    setOrganOpacities({});
    setLesionOpacity(1.0);
    setAppState('initial');
  }, [stopPolling]);

  // ── Organ visibility toggle ────────────────────────────────────────────────
  const handleToggleVisibility = useCallback((key) => {
    setVisibility(prev => ({ ...prev, [key]: !prev[key] }));
  }, []);

  // ── Lesion visibility toggle ───────────────────────────────────────────────
  const handleToggleLesion = useCallback((lesionId) => {
    setLesionVisibility(prev => ({ ...prev, [lesionId]: !(prev[lesionId] !== false) }));
  }, []);

  // ── Select organ (clears lesion selection) ─────────────────────────────────
  const handleSelectOrgan = useCallback((key) => {
    setSelectedOrgan(key);
    setSelectedLesion(null);
    setFocusedLesion(null);
    setOrganOpacities({});
  }, []);

  // ── Select lesion (clears organ selection, dims host kidney) ───────────────
  const handleSelectLesion = useCallback((lesion) => {
    setSelectedLesion(lesion);
    setSelectedOrgan(null);

    // Dim the host kidney to reveal the internal lesion
    const host = lesion.lesion_id.includes('right') ? 'kidney_right' : 'kidney_left';
    setOrganOpacities({ [host]: 0.25 });
  }, []);

  // ── Focus camera on lesion ────────────────────────────────────────────────
  const handleFocusLesion = useCallback((lesion) => {
    setSelectedLesion(lesion);
    setSelectedOrgan(null);
    setFocusedLesion(lesion);

    const host = lesion.lesion_id.includes('right') ? 'kidney_right' : 'kidney_left';
    setOrganOpacities({ [host]: 0.20 });
  }, []);

  // ── Camera transition done ────────────────────────────────────────────────
  const handleFocusDone = useCallback(() => {
    setFocusedLesion(null); // clear trigger but keep opacity overrides
  }, []);

  // ── Build mesh URL map (organs + lesions) ─────────────────────────────────
  const meshUrls = React.useMemo(() => {
    if (!caseId || appState !== 'completed') return null;
    const urls = {};
    // Organ meshes
    Object.keys(ORGAN_DATA).forEach(key => {
      urls[key] = getMeshUrl(caseId, key);
    });
    // Lesion meshes
    lesions.forEach(l => {
      urls[l.lesion_id] = getMeshUrl(caseId, l.lesion_id);
    });
    return urls;
  }, [caseId, appState, lesions]);

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

            {/* Lesion opacity slider (only in completed state when lesions present) */}
            {showViewer && lesions.length > 0 && (
              <div className="lesion-opacity-control">
                <label htmlFor="lesion-opacity-slider" className="lesion-opacity-label">
                  Lesion opacity
                </label>
                <input
                  id="lesion-opacity-slider"
                  type="range"
                  min="0"
                  max="1"
                  step="0.05"
                  value={lesionOpacity}
                  onChange={(e) => setLesionOpacity(parseFloat(e.target.value))}
                  className="lesion-opacity-slider"
                  aria-label="Lesion mesh opacity"
                />
              </div>
            )}

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
                onSelectOrgan={handleSelectOrgan}
                visibility={visibility}
                onToggleVisibility={handleToggleVisibility}
                lesions={lesions}
                lesionVisibility={lesionVisibility}
                onToggleLesion={handleToggleLesion}
                selectedLesion={selectedLesion}
                onSelectLesion={handleSelectLesion}
                onFocusLesion={handleFocusLesion}
                onReset={handleReset}
              />
            </aside>

            <main className="app-main">
              <Viewer3D
                visibility={visibility}
                meshUrls={meshUrls}
                lesions={lesions}
                lesionVisibility={lesionVisibility}
                lesionOpacity={lesionOpacity}
                focusedLesion={focusedLesion}
                organOpacities={organOpacities}
                onFocusDone={handleFocusDone}
              />
            </main>
          </div>

          <footer className="app-footer">
            <InfoPanel
              selectedOrgan={selectedOrgan}
              organResults={selectedOrgan && results ? results[selectedOrgan] : null}
              selectedLesion={selectedLesion}
            />
          </footer>
        </>
      )}
    </div>
  );
}

export default App;
