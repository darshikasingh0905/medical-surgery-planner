/**
 * api.js — Centralized API client for the Medical Surgery Planner frontend.
 *
 * All communication with the FastAPI backend is routed through this module.
 * In development the Vite proxy (`/api → http://127.0.0.1:8000`) handles CORS.
 * In production the same relative paths are used (same-origin or configured reverse proxy).
 *
 * ⚠️ Medical Safety: This system is an AI-assisted preoperative planning prototype.
 *    All outputs are decision-support information requiring clinical review.
 */

const BASE_URL = '/api';

/**
 * Generic fetch wrapper. Throws a plain Error with a user-facing message on failure.
 * Never exposes Python stack traces.
 */
async function apiFetch(path, options = {}) {
  let response;
  try {
    response = await fetch(`${BASE_URL}${path}`, options);
  } catch (_networkError) {
    throw new Error(
      'Cannot reach the backend server. Please ensure the FastAPI server is running on port 8000.'
    );
  }

  if (!response.ok) {
    let detail = `Server error (${response.status})`;
    try {
      const body = await response.json();
      if (body.detail) {
        detail = body.detail;
      }
    } catch {
      // ignore JSON parse failure — use the default message
    }
    throw new Error(detail);
  }

  return response.json();
}

/**
 * Check that the backend API is reachable.
 * Returns { status: 'ok' } on success or throws.
 */
export async function healthCheck() {
  return apiFetch('/health');
}

/**
 * Upload a CT scan file (.nii or .nii.gz).
 * Uses multipart/form-data as required by the backend.
 *
 * @param {File} file - The NIfTI file selected by the user.
 * @returns {Promise<{ case_id: string, filename: string, status: string }>}
 */
export async function uploadCase(file) {
  const formData = new FormData();
  formData.append('file', file);

  return apiFetch('/cases/upload', {
    method: 'POST',
    body: formData,
    // Do NOT set Content-Type manually — the browser sets the multipart boundary automatically.
  });
}

/**
 * Poll the status of a case.
 * Possible status values: 'uploaded' | 'processing' | 'completed' | 'failed'
 *
 * @param {string} caseId - The UUID returned by uploadCase.
 * @returns {Promise<{ case_id: string, filename: string, status: string, error?: string }>}
 */
export async function getCaseStatus(caseId) {
  return apiFetch(`/cases/${caseId}`);
}

/**
 * Retrieve structured measurement results for a completed case.
 * Only valid when status === 'completed'.
 *
 * @param {string} caseId - The UUID of the completed case.
 * @returns {Promise<{ case_id: string, status: string, organs: object }>}
 */
export async function getCaseResults(caseId) {
  return apiFetch(`/cases/${caseId}/results`);
}

/**
 * Build the URL for a generated 3D OBJ mesh.
 * Returns a relative URL string — do NOT fetch this directly; pass it to useLoader / OBJLoader.
 *
 * @param {string} caseId - The UUID of the case.
 * @param {string} organ - One of: liver | heart | aorta | kidney_left
 * @returns {string} Relative URL, e.g. /api/cases/<id>/meshes/liver
 */
export function getMeshUrl(caseId, organ) {
  return `${BASE_URL}/cases/${caseId}/meshes/${organ}`;
}
