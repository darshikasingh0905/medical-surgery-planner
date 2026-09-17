import React, { Suspense, useMemo, useRef, useEffect, useState } from 'react';
import { Canvas, useThree } from '@react-three/fiber';
import { OrbitControls, GizmoHelper, GizmoViewport, Center } from '@react-three/drei';
import { OBJLoader } from 'three/examples/jsm/loaders/OBJLoader';
import { useLoader } from '@react-three/fiber';
import * as THREE from 'three';
import { ORGAN_DATA, LESION_VISUAL_CONFIG } from './data';

/**
 * OrganMesh — Renders a single organ OBJ mesh with physically-based materials.
 *
 * Improvements (Day 14):
 *  - Per-organ material properties from ORGAN_DATA (roughness, metalness)
 *  - Opacity control support for lesion focus mode
 *  - Smooth PBR shading with environment response
 */
const OrganMesh = ({ organId, url, visible, opacity = 1.0 }) => {
  const organ = ORGAN_DATA[organId];
  const obj = useLoader(OBJLoader, url);
  const meshRef = useRef();

  const geometry = useMemo(() => {
    let geo;
    obj.traverse((child) => {
      if (child.isMesh) {
        geo = child.geometry;
        geo.computeVertexNormals();
      }
    });
    return geo;
  }, [obj]);

  if (!visible || !geometry) return null;

  const isTransparent = opacity < 0.999;

  return (
    <mesh ref={meshRef} geometry={geometry}>
      <meshStandardMaterial
        color={organ.color}
        roughness={organ.roughness ?? 0.4}
        metalness={organ.metalness ?? 0.1}
        side={THREE.DoubleSide}
        transparent={isTransparent}
        opacity={opacity}
        depthWrite={!isTransparent}
      />
    </mesh>
  );
};

/**
 * LesionMesh — Renders a model-predicted lesion OBJ mesh.
 *
 * Clinical governance: labeled as "model-predicted", never as a confirmed diagnosis.
 * Distinct visual treatment (color, emissive glow, subtle transparency) for clinical differentiation.
 */
const LesionMesh = ({ lesionId, classType, url, visible, opacity = 1.0, highlighted = false }) => {
  const config = LESION_VISUAL_CONFIG[classType] ?? LESION_VISUAL_CONFIG.cyst;
  const obj = useLoader(OBJLoader, url);

  const geometry = useMemo(() => {
    let geo;
    obj.traverse((child) => {
      if (child.isMesh) {
        geo = child.geometry;
        geo.computeVertexNormals();
      }
    });
    return geo;
  }, [obj]);

  if (!visible || !geometry) return null;

  const effectiveOpacity = opacity;
  const isTransparent = effectiveOpacity < 0.999;
  const emissiveIntensity = highlighted ? 0.5 : 0.15;

  return (
    <mesh geometry={geometry}>
      <meshStandardMaterial
        color={config.color}
        emissive={config.emissive ?? '#000000'}
        emissiveIntensity={emissiveIntensity}
        roughness={config.roughness ?? 0.2}
        metalness={config.metalness ?? 0.1}
        side={THREE.DoubleSide}
        transparent={isTransparent}
        opacity={effectiveOpacity}
        depthWrite={!isTransparent}
      />
    </mesh>
  );
};

/**
 * CameraController — Handles smooth camera transition to lesion focus position.
 */
function CameraController({ focusTarget, onFocusDone }) {
  const { camera, controls } = useThree();
  const frameRef = useRef(null);

  useEffect(() => {
    if (!focusTarget) return;

    const target = focusTarget;
    const startPos = camera.position.clone();
    const destPos = new THREE.Vector3(target[0], target[1] - 80, target[2] + 60);

    let t = 0;
    const duration = 60;

    function animate() {
      t++;
      const alpha = Math.min(t / duration, 1);
      const eased = 1 - Math.pow(1 - alpha, 3);
      camera.position.lerpVectors(startPos, destPos, eased);
      if (controls) controls.target.set(target[0], target[1], target[2]);
      if (alpha < 1) {
        frameRef.current = requestAnimationFrame(animate);
      } else if (onFocusDone) {
        onFocusDone();
      }
    }

    frameRef.current = requestAnimationFrame(animate);
    return () => {
      if (frameRef.current) cancelAnimationFrame(frameRef.current);
    };
  }, [focusTarget, camera, controls, onFocusDone]);

  return null;
}

/**
 * OrganErrorBoundary — Per-organ/lesion error boundary.
 * Silently suppresses 404 or OBJ load errors — the rest of the scene continues.
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
    console.warn(`Mesh load failed for ${this.props.organId}:`, error.message);
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
 *   visibility       {object}      — map of organId → boolean
 *   meshUrls         {object|null} — map of organId → URL string (from backend)
 *   lesions          {Array}       — lesion objects from /api/cases/{id}/lesions
 *   lesionVisibility {object}      — map of lesionId → boolean
 *   lesionOpacity    {number}      — global lesion opacity (0–1)
 *   focusedLesion    {object|null} — lesion being focused (triggers camera transition)
 *   organOpacities   {object}      — map of organId → opacity override (for focus mode)
 *   onFocusDone      {function}    — called after camera transition completes
 *
 * Day 14 improvements:
 *   - Per-organ PBR materials (roughness, metalness)
 *   - Lesion rendering with distinct materials
 *   - Lesion focus camera animation
 *   - Improved lighting for depth perception
 */
const Viewer3D = ({
  visibility,
  meshUrls,
  lesions = [],
  lesionVisibility = {},
  lesionOpacity = 1.0,
  focusedLesion = null,
  organOpacities = {},
  onFocusDone,
}) => {
  const [focusTarget, setFocusTarget] = useState(null);

  useEffect(() => {
    if (focusedLesion?.centroid_mm) {
      const [x, y, z] = focusedLesion.centroid_mm;
      setFocusTarget([x, z, -y]); // NIfTI → Three.js axis conversion (matches -PI/2 rotation group)
    } else {
      setFocusTarget(null);
    }
  }, [focusedLesion]);

  return (
    <div className="viewer-container">
      <Canvas
        camera={{ position: [0, -300, 300], fov: 50, up: [0, 0, 1] }}
        gl={{ antialias: true, toneMapping: THREE.ACESFilmicToneMapping, toneMappingExposure: 1.1 }}
      >
        <color attach="background" args={['#111820']} />

        {/* Improved multi-light rig for clinical depth perception */}
        <ambientLight intensity={0.35} />
        <directionalLight position={[200, 300, 200]} intensity={1.4} castShadow={false} />
        <directionalLight position={[-150, -200, 100]} intensity={0.5} />
        <directionalLight position={[0, -300, -50]} intensity={0.3} />
        <pointLight position={[0, 0, 400]} intensity={0.4} color="#cce0ff" />

        <Suspense fallback={null}>
          <Center>
            {/* Medical coordinate correction: NIfTI RAS → Three.js scene */}
            <group rotation={[-Math.PI / 2, 0, 0]}>
              {/* ── Organ meshes ── */}
              {meshUrls && Object.keys(ORGAN_DATA).map(key => {
                const organOpacity = organOpacities[key] ?? (ORGAN_DATA[key].defaultOpacity ?? 1.0);
                return (
                  <OrganErrorBoundary key={key} organId={key}>
                    <OrganMesh
                      organId={key}
                      url={meshUrls[key]}
                      visible={visibility[key]}
                      opacity={organOpacity}
                    />
                  </OrganErrorBoundary>
                );
              })}

              {/* ── Model-predicted lesion meshes ── */}
              {lesions.map(lesion => {
                if (!meshUrls) return null;
                const classType = lesion.class_name ?? 'cyst';
                const lesionMeshUrl = meshUrls[lesion.lesion_id];
                if (!lesionMeshUrl) return null;
                const isVisible = lesionVisibility[lesion.lesion_id] !== false;
                const isHighlighted = focusedLesion?.lesion_id === lesion.lesion_id;

                return (
                  <OrganErrorBoundary key={lesion.lesion_id} organId={lesion.lesion_id}>
                    <LesionMesh
                      lesionId={lesion.lesion_id}
                      classType={classType}
                      url={lesionMeshUrl}
                      visible={isVisible}
                      opacity={lesionOpacity}
                      highlighted={isHighlighted}
                    />
                  </OrganErrorBoundary>
                );
              })}
            </group>
          </Center>
        </Suspense>

        {/* Smooth camera animation toward focused lesion */}
        <CameraController
          focusTarget={focusTarget}
          onFocusDone={onFocusDone}
        />

        <OrbitControls makeDefault />
        <GizmoHelper alignment="bottom-right" margin={[80, 80]}>
          <GizmoViewport axisColors={['#e74c3c', '#2ecc71', '#3498db']} labelColor="white" />
        </GizmoHelper>
      </Canvas>
    </div>
  );
};

export default Viewer3D;
