import React, { Suspense, useMemo, useRef, useEffect, useState, useCallback } from 'react';
import { Canvas, useThree } from '@react-three/fiber';
import { OrbitControls, GizmoHelper, GizmoViewport, Center } from '@react-three/drei';
import { OBJLoader } from 'three/examples/jsm/loaders/OBJLoader';
import { useLoader } from '@react-three/fiber';
import * as THREE from 'three';
import { ORGAN_DATA, LESION_VISUAL_CONFIG, ANATOMICAL_STRUCTURE_STYLES } from './data';

/**
 * OrganMesh — Renders a single anatomical structure OBJ mesh.
 * Supports highlighting, transparency overrides, and center calculation.
 */
const OrganMesh = ({
  organId,
  url,
  visible,
  opacity = 1.0,
  highlighted = false,
  onRegisterCenter,
}) => {
  const organStyle = ORGAN_DATA[organId] || ANATOMICAL_STRUCTURE_STYLES[organId] || {
    color: '#94A3B8',
    roughness: 0.4,
    metalness: 0.1,
  };

  const obj = useLoader(OBJLoader, url);
  const meshRef = useRef();

  const geometry = useMemo(() => {
    let geo = null;
    obj.traverse((child) => {
      if (child.isMesh) {
        geo = child.geometry;
        geo.computeVertexNormals();
        geo.computeBoundingBox();
      }
    });
    return geo;
  }, [obj]);

  // Report center in NIfTI coordinates so camera focus can target it
  useEffect(() => {
    if (geometry && geometry.boundingBox && onRegisterCenter) {
      const center = new THREE.Vector3();
      geometry.boundingBox.getCenter(center);
      // Under group rotation [-PI/2, 0, 0]: local [x, y, z] -> world [x, z, -y]
      onRegisterCenter(organId, [center.x, center.z, -center.y]);
    }
  }, [geometry, organId, onRegisterCenter]);

  if (!visible || !geometry) return null;

  const isTransparent = opacity < 0.999;
  const baseColor = organStyle.color || '#94A3B8';
  const emissiveColor = highlighted ? baseColor : '#000000';
  const emissiveIntensity = highlighted ? 0.45 : 0.0;

  return (
    <mesh ref={meshRef} geometry={geometry}>
      <meshStandardMaterial
        color={baseColor}
        emissive={emissiveColor}
        emissiveIntensity={emissiveIntensity}
        roughness={organStyle.roughness ?? 0.4}
        metalness={organStyle.metalness ?? 0.1}
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
 */
const LesionMesh = ({
  lesionId,
  classType,
  url,
  visible,
  opacity = 1.0,
  highlighted = false,
}) => {
  const config = LESION_VISUAL_CONFIG[classType] ?? LESION_VISUAL_CONFIG.cyst;
  const obj = useLoader(OBJLoader, url);

  const geometry = useMemo(() => {
    let geo = null;
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
  const emissiveIntensity = highlighted ? 0.65 : 0.2;

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
 * CameraController — Smoothly animates camera focus to target position or resets to home.
 */
function CameraController({ focusTarget, resetTrigger, onFocusDone }) {
  const { camera, controls } = useThree();
  const frameRef = useRef(null);

  // Focus on target
  useEffect(() => {
    if (!focusTarget) return;

    const target = focusTarget;
    const startPos = camera.position.clone();
    const destPos = new THREE.Vector3(target[0], target[1] - 120, target[2] + 90);

    let t = 0;
    const duration = 50;

    function animate() {
      t++;
      const alpha = Math.min(t / duration, 1);
      const eased = 1 - Math.pow(1 - alpha, 3);
      camera.position.lerpVectors(startPos, destPos, eased);
      if (controls) {
        controls.target.set(target[0], target[1], target[2]);
        controls.update();
      }
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

  // Reset view to default
  useEffect(() => {
    if (!resetTrigger) return;

    const startPos = camera.position.clone();
    const destPos = new THREE.Vector3(0, -300, 300);
    const startTarget = controls ? controls.target.clone() : new THREE.Vector3(0, 0, 0);
    const destTarget = new THREE.Vector3(0, 0, 0);

    let t = 0;
    const duration = 40;

    function animate() {
      t++;
      const alpha = Math.min(t / duration, 1);
      const eased = 1 - Math.pow(1 - alpha, 3);
      camera.position.lerpVectors(startPos, destPos, eased);
      if (controls) {
        controls.target.lerpVectors(startTarget, destTarget, eased);
        controls.update();
      }
      if (alpha < 1) {
        frameRef.current = requestAnimationFrame(animate);
      }
    }

    frameRef.current = requestAnimationFrame(animate);
    return () => {
      if (frameRef.current) cancelAnimationFrame(frameRef.current);
    };
  }, [resetTrigger, camera, controls]);

  return null;
}

/**
 * OrganErrorBoundary — Per-mesh error boundary.
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
 * Supports standard view and preoperative planning view.
 * Dynamically renders all available anatomical structures and model-predicted lesions.
 */
const Viewer3D = ({
  visibility = {},
  meshUrls = {},
  lesions = [],
  lesionVisibility = {},
  lesionOpacity = 1.0,
  organOpacities = {},
  selectedStructure = null,
  focusedTarget = null,
  isPlanningView = false,
  onFocusDone,
  onResetCamera,
}) => {
  const [centers, setCenters] = useState({});
  const [resetCount, setResetCount] = useState(0);

  const handleRegisterCenter = useCallback((id, centerCoords) => {
    setCenters((prev) => ({ ...prev, [id]: centerCoords }));
  }, []);

  // Compute camera target based on focusedTarget (lesion object, structure id, or explicit coordinates)
  const computedFocusTarget = useMemo(() => {
    if (!focusedTarget) return null;

    // Direct [x, y, z] coordinates
    if (Array.isArray(focusedTarget) && focusedTarget.length === 3) {
      return focusedTarget;
    }

    // Lesion with centroid_mm
    if (focusedTarget.centroid_mm) {
      const [x, y, z] = focusedTarget.centroid_mm;
      return [x, z, -y];
    }

    // Structure ID registered in centers map
    if (typeof focusedTarget === 'string' && centers[focusedTarget]) {
      return centers[focusedTarget];
    }

    return null;
  }, [focusedTarget, centers]);

  const handleReset = () => {
    setResetCount((c) => c + 1);
    if (onResetCamera) onResetCamera();
  };

  // Collect all mesh keys to render (organs + registered anatomical structures)
  const allMeshKeys = useMemo(() => {
    if (!meshUrls) return [];
    return Object.keys(meshUrls).filter(
      (key) => !lesions.some((l) => l.lesion_id === key)
    );
  }, [meshUrls, lesions]);

  return (
    <div className="viewer-container">
      {/* ── Viewport HUD / Mode Indicator ── */}
      <div className="viewer-hud">
        {isPlanningView && (
          <div className="viewer-mode-badge" title="Preoperative Planning View Active">
            <span className="mode-pulse-dot" />
            Planning View
          </div>
        )}
        <button
          id="btn-reset-camera"
          className="viewer-hud-btn"
          onClick={handleReset}
          title="Reset camera view to home position"
        >
          🔄 Reset View
        </button>
      </div>

      <Canvas
        camera={{ position: [0, -300, 300], fov: 50, up: [0, 0, 1] }}
        gl={{ antialias: true, toneMapping: THREE.ACESFilmicToneMapping, toneMappingExposure: 1.1 }}
      >
        <color attach="background" args={['#111820']} />

        {/* Multi-light rig for depth perception */}
        <ambientLight intensity={0.4} />
        <directionalLight position={[200, 300, 200]} intensity={1.4} castShadow={false} />
        <directionalLight position={[-150, -200, 100]} intensity={0.5} />
        <directionalLight position={[0, -300, -50]} intensity={0.3} />
        <pointLight position={[0, 0, 400]} intensity={0.4} color="#cce0ff" />

        <Suspense fallback={null}>
          <Center>
            {/* Coordinate correction: NIfTI RAS -> Three.js scene */}
            <group rotation={[-Math.PI / 2, 0, 0]}>
              {/* ── Anatomical Structure Meshes ── */}
              {allMeshKeys.map((key) => {
                const url = meshUrls[key];
                if (!url) return null;
                const isVisible = visibility[key] !== false;
                const opacityOverride = organOpacities[key] ?? 1.0;
                const isHighlighted = selectedStructure === key;

                return (
                  <OrganErrorBoundary key={key} organId={key}>
                    <OrganMesh
                      organId={key}
                      url={url}
                      visible={isVisible}
                      opacity={opacityOverride}
                      highlighted={isHighlighted}
                      onRegisterCenter={handleRegisterCenter}
                    />
                  </OrganErrorBoundary>
                );
              })}

              {/* ── Model-Predicted Lesion Meshes ── */}
              {lesions.map((lesion) => {
                const url = meshUrls[lesion.lesion_id];
                if (!url) return null;
                const classType = lesion.class_name ?? 'cyst';
                const isVisible = lesionVisibility[lesion.lesion_id] !== false;
                const isHighlighted =
                  selectedStructure === lesion.lesion_id ||
                  focusedTarget?.lesion_id === lesion.lesion_id;

                return (
                  <OrganErrorBoundary key={lesion.lesion_id} organId={lesion.lesion_id}>
                    <LesionMesh
                      lesionId={lesion.lesion_id}
                      classType={classType}
                      url={url}
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

        {/* Smooth camera animation */}
        <CameraController
          focusTarget={computedFocusTarget}
          resetTrigger={resetCount}
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
