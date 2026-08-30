import argparse
import sys
from pathlib import Path
import pyvista as pv

# Colors for different anatomical structures to ensure they are visually distinguishable
ORGAN_COLORS = {
    "liver": "darkred",
    "heart": "salmon",
    "aorta": "red",
    "kidney_left": "yellow",
}

def load_mesh(mesh_path: Path):
    """
    Loads a 3D mesh from a given file path using PyVista.
    """
    if not mesh_path.exists():
        raise FileNotFoundError(f"Mesh file not found: {mesh_path}")
        
    # PyVista reads .obj files seamlessly.
    mesh = pv.read(str(mesh_path))
    return mesh

def print_mesh_stats(organ_name: str, mesh: pv.PolyData):
    """
    Prints basic validation information about a loaded mesh.
    """
    print(f"\n--- {organ_name.upper()} ---")
    print(f"Points (Vertices): {mesh.n_points}")
    print(f"Cells (Faces): {mesh.n_cells}")
    
    bounds = mesh.bounds
    # bounds are (xmin, xmax, ymin, ymax, zmin, zmax)
    dimensions = (
        bounds[1] - bounds[0],
        bounds[3] - bounds[2],
        bounds[5] - bounds[4]
    )
    print(f"Bounding Box: Min({bounds[0]:.2f}, {bounds[2]:.2f}, {bounds[4]:.2f}) "
          f"Max({bounds[1]:.2f}, {bounds[3]:.2f}, {bounds[5]:.2f})")
    print(f"Dimensions (mm): {dimensions[0]:.2f} x {dimensions[1]:.2f} x {dimensions[2]:.2f}")

def create_scene():
    """
    Initializes and returns a PyVista Plotter (the 3D scene).
    """
    plotter = pv.Plotter(title="Medical Surgery Planner - 3D Anatomy Viewer")
    plotter.set_background("black")
    
    # Adds a useful 3D orientation axis in the corner
    plotter.add_axes()
    
    return plotter

def add_organ(plotter: pv.Plotter, mesh: pv.PolyData, organ_name: str, color: str):
    """
    Adds a mesh to the plotter with a specific color and enables smooth shading.
    """
    plotter.add_mesh(
        mesh,
        color=color,
        opacity=1.0,
        smooth_shading=True,
        label=organ_name
    )

def main():
    parser = argparse.ArgumentParser(description="Interactive 3D Anatomy Viewer using PyVista")
    parser.add_argument("--mesh-dir", type=str, default="outputs/meshes", help="Directory containing the OBJ meshes")
    parser.add_argument("--test-mode", action="store_true", help="Run in test mode (loads meshes, prints stats, and exits without blocking)")
    
    args = parser.parse_args()
    mesh_dir = Path(args.mesh_dir)
    
    if not mesh_dir.exists():
        print(f"[ERROR] Mesh directory not found: {mesh_dir}")
        sys.exit(1)
        
    organs_to_load = ["liver", "heart", "aorta", "kidney_left"]
    
    plotter = create_scene()
    
    print("Loading 3D anatomy meshes...")
    
    successful_loads = 0
    for organ in organs_to_load:
        mesh_path = mesh_dir / f"{organ}.obj"
        try:
            mesh = load_mesh(mesh_path)
            
            # Use predefined color or fallback to white
            color = ORGAN_COLORS.get(organ, "white")
            
            add_organ(plotter, mesh, organ, color)
            print_mesh_stats(organ, mesh)
            
            successful_loads += 1
        except Exception as e:
            print(f"[WARNING] Could not load {organ}: {e}")
            
    if successful_loads == 0:
        print("[ERROR] No meshes were loaded. Ensure Day 2 completed successfully.")
        sys.exit(1)
        
    # Add a legend for the labels
    plotter.add_legend()
    
    print(f"\n[INFO] Successfully loaded {successful_loads}/{len(organs_to_load)} meshes.")
    
    if args.test_mode:
        print("[INFO] Test mode enabled. Closing viewer immediately.")
        # Render a frame off-screen to verify the pipeline works, then exit
        plotter.show(auto_close=True, interactive=False)
    else:
        print("[INFO] Launching interactive 3D viewer. Use the mouse to rotate, zoom, and pan.")
        plotter.show()

if __name__ == "__main__":
    main()
