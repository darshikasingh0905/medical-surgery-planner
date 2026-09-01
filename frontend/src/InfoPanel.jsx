import React from 'react';
import { ORGAN_DATA } from './data';

const InfoPanel = ({ selectedOrgan }) => {
  if (!selectedOrgan) {
    return (
      <div className="info-panel empty">
        <p>Select an organ to view information.</p>
      </div>
    );
  }

  const organ = ORGAN_DATA[selectedOrgan];

  return (
    <div className="info-panel">
      <h2>Selected Organ Information</h2>
      <div className="info-content">
        <h3>{organ.name}</h3>
        <p><strong>Volume:</strong> {organ.volume}</p>
        <p><strong>Dimensions (bounding box):</strong> {organ.dimensions}</p>
        <p className="note">
          <em>Note: These are computational estimates derived from Day 4 segmentation data.</em>
        </p>
      </div>
    </div>
  );
};

export default InfoPanel;
