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
    roughness: 0.45,
    metalness: 0.05,
    defaultOpacity: 0.9,
  },
  heart: {
    id: 'heart',
    name: 'Heart',
    color: '#FA8072', // Salmon
    roughness: 0.4,
    metalness: 0.1,
    defaultOpacity: 0.9,
  },
  aorta: {
    id: 'aorta',
    name: 'Aorta',
    color: '#FF6347', // Tomato Red
    roughness: 0.35,
    metalness: 0.15,
    defaultOpacity: 0.95,
  },
  kidney_left: {
    id: 'kidney_left',
    name: 'Left Kidney',
    color: '#E5A93C', // Warm Anatomical Gold
    roughness: 0.35,
    metalness: 0.1,
    defaultOpacity: 0.85,
    focusOpacity: 0.30, // Reduced opacity when inspecting internal lesion
  },
};

/**
 * Visual styling configuration for model-predicted lesions.
 * Designed for clinical distinction and depth perception.
 */
export const LESION_VISUAL_CONFIG = {
  cyst: {
    name: 'Renal Cyst (Model Predicted)',
    color: '#00E5FF', // High-contrast translucent cyan
    emissive: '#003344',
    roughness: 0.15,
    metalness: 0.1,
    defaultOpacity: 0.95,
  },
  tumor: {
    name: 'Renal Tumor (Model Predicted)',
    color: '#FF5722', // High-contrast amber/coral
    emissive: '#441000',
    roughness: 0.4,
    metalness: 0.1,
    defaultOpacity: 0.95,
  },
};

