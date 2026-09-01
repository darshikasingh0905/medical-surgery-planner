# Web Viewer Technical Reference

This document serves as a reusable technical reference for setting up and configuring the 3D anatomical viewer in the frontend using React Three Fiber.

## Core Setup

The viewer uses `@react-three/fiber` as the React renderer for Three.js, and `@react-three/drei` for useful abstractions (like controls and helpers).

```bash
npm install three @react-three/fiber @react-three/drei
```

## Loading OBJ Meshes

To load wavefront `.obj` files, we use the `OBJLoader` from Three.js in combination with the `useLoader` hook from `@react-three/fiber`.

```javascript
import { useLoader } from '@react-three/fiber';
import { OBJLoader } from 'three/examples/jsm/loaders/OBJLoader';

const obj = useLoader(OBJLoader, '/path/to/mesh.obj');
```

**Important considerations for anatomical meshes:**
- The `useLoader` hook caches the loaded object. To apply different materials or modify geometry without affecting the cached version across multiple instances, it is recommended to traverse and extract the geometry, rather than rendering the raw object directly.
- Anatomical meshes exported via Marching Cubes often have sharp faceted edges. Applying smooth shading significantly improves visual quality.

```javascript
const geometry = useMemo(() => {
  let geo;
  obj.traverse((child) => {
    if (child.isMesh) {
      geo = child.geometry;
      // Essential for smooth shading of medical meshes
      geo.computeVertexNormals();
    }
  });
  return geo;
}, [obj]);
```

## Scene Configuration

A typical medical viewing scene requires clear, uncolored lighting and intuitive navigation.

### Lighting
We use a combination of Ambient and Directional lights to provide base visibility and depth perception across the complex curved surfaces of organs.

```javascript
<ambientLight intensity={0.5} />
<directionalLight position={[10, 10, 10]} intensity={1} />
<directionalLight position={[-10, -10, -10]} intensity={0.5} />
```

### Camera & Controls
We rely on `OrbitControls` to handle pan, zoom, and rotation interactions automatically.

```javascript
import { OrbitControls, Center } from '@react-three/drei';

<Canvas camera={{ position: [0, -300, 300], fov: 50, up: [0, 0, 1] }}>
  <Center>
    {/* Scene contents */}
  </Center>
  <OrbitControls makeDefault />
</Canvas>
```
*Note: Depending on the coordinate system of the exported meshes, the initial camera position, `up` vector, and group rotation may need to be adjusted. Medical imaging often uses different coordinate conventions (e.g., LPS/RAS) than standard graphics (Y-up).*

### Materials
We use `meshStandardMaterial` for realistic lighting reactions. `DoubleSide` is recommended for anatomical structures that might have open boundaries (e.g., clipped vessels).

```javascript
<meshStandardMaterial 
  color="#8B0000" 
  roughness={0.4} 
  metalness={0.1} 
  side={THREE.DoubleSide} 
/>
```
