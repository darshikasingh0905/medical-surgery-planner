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
  kidney_right: {
    id: 'kidney_right',
    name: 'Right Kidney',
    color: '#D48828',
    roughness: 0.35,
    metalness: 0.1,
    defaultOpacity: 0.85,
  },
  inferior_vena_cava: {
    id: 'inferior_vena_cava',
    name: 'Inferior Vena Cava',
    color: '#3B82F6',
    roughness: 0.35,
    metalness: 0.15,
    defaultOpacity: 0.9,
  },
  adrenal_gland_left: {
    id: 'adrenal_gland_left',
    name: 'Left Adrenal Gland',
    color: '#D97706',
    roughness: 0.4,
    metalness: 0.1,
    defaultOpacity: 0.85,
  },
  adrenal_gland_right: {
    id: 'adrenal_gland_right',
    name: 'Right Adrenal Gland',
    color: '#B45309',
    roughness: 0.4,
    metalness: 0.1,
    defaultOpacity: 0.85,
  },
};

/**
 * Visual styling configuration for all registered anatomical structures.
 */
export const ANATOMICAL_STRUCTURE_STYLES = {
  kidney_left: { color: '#E5A93C', category: 'organ' },
  kidney_right: { color: '#D48828', category: 'organ' },
  aorta: { color: '#FF6347', category: 'vascular' },
  inferior_vena_cava: { color: '#3B82F6', category: 'vascular' },
  renal_artery: { color: '#EF4444', category: 'vascular' },
  renal_vein: { color: '#60A5FA', category: 'vascular' },
  renal_pelvis: { color: '#F59E0B', category: 'collecting_system' },
  ureter: { color: '#FCD34D', category: 'collecting_system' },
  adrenal_gland_left: { color: '#D97706', category: 'endocrine' },
  adrenal_gland_right: { color: '#B45309', category: 'endocrine' },
  liver: { color: '#8B0000', category: 'organ' },
  heart: { color: '#FA8072', category: 'organ' },
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

