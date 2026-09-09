import React, { Suspense, useMemo } from 'react';
import { Canvas } from '@react-three/fiber';
import { OrbitControls, GizmoHelper, GizmoViewport, Center } from '@react-three/drei';
import { OBJLoader } from 'three/examples/jsm/loaders/OBJLoader';
import { useLoader } from '@react-three/fiber';
import * as THREE from 'three';
import { ORGAN_DATA } from './data';

/**
 * OrganMesh — Renders a single organ OBJ mesh from a dynamic URL.
 *
 * Props:
 *   organId  {string}  — key in ORGAN_DATA (used for color)
 *   url      {string}  — full URL to the .obj file (from getMeshUrl or static)
 *   visible  {boolean} — controls Three.js mesh visibility
 *
 * Graceful degradation: if the mesh URL returns a 404 or fails to load,
 * the error is caught by the per-organ ErrorBoundary and that organ is
 * simply not rendered — the rest of the scene continues to function.
 */
const OrganMesh = ({ organId, url, visible }) => {
  const organ = ORGAN_DATA[organId];
  const obj = useLoader(OBJLoader, url);

  const geometry = useMemo(() => {
    let geo;
    obj.traverse((child) => {
      if (child.isMesh) {
        geo = child.geometry;
        // Compute vertex normals for smooth shading of Marching Cubes meshes
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

/**
 * OrganErrorBoundary — Per-organ error boundary.
 * If an organ's mesh fails to load (404, network error, malformed OBJ),
 * this boundary swallows the error silently so the rest of the scene remains intact.
 */
class OrganErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false };
  }

  static getDerivedStateFromError() {
    return { hasError: true };
  }

  componentDidCatch(error) {
    console.warn(`OrganMesh load failed for ${this.props.organId}:`, error.message);
  }

  render() {
    if (this.state.hasError) return null;
    return this.props.children;
  }
}

/**
 * Viewer3D — 3D anatomical scene using React Three Fiber.
 *
 * Props:
 *   visibility {object} — map of organId → boolean
 *   meshUrls   {object|null} — map of organId → URL string (from backend)
 *                              If null, nothing is rendered in the scene.
 *
 * Preserved from Day 5:
 *   - OrbitControls (pan, zoom, rotate)
 *   - GizmoHelper with axis viewport
 *   - Ambient + directional + spot lighting
 *   - Smooth shading via computeVertexNormals
 *   - DoubleSide material
 *   - Rotation group correcting medical image coordinate conventions
 *   - Dark background (#1a1a1a)
 */
const Viewer3D = ({ visibility, meshUrls }) => {
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
              {meshUrls && Object.keys(ORGAN_DATA).map(key => (
                <OrganErrorBoundary key={key} organId={key}>
                  <OrganMesh
                    organId={key}
                    url={meshUrls[key]}
                    visible={visibility[key]}
                  />
                </OrganErrorBoundary>
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
