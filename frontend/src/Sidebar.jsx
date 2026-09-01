import React from 'react';
import { ORGAN_DATA } from './data';

const Sidebar = ({ selectedOrgan, onSelectOrgan, visibility, onToggleVisibility }) => {
  return (
    <div className="sidebar">
      <h2>Organ Panel</h2>
      <ul className="organ-list">
        {Object.keys(ORGAN_DATA).map(key => {
          const organ = ORGAN_DATA[key];
          return (
            <li 
              key={key} 
              className={`organ-item ${selectedOrgan === key ? 'selected' : ''}`}
              onClick={() => onSelectOrgan(key)}
            >
              <span className="organ-color-swatch" style={{ backgroundColor: organ.color }}></span>
              <span className="organ-name">{organ.name}</span>
              <button 
                className="visibility-toggle"
                onClick={(e) => {
                  e.stopPropagation();
                  onToggleVisibility(key);
                }}
              >
                {visibility[key] ? '👁️' : '👁️‍🗨️'}
              </button>
            </li>
          );
        })}
      </ul>
    </div>
  );
};

export default Sidebar;
