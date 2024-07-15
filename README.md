# Launch Mesh Kit — Blender Geometry Editing

![3D render of an abstract M-shaped logo made up of blocks with some rounded corners in soft purple, text in the image reads Mesh Kit from the Mograph team at Launch by NTT DATA](images/MeshKit.jpg)

Combining multiple utilities for geometry copy/paste, point arrays, planar UV mapping, and others for Blender 2.8-4.1, Mesh Kit refactors the code for Blender 4.2. Features haven't changed significantly, so for the time being please refer to the original documentation for details.

Includes:

- https://github.com/jeinselen/VF-BlenderCopyPasteGeometry
	- Copy and paste geometry data
- https://github.com/jeinselen/VF-BlenderPlanarUV
	- Planar UV projection
- https://github.com/jeinselen/VF-BlenderPointArray
	- Generate point arrays
- https://github.com/jeinselen/VF-BlenderRadialOffset
	- Radial offset
- https://github.com/jeinselen/VF-BlenderSegmentMesh
	- Mesh segmentation
- https://github.com/jeinselen/VF-BlenderVertexQuantize
	- Quantise vertices



***WARNING: This extension is in early beta and should be installed only for testing purposes.***



## Installation via Extensions Platform:

- Go to Blender Preferences > Get Extensions > Repositories > **＋** > Add Remote Repository
- Set the URL to `https://jeinselen.github.io/Launch-Blender-Extensions/index.json`
- Set the local directory if desired (relative paths seem to fail, try absolute instead)
- Enable `Check for Updates on Start`
- Filter the available extensions for "Launch" and install as needed



## Installation via Download:

- Download the .zip file for a specific kit
- Drag-and-drop the file into Blender

This method will not connect to the centralised repository here on GitHub and updates will not be automatically available. If you don't need easy updates, don't want GitHub servers to be pinged when you start up Blender, or would just like to try some extensions without adding yet another repository to your Blender settings, this is the option for you.

Software is provided as-is with no warranty or provision of suitability. These are internal tools and are shared because we want to support an open community. Bug reports are welcomed, but we cannot commit to fixing or adding features.
