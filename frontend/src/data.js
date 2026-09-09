/**
 * data.js — Static organ metadata (display only).
 *
 * File paths, volumes, and dimensions have been removed from this file.
 * Measurements come from the live backend: GET /api/cases/{case_id}/results
 * Mesh URLs are built dynamically via api.getMeshUrl(caseId, organ).
 *
 * Only the display metadata that is always constant is stored here:
 * id, name, and color.
 */
export const ORGAN_DATA = {
  liver: {
    id: 'liver',
    name: 'Liver',
    color: '#8B0000', // Dark Red
  },
  heart: {
    id: 'heart',
    name: 'Heart',
    color: '#FA8072', // Salmon
  },
  aorta: {
    id: 'aorta',
    name: 'Aorta',
    color: '#FF6347', // Tomato Red
  },
  kidney_left: {
    id: 'kidney_left',
    name: 'Left Kidney',
    color: '#FFD700', // Gold
  },
};
