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
 * Retrieve structured lesion metrics and spatial measurements for a completed case.
 * Only valid when status === 'completed'.
 *
 * @param {string} caseId - The UUID of the case.
 * @returns {Promise<{ case_id: string, total_lesions: number, lesions: Array, disclaimer: string }>}
 */
export async function getCaseLesions(caseId) {
  return apiFetch(`/cases/${caseId}/lesions`);
}

/**
 * Retrieve anatomical structure audit for a case.
 *
 * @param {string} caseId - The UUID of the case.
 * @returns {Promise<{ case_id: string, structures: Array }>}
 */
export async function getCaseStructures(caseId) {
  return apiFetch(`/cases/${caseId}/structures`);
}

/**
 * Retrieve computational spatial relationships between a lesion and anatomical structures.
 *
 * @param {string} caseId - The UUID of the case.
 * @param {string} lesionId - The ID of the lesion (e.g. 'cyst_left').
 * @returns {Promise<{ case_id: string, lesion_id: string, relationships: Array, summary: object, safety_disclaimer: string }>}
 */
export async function getLesionRelationships(caseId, lesionId) {
  return apiFetch(`/cases/${caseId}/lesions/${lesionId}/relationships`);
}

/**
 * Build the URL for a generated 3D OBJ mesh.
 * Returns a relative URL string — do NOT fetch this directly; pass it to useLoader / OBJLoader.
 *
 * @param {string} caseId - The UUID of the case.
 * @param {string} organ - Structure or lesion identifier
 * @returns {string} Relative URL, e.g. /api/cases/<id>/meshes/liver
 */
export function getMeshUrl(caseId, organ) {
  return `${BASE_URL}/cases/${caseId}/meshes/${organ}`;
}

/**
 * Retrieve volume metadata and plane dimensions for Multi-Planar Reconstruction (MPR).
 *
 * @param {string} caseId - The UUID of the case.
 * @returns {Promise<{ case_id: string, shape: Array, voxel_spacing_mm: Array, planes: object, presets: object }>}
 */
export async function getCaseMPRMetadata(caseId) {
  return apiFetch(`/cases/${caseId}/mpr`);
}

/**
 * Build the URL for an orthogonal 2D CT slice PNG.
 *
 * @param {string} caseId - The UUID of the case.
 * @param {string} plane - 'axial' | 'coronal' | 'sagittal'
 * @param {number} index - Slice index
 * @param {number} ww - Window Width
 * @param {number} wl - Window Level
 * @param {boolean} overlayLesion - Whether to blend genuine lesion mask overlay
 * @returns {string} Relative URL for image tag
 */
export function getMPRSliceUrl(caseId, plane, index, ww = 400, wl = 40, overlayLesion = true) {
  const params = new URLSearchParams({
    ww: String(ww),
    wl: String(wl),
    overlay_lesion: String(overlayLesion),
  });
  return `${BASE_URL}/cases/${caseId}/mpr/slice/${plane}/${index}?${params.toString()}`;
}

/**
 * Retrieve all planning targets for a case (model findings + user annotations).
 *
 * @param {string} caseId - The UUID of the case.
 * @returns {Promise<{ case_id: string, total_targets: number, targets: Array }>}
 */
export async function getPlanningTargets(caseId) {
  return apiFetch(`/cases/${caseId}/planning/targets`);
}

/**
 * Retrieve user-created planning annotations for a case.
 *
 * @param {string} caseId - The UUID of the case.
 * @returns {Promise<{ case_id: string, total_annotations: number, annotations: Array }>}
 */
export async function getPlanningAnnotations(caseId) {
  return apiFetch(`/cases/${caseId}/planning/annotations`);
}

/**
 * Create a new user-defined surgical planning annotation.
 *
 * @param {string} caseId - The UUID of the case.
 * @param {object} payload - { label, voxel_coordinate, notes, ... }
 * @returns {Promise<object>} Created PlanningTarget
 */
export async function createPlanningAnnotation(caseId, payload) {
  return apiFetch(`/cases/${caseId}/planning/annotations`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
}

/**
 * Update an existing user planning annotation.
 *
 * @param {string} caseId - The UUID of the case.
 * @param {string} annotationId - Target ID
 * @param {object} payload - Updated fields
 * @returns {Promise<object>} Updated PlanningTarget
 */
export async function updatePlanningAnnotation(caseId, annotationId, payload) {
  return apiFetch(`/cases/${caseId}/planning/annotations/${annotationId}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
}

/**
 * Delete a user planning annotation.
 *
 * @param {string} caseId - The UUID of the case.
 * @param {string} annotationId - Target ID to delete
 * @returns {Promise<{ status: string, annotation_id: string }>}
 */
export async function deletePlanningAnnotation(caseId, annotationId) {
  return apiFetch(`/cases/${caseId}/planning/annotations/${annotationId}`, {
    method: 'DELETE',
  });
}

/**
 * Create an annotation referencing an existing computational lesion.
 *
 * @param {string} caseId - The UUID of the case.
 * @param {string} lesionId - Lesion ID (e.g. cyst_left)
 * @param {object} payload - { label?: string, notes?: string }
 * @returns {Promise<object>} Created PlanningTarget
 */
export async function createAnnotationFromLesion(caseId, lesionId, payload = {}) {
  return apiFetch(`/cases/${caseId}/planning/annotations/from-lesion/${lesionId}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
}




