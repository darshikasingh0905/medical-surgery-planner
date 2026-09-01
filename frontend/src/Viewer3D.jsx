import React, { Suspense, useMemo } from 'react';
import { Canvas } from '@react-three/fiber';
import { OrbitControls, GizmoHelper, GizmoViewport, Center } from '@react-three/drei';
import { OBJLoader } from 'three/examples/jsm/loaders/OBJLoader';
import { useLoader } from '@react-three/fiber';
import * as THREE from 'three';
import { ORGAN_DATA } from './data';

const OrganMesh = ({ organId, visible }) => {
  const organ = ORGAN_DATA[organId];
  const obj = useLoader(OBJLoader, organ.file);
  
  // Create material and clone the object so we don't mutate the cached one
  const geometry = useMemo(() => {
    let geo;
    obj.traverse((child) => {
      if (child.isMesh) {
        geo = child.geometry;
        // Compute vertex normals for smooth shading
        geo.computeVertexNormals();
      }
    });
    return geo;
  }, [obj]);

  if (!visible || !geometry) return null;

  return (
    <mesh geometry={geometry}>
      <meshStandardMaterial 
        color={organ.color} 
        roughness={0.4} 
        metalness={0.1} 
        side={THREE.DoubleSide} 
      />
    </mesh>
  );
};

const Viewer3D = ({ visibility }) => {
  return (
    <div className="viewer-container">
      <Canvas camera={{ position: [0, -300, 300], fov: 50, up: [0, 0, 1] }}>
        <color attach="background" args={['#1a1a1a']} />
        
        <ambientLight intensity={0.5} />
        <directionalLight position={[10, 10, 10]} intensity={1} />
        <directionalLight position={[-10, -10, -10]} intensity={0.5} />
        <spotLight position={[0, 500, 0]} intensity={0.8} />

        <Suspense fallback={null}>
          <Center>
            <group rotation={[-Math.PI / 2, 0, 0]}>
              {Object.keys(ORGAN_DATA).map(key => (
                <OrganMesh 
                  key={key} 
                  organId={key} 
                  visible={visibility[key]} 
                />
              ))}
            </group>
          </Center>
        </Suspense>

        <OrbitControls makeDefault />
        <GizmoHelper alignment="bottom-right" margin={[80, 80]}>
          <GizmoViewport axisColors={['red', 'green', 'blue']} labelColor="black" />
        </GizmoHelper>
      </Canvas>
    </div>
  );
};

export default Viewer3D;
