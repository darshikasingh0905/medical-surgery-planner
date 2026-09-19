import React, { useState, useEffect, useRef, useCallback } from 'react';
import Sidebar from './Sidebar';
import Viewer3D from './Viewer3D';
import InfoPanel from './InfoPanel';
import UploadPanel from './UploadPanel';
import StatusPanel from './StatusPanel';
import { ORGAN_DATA } from './data';
import {
  healthCheck,
  uploadCase,
  getCaseStatus,
  getCaseResults,
  getCaseLesions,
  getCaseStructures,
  getLesionRelationships,
  getMeshUrl,
} from './api';
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
 * Day 15 additions:
 *   - Preoperative Planning View state toggle
 *   - Anatomical structure registry integration (available vs unavailable)
 *   - Computational spatial relationships between lesion and anatomical structures
 *   - Structure highlighting, visibility toggles, and camera focus
 *   - Organ transparency & lesion opacity controls
 *
 * ⚠️ Medical Safety Governance:
 * This application is a computational visualization prototype for research/educational use.
 * Outputs require clinical review by a qualified medical professional.
 * Computational distances do NOT constitute clinical margins or surgical clearance.
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

  // ── View mode: Standard Normal View vs Preoperative Planning View ──────────
  const [isPlanningView, setIsPlanningView] = useState(false);

  // ── Viewer state ───────────────────────────────────────────────────────────
  const [selectedOrgan, setSelectedOrgan] = useState(null);
  const [visibility, setVisibility] = useState(initialVisibility);

  // ── Anatomical Structures state (Day 15) ────────────────────────────────────
  const [structures, setStructures] = useState([]);
  const [structureVisibility, setStructureVisibility] = useState({});
  const [selectedStructure, setSelectedStructure] = useState(null);

  // ── Lesions & Spatial Relationships state ──────────────────────────────────
  const [lesions, setLesions] = useState([]);
  const [lesionVisibility, setLesionVisibility] = useState({});
  const [selectedLesion, setSelectedLesion] = useState(null);
  const [relationships, setRelationships] = useState([]);

  // ── Camera & Opacity controls ──────────────────────────────────────────────
  const [focusedTarget, setFocusedTarget] = useState(null);
  const [organOpacity, setOrganOpacity] = useState(0.85);
  const [lesionOpacity, setLesionOpacity] = useState(1.0);
  const [organOpacities, setOrganOpacities] = useState({});

  // ── Polling ref ────────────────────────────────────────────────────────────
  const pollIntervalRef = useRef(null);

  // ── Health check on mount ──────────────────────────────────────────────────
  useEffect(() => {
    let cancelled = false;
    healthCheck()
      .then(() => {
        if (!cancelled) setBackendAvailable(true);
      })
      .catch(() => {
        if (!cancelled) setBackendAvailable(false);
      });
    return () => {
      cancelled = true;
    };
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
  const startPolling = useCallback(
    (id) => {
      stopPolling();

      const poll = async () => {
        try {
          const data = await getCaseStatus(id);
          setBackendStatus(data.status);

          if (data.status === 'completed') {
            stopPolling();
            setAppState('completed');

            // 1. Fetch organ results
            try {
              const resultData = await getCaseResults(id);
              setResults(resultData.organs || {});
            } catch (err) {
              console.error('Results fetch failed:', err);
              setResults({});
            }

            // 2. Fetch anatomical structures audit (Day 15)
            try {
              const structData = await getCaseStructures(id);
              const structList = structData.structures ?? [];
              setStructures(structList);
              const initStructVis = {};
              structList.forEach((s) => {
                initStructVis[s.structure_id] = s.available;
              });
              setStructureVisibility(initStructVis);
            } catch (err) {
              console.warn('Structure registry not available:', err.message);
              setStructures([]);
            }

            // 3. Fetch lesion measurements
            let detectedLesions = [];
            try {
              const lesionData = await getCaseLesions(id);
              detectedLesions = lesionData.lesions ?? [];
              setLesions(detectedLesions);

              const initVis = {};
              detectedLesions.forEach((l) => {
                initVis[l.lesion_id] = true;
              });
              setLesionVisibility(initVis);
            } catch (err) {
              console.warn('Lesion data not available:', err.message);
              setLesions([]);
            }

            // 4. Pre-fetch computational spatial relationships for the primary lesion
            if (detectedLesions.length > 0) {
              const primary = detectedLesions[0];
              try {
                const relData = await getLesionRelationships(id, primary.lesion_id);
                setRelationships(relData.relationships ?? []);
              } catch (err) {
                console.warn('Spatial relationships not available:', err.message);
                setRelationships([]);
              }
            }
          } else if (data.status === 'failed') {
            stopPolling();
            setAppState('failed');
            setErrorMessage(
              data.error || 'The backend pipeline encountered an error. Please try again.'
            );
          }
        } catch (err) {
          console.error('Polling error:', err);
        }
      };

      poll();
      pollIntervalRef.current = setInterval(poll, POLL_INTERVAL_MS);
    },
    [stopPolling]
  );

  // ── Upload handler ─────────────────────────────────────────────────────────
  const handleUpload = useCallback(
    async (file) => {
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
        setUploadError(
          err.message || 'Upload failed. Please check your connection and try again.'
        );
        setAppState('initial');
      } finally {
        setIsUploading(false);
      }
    },
    [startPolling]
  );

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
    setStructures([]);
    setStructureVisibility({});
    setSelectedStructure(null);
    setLesions([]);
    setLesionVisibility({});
    setSelectedLesion(null);
    setRelationships([]);
    setFocusedTarget(null);
    setOrganOpacities({});
    setOrganOpacity(0.85);
    setLesionOpacity(1.0);
    setIsPlanningView(false);
    setAppState('initial');
  }, [stopPolling]);

  // ── Organ visibility toggle (Normal View) ──────────────────────────────────
  const handleToggleVisibility = useCallback((key) => {
    setVisibility((prev) => ({ ...prev, [key]: !prev[key] }));
  }, []);

  // ── Structure visibility toggle (Planning View) ────────────────────────────
  const handleToggleStructureVisibility = useCallback((structId) => {
    setStructureVisibility((prev) => ({
      ...prev,
      [structId]: !(prev[structId] !== false),
    }));
    setVisibility((prev) => ({
      ...prev,
      [structId]: !(prev[structId] !== false),
    }));
  }, []);

  // ── Lesion visibility toggle ───────────────────────────────────────────────
  const handleToggleLesion = useCallback((lesionId) => {
    setLesionVisibility((prev) => ({
      ...prev,
      [lesionId]: !(prev[lesionId] !== false),
    }));
  }, []);

  // ── Select organ (clears lesion/structure selection) ───────────────────────
  const handleSelectOrgan = useCallback((key) => {
    setSelectedOrgan(key);
    setSelectedStructure(key);
    setSelectedLesion(null);
    setFocusedTarget(null);
    setOrganOpacities({});
  }, []);

  // ── Select registered anatomical structure ─────────────────────────────────
  const handleSelectStructure = useCallback((structId) => {
    setSelectedStructure(structId);
    setSelectedOrgan(structId);
    setSelectedLesion(null);
    setFocusedTarget(null);
  }, []);

  // ── Focus camera on anatomical structure ───────────────────────────────────
  const handleFocusStructure = useCallback((structId) => {
    setSelectedStructure(structId);
    setSelectedOrgan(structId);
    setSelectedLesion(null);
    setFocusedTarget(structId);

    // Dim other anatomy to visually emphasize focused structure
    const dimOverrides = {};
    structures.forEach((s) => {
      if (s.structure_id !== structId) {
        dimOverrides[s.structure_id] = 0.35;
      }
    });
    setOrganOpacities(dimOverrides);
  }, [structures]);

  // ── Select lesion (clears organ selection, dims host kidney) ───────────────
  const handleSelectLesion = useCallback(
    async (lesion) => {
      setSelectedLesion(lesion);
      setSelectedOrgan(null);
      setSelectedStructure(lesion.lesion_id);

      const host = lesion.lesion_id.includes('right') ? 'kidney_right' : 'kidney_left';
      setOrganOpacities({ [host]: 0.25 });

      if (caseId) {
        try {
          const relData = await getLesionRelationships(caseId, lesion.lesion_id);
          setRelationships(relData.relationships ?? []);
        } catch (err) {
          console.warn('Failed to fetch relationships for lesion:', err.message);
        }
      }
    },
    [caseId]
  );

  // ── Focus camera on lesion ────────────────────────────────────────────────
  const handleFocusLesion = useCallback((lesion) => {
    setSelectedLesion(lesion);
    setSelectedOrgan(null);
    setSelectedStructure(lesion.lesion_id);
    setFocusedTarget(lesion);

    const host = lesion.lesion_id.includes('right') ? 'kidney_right' : 'kidney_left';
    setOrganOpacities({ [host]: 0.2 });
  }, []);

  // ── Reset camera view & opacities ──────────────────────────────────────────
  const handleResetCamera = useCallback(() => {
    setFocusedTarget(null);
    setOrganOpacities({});
  }, []);

  // ── Camera transition done ────────────────────────────────────────────────
  const handleFocusDone = useCallback(() => {
    setFocusedTarget(null); // Clear trigger, preserve opacities
  }, []);

  // ── Build mesh URL map (organs + registered structures + lesions) ──────────
  const meshUrls = React.useMemo(() => {
    if (!caseId || appState !== 'completed') return null;
    const urls = {};
    // Base organs
    Object.keys(ORGAN_DATA).forEach((key) => {
      urls[key] = getMeshUrl(caseId, key);
    });
    // Registered case structures with meshes available
    structures.forEach((s) => {
      if (s.mesh_available && s.available) {
        urls[s.structure_id] = getMeshUrl(caseId, s.structure_id);
      }
    });
    // Lesions
    lesions.forEach((l) => {
      urls[l.lesion_id] = getMeshUrl(caseId, l.lesion_id);
    });
    return urls;
  }, [caseId, appState, lesions, structures]);

  // Combined visibility state
  const combinedVisibility = React.useMemo(() => {
    return { ...visibility, ...structureVisibility };
  }, [visibility, structureVisibility]);

  // Combined organ opacities
  const effectiveOrganOpacities = React.useMemo(() => {
    const base = {};
    Object.keys(combinedVisibility).forEach((key) => {
      base[key] = organOpacity;
    });
    return { ...base, ...organOpacities };
  }, [combinedVisibility, organOpacity, organOpacities]);

  // ── Render ─────────────────────────────────────────────────────────────────
  const showViewer = appState === 'completed';
  const showStatus =
    appState === 'uploading' || appState === 'processing' || appState === 'failed';
  const showUpload = appState === 'initial';

  return (
    <div className="app-container">
      {/* ── Header ── */}
      <header className="app-header">
        <div className="app-header-inner">
          <div className="app-header-left">
            <svg
              className="app-logo-icon"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="1.5"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M21 8.25c0-2.485-2.099-4.5-4.688-4.5-1.935 0-3.597 1.126-4.312 2.733-.715-1.607-2.377-2.733-4.313-2.733C5.1 3.75 3 5.765 3 8.25c0 7.22 9 12 9 12s9-4.78 9-12z"
              />
            </svg>
            <h1 className="app-header-title">Medical Surgery Planner</h1>
            {isPlanningView && (
              <span className="header-planning-badge">Planning View</span>
            )}
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
                isPlanningView={isPlanningView}
                onTogglePlanningView={setIsPlanningView}
                selectedOrgan={selectedOrgan}
                onSelectOrgan={handleSelectOrgan}
                visibility={visibility}
                onToggleVisibility={handleToggleVisibility}
                structures={structures}
                structureVisibility={structureVisibility}
                onToggleStructureVisibility={handleToggleStructureVisibility}
                selectedStructure={selectedStructure}
                onSelectStructure={handleSelectStructure}
                onFocusStructure={handleFocusStructure}
                lesions={lesions}
                lesionVisibility={lesionVisibility}
                onToggleLesion={handleToggleLesion}
                selectedLesion={selectedLesion}
                onSelectLesion={handleSelectLesion}
                onFocusLesion={handleFocusLesion}
                organOpacity={organOpacity}
                onChangeOrganOpacity={setOrganOpacity}
                lesionOpacity={lesionOpacity}
                onChangeLesionOpacity={setLesionOpacity}
                onReset={handleReset}
              />
            </aside>

            <main className="app-main">
              <Viewer3D
                visibility={combinedVisibility}
                meshUrls={meshUrls}
                lesions={lesions}
                lesionVisibility={lesionVisibility}
                lesionOpacity={lesionOpacity}
                organOpacities={effectiveOrganOpacities}
                selectedStructure={selectedStructure}
                focusedTarget={focusedTarget}
                isPlanningView={isPlanningView}
                onFocusDone={handleFocusDone}
                onResetCamera={handleResetCamera}
              />
            </main>
          </div>

          <footer className="app-footer">
            <InfoPanel
              selectedOrgan={selectedOrgan}
              organResults={selectedOrgan && results ? results[selectedOrgan] : null}
              selectedLesion={selectedLesion}
              selectedStructure={selectedStructure}
              structures={structures}
              lesions={lesions}
              relationships={relationships}
              isPlanningView={isPlanningView}
            />
          </footer>
        </>
      )}
    </div>
  );
}

export default App;
