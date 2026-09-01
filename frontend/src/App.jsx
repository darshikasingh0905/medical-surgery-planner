import React, { useState } from 'react';
import Sidebar from './Sidebar';
import Viewer3D from './Viewer3D';
import InfoPanel from './InfoPanel';
import { ORGAN_DATA } from './data';
import './index.css';

function App() {
  const [selectedOrgan, setSelectedOrgan] = useState(null);
  
  // State for visibility of each organ
  const [visibility, setVisibility] = useState(
    Object.keys(ORGAN_DATA).reduce((acc, key) => {
      acc[key] = true;
      return acc;
    }, {})
  );

  const handleToggleVisibility = (key) => {
    setVisibility(prev => ({
      ...prev,
      [key]: !prev[key]
    }));
  };

  return (
    <div className="app-container">
      <header className="app-header">
        <h1>MEDICAL SURGERY PLANNER</h1>
      </header>
      
      <div className="app-content">
        <aside className="app-sidebar">
          <Sidebar 
            selectedOrgan={selectedOrgan}
            onSelectOrgan={setSelectedOrgan}
            visibility={visibility}
            onToggleVisibility={handleToggleVisibility}
          />
        </aside>
        
        <main className="app-main">
          <Viewer3D visibility={visibility} />
        </main>
      </div>
      
      <footer className="app-footer">
        <InfoPanel selectedOrgan={selectedOrgan} />
      </footer>
    </div>
  );
}

export default App;
