import bpy
import os

# Local imports
from . import copy_paste
from . import mesh_align
from . import planar_uv
from . import point_array
from . import radial_offset
from . import segment_mesh
from . import edit_attribute
from . import utility_panel
from . import uv_mesh
from . import vertex_quantize



###########################################################################
# Global user preferences and UI rendering class

class MeshKitPreferences(bpy.types.AddonPreferences):
	bl_idname = __package__
	
	########## Copy Paste ##########
	
	def update_copypaste_category(self, context):
		utility_panel.register_panels(copy_paste.panels)
	
	copypaste_category: bpy.props.StringProperty(
		name="3D View",
		description="Choose a 3D view tab category for the panel to be placed in, or leave empty to hide the panel",
		default="Launch",
		update=update_copypaste_category)
		# Consider adding search_options=(list of currently available tabs) for easier operation
	
	########## Mesh Align ##########
	
	def update_meshalign_category(self, context):
		utility_panel.register_panels(mesh_align.panels)
	
	meshalign_category: bpy.props.StringProperty(
		name="3D View",
		description="Choose a 3D view tab category for the panel to be placed in, or leave empty to hide the panel",
		default="Launch",
		update=update_meshalign_category)
		# Consider adding search_options=(list of currently available tabs) for easier operation
	
	########## Planar UV ##########
	
	def update_planaruv_category(self, context):
		# Includes the Advanced subpanel, which must follow its parent
		utility_panel.register_panels(planar_uv.panels)
	
	planaruv_category: bpy.props.StringProperty(
		name="3D View",
		description="Choose a 3D view tab category for the panel to be placed in, or leave empty to hide the panel",
		default="Launch",
		update=update_planaruv_category)
		# Consider adding search_options=(list of currently available tabs) for easier operation
	
	########## Point Array ##########
	
	def update_pointarray_category(self, context):
		utility_panel.register_panels(point_array.panels)
	
	pointarray_category: bpy.props.StringProperty(
		name="3D View",
		description="Choose a 3D view tab category for the panel to be placed in, or leave empty to hide the panel",
		default="Launch",
		update=update_pointarray_category)
		# Consider adding search_options=(list of currently available tabs) for easier operation
	
	########## Radial Offset ##########
	
	def update_radialoffset_category(self, context):
		utility_panel.register_panels(radial_offset.panels)
	
	radialoffset_category: bpy.props.StringProperty(
		name="3D View",
		description="Choose a 3D view tab category for the panel to be placed in, or leave empty to hide the panel",
		default="Launch",
		update=update_radialoffset_category)
		# Consider adding search_options=(list of currently available tabs) for easier operation
	
	########## Segment Mesh ##########
	
	def update_segmentmesh_category(self, context):
		utility_panel.register_panels(segment_mesh.panels)
	
	segmentmesh_category: bpy.props.StringProperty(
		name="3D View",
		description="Choose a 3D view tab category for the panel to be placed in, or leave empty to hide the panel",
		default="Launch",
		update=update_segmentmesh_category)
		# Consider adding search_options=(list of currently available tabs) for easier operation
	
	########## Edit Attribute ##########
	
	def update_editattribute_category(self, context):
		utility_panel.register_panels(edit_attribute.panels)
	
	editattribute_category: bpy.props.StringProperty(
		name="3D View",
		description="Choose a 3D view tab category for the panel to be placed in, or leave empty to hide the panel",
		default="Launch",
		update=update_editattribute_category)
		# Consider adding search_options=(list of currently available tabs) for easier operation
	
	########## UV to Mesh ##########
	
	def update_uv_mesh_category(self, context):
		utility_panel.register_panels(uv_mesh.panels)
	
	uv_mesh_category: bpy.props.StringProperty(
		name="3D View",
		description="Choose a 3D view tab category for the panel to be placed in, or leave empty to hide the panel",
		default="Launch",
		update=update_uv_mesh_category)
		# Consider adding search_options=(list of currently available tabs) for easier operation
	
	########## Vertex Quantize ##########
	
	def update_vertexquantise_category(self, context):
		utility_panel.register_panel(vertex_quantize.MESHKIT_PT_vertex_quantize)
	
	def update_vertexquantiseuv_category(self, context):
		utility_panel.register_panel(vertex_quantize.MESHKIT_PT_uv_quantize)
	
	# 3D view tab
	vertexquantize_category: bpy.props.StringProperty(
		name="3D View",
		description="Choose a 3D view tab category for the panel to be placed in, or leave empty to hide the panel",
		default="Launch",
		update=update_vertexquantise_category)
		# Consider adding search_options=(list of currently available tabs) for easier operation
	# UV editor tab
	vertexquantizeuv_category: bpy.props.StringProperty(
		name="UV Editor",
		description="Choose a UV editor tab category for the panel to be placed in, or leave empty to hide the panel",
		default="Tool",
		update=update_vertexquantiseuv_category)
		# Consider adding search_options=(list of currently available tabs) for easier operation
	
	
	
	############################## Preferences UI ##############################
	
	# User Interface
	def draw(self, context):
		settings = context.scene.mesh_kit_settings
		
		layout = self.layout
#		layout.use_property_split = True
		
		########## Copy Paste ##########
		titlegrid = layout.grid_flow(row_major=True, columns=2, even_columns=True, even_rows=True, align=False)
		titlegrid.label(text="Copy Paste", icon="PASTEDOWN") # COPYDOWN PASTEDOWN DUPLICATE
		titlegrid.prop(self, "copypaste_category", text="", icon="VIEW3D")

		########## Edit Attribute ##########
		layout.separator(factor = 2.0)
		titlegrid = layout.grid_flow(row_major=True, columns=2, even_columns=True, even_rows=True, align=False)
		titlegrid.label(text="Edit Attribute", icon="MESH_DATA")
		titlegrid.prop(self, "editattribute_category", text="", icon="VIEW3D")

		########## Mesh Align ##########
		layout.separator(factor = 2.0)
		titlegrid = layout.grid_flow(row_major=True, columns=2, even_columns=True, even_rows=True, align=False)
		titlegrid.label(text="Mesh Align", icon="PIVOT_CURSOR") # PIVOT_CURSOR OBJECT_ORIGIN EMPTY_AXIS ORIENTATION_CURSOR PIVOT_BOUNDBOX MOD_WIREFRAME CUBE LIGHTPROBE_SPHERE
		titlegrid.prop(self, "meshalign_category", text="", icon="VIEW3D")
		
		########## Planar UV ##########
		layout.separator(factor = 2.0)
		titlegrid = layout.grid_flow(row_major=True, columns=2, even_columns=True, even_rows=True, align=False)
		titlegrid.label(text="Planar UV", icon="MOD_UVPROJECT") # UV UV_DATA GROUP_UVS MOD_UVPROJECT FACE_MAPS VIEW_ORTHO
		titlegrid.prop(self, "planaruv_category", text="", icon="VIEW3D")
		
		########## Point Array ##########
		layout.separator(factor = 2.0)
		titlegrid = layout.grid_flow(row_major=True, columns=2, even_columns=True, even_rows=True, align=False)
		titlegrid.label(text="Point Array", icon="GROUP_VERTEX") # GROUP_VERTEX SNAP_VERTEX OUTLINER_OB_POINTCLOUD OUTLINER_DATA_POINTCLOUD POINTCLOUD_DATA POINTCLOUD_POINT
		titlegrid.prop(self, "pointarray_category", text="", icon="VIEW3D")
		
		########## Radial Offset ##########
		layout.separator(factor = 2.0)
		titlegrid = layout.grid_flow(row_major=True, columns=2, even_columns=True, even_rows=True, align=False)
		titlegrid.label(text="Radial Offset", icon="SPHERE") # SPHERE PARTICLE_PATH PROP_ON PROP_CON
		titlegrid.prop(self, "radialoffset_category", text="", icon="VIEW3D")
		
		########## Segment Mesh ##########
		layout.separator(factor = 2.0)
		titlegrid = layout.grid_flow(row_major=True, columns=2, even_columns=True, even_rows=True, align=False)
		titlegrid.label(text="Segment Mesh", icon="MESH_GRID") # MESH_GRID GRID VIEW_ORTHO
		titlegrid.prop(self, "segmentmesh_category", text="", icon="VIEW3D")
		
		########## UV to Mesh ##########
		
		layout.separator(factor = 2.0)
		titlegrid = layout.grid_flow(row_major=True, columns=2, even_columns=True, even_rows=True, align=False)
		titlegrid.label(text="UV to Mesh", icon="UV") # UV UV_DATA GROUP_UVS
		titlegrid.prop(self, "uv_mesh_category", text="", icon="VIEW3D")
		
		########## Vertex Quantize ##########
		layout.separator(factor = 2.0)
		titlegrid = layout.grid_flow(row_major=True, columns=2, even_columns=True, even_rows=True, align=False)
		titlegrid.label(text="Vertex Quantize", icon="UV_VERTEXSEL") # UV_VERTEXSEL NORMALS_VERTEX NORMALS_VERTEX_FACE SNAP_VERTEX
		row = titlegrid.row()
		row.prop(self, "vertexquantize_category", text="", icon="VIEW3D")
		row.prop(self, "vertexquantizeuv_category", text="", icon="UV") # UV MOD_UVPROJECT UV_DATA GROUP_UVS





###########################################################################
# Local project settings

class MeshKitSettings(bpy.types.PropertyGroup):
	
	
	
	########## Edit Attribute ##########
	
	def attribute_enum_items(self, context):
		"""
		Dynamic list of compatible attributes on the active mesh or curves object.

		Includes:
		- Mesh domains: POINT, EDGE, FACE.  Curves domains: POINT, CURVE.
		- Data types: FLOAT, INT, BOOLEAN, FLOAT_VECTOR, FLOAT_COLOR, BYTE_COLOR.
		"""
		items = []

		obj = getattr(context, "active_object", None) if context else None
		if not obj:
			return items
		if obj.type == "MESH":
			valid_domains = {"POINT", "EDGE", "FACE"}
		elif obj.type == "CURVES":
			valid_domains = {"POINT", "CURVE"}
		else:
			return items

		valid_types = {"FLOAT", "INT", "BOOLEAN", "FLOAT_VECTOR", "FLOAT_COLOR", "BYTE_COLOR"}
		for attr in obj.data.attributes:
			if attr.domain not in valid_domains:
				continue
			if attr.data_type not in valid_types:
				continue
			# Skip internal attributes (".selection", ".sculpt_mask", etc.)
			if attr.name.startswith("."):
				continue
			items.append((attr.name, attr.name, ""))

		return items
	
	# Attribute selection
	edit_attribute_name: bpy.props.EnumProperty(
		name="Attribute",
		description="Existing mesh attribute to edit",
		items=attribute_enum_items,
	)
	
	# Float data
	edit_attribute_float_a: bpy.props.FloatProperty(
		name="Input A",
		description="Scalar value for Input A",
		default=0.0,
	)
	edit_attribute_float_b: bpy.props.FloatProperty(
		name="Input B",
		description="Scalar value for Input B",
		default=1.0,
	)
	
	# Vector data
	edit_attribute_vector_a: bpy.props.FloatVectorProperty(
		name="Input A",
		description="Vector value for Input A",
		size=3,
		default=(0.0, 0.0, 0.0),
	)
	edit_attribute_vector_b: bpy.props.FloatVectorProperty(
		name="Input B",
		description="Vector value for Input B",
		size=3,
		default=(1.0, 1.0, 1.0),
	)
	
	# Color data
	edit_attribute_color_a: bpy.props.FloatVectorProperty(
		name="Input A",
		description="Color value for Input A",
		subtype="COLOR",
		size=4,
		min=0.0,
		max=1.0,
		default=(0.0, 0.0, 0.0, 1.0),
	)
	edit_attribute_color_b: bpy.props.FloatVectorProperty(
		name="Input B",
		description="Color value for Input B",
		subtype="COLOR",
		size=4,
		min=0.0,
		max=1.0,
		default=(1.0, 1.0, 1.0, 1.0),
	)

	# Integer data
	edit_attribute_int_a: bpy.props.IntProperty(
		name="Input A",
		description="Integer value for Input A",
		default=0,
	)
	edit_attribute_int_b: bpy.props.IntProperty(
		name="Input B",
		description="Integer value for Input B",
		default=1,
	)

	# Boolean data
	edit_attribute_bool_a: bpy.props.BoolProperty(
		name="Input A",
		description="Boolean value for Input A",
		default=False,
	)
	edit_attribute_bool_b: bpy.props.BoolProperty(
		name="Input B",
		description="Boolean value for Input B",
		default=True,
	)

	# Gradient endpoints
	edit_attribute_item_a: bpy.props.PointerProperty(
		name="Item A",
		description="Scene item used as gradient start point",
		type=bpy.types.Object,
	)
	edit_attribute_item_b: bpy.props.PointerProperty(
		name="Item B",
		description="Scene item used as gradient end point",
		type=bpy.types.Object,
	)
	
	# Interpolation mode: linear, smooth, smoother.
	edit_attribute_interpolation: bpy.props.EnumProperty(
		name="Interpolation",
		description="Gradient interpolation mode",
		items=[
			("LINEAR", "Linear", "Linear interpolation"),
			("SMOOTH", "Smooth", "Smoothstep interpolation"),
			("SMOOTHER", "Smoother", "Smootherstep interpolation"),
			],
		default="LINEAR",
	)
	
	
	
	########## Mesh Align ##########
	
	mesh_align_x: bpy.props.EnumProperty(
		name='X',
		description='X axis alignment',
		items=[
			('X', 'X', 'Leave X coordinate unchanged'),
			('-', '-', 'Align object with negative X'),
			('0', '0', 'Centre object along X axis'),
			('+', '+', 'Align object with positive X')
			],
		default='X')
	mesh_align_y: bpy.props.EnumProperty(
		name='Y',
		description='Y axis alignment',
		items=[
			('Y', 'Y', 'Leave Y coordinate unchanged'),
			('-', '-', 'Align object with negative Y'),
			('0', '0', 'Centre object along Y axis'),
			('+', '+', 'Align object with positive Y')
			],
		default='Y')
	mesh_align_z: bpy.props.EnumProperty(
		name='Z',
		description='Z axis alignment',
		items=[
			('Z', 'Z', 'Leave Z coordinate unchanged'),
			('-', '-', 'Align object with negative Z'),
			('0', '0', 'Centre object along Z axis'),
			('+', '+', 'Align object with positive Z')
			],
		default='Z')
	
	
	
	########## Planar UV ##########
	
	projection_axis: bpy.props.EnumProperty(
		name='Axis',
		description='Planar projection axis',
		items=[
			('X', 'X', 'X axis projection'),
			('Y', 'Y', 'Y axis projection'),
			('Z', 'Z', 'Z axis projection')
			],
		default='X')
	projection_centre: bpy.props.FloatVectorProperty(
		name="Centre",
		description="Centre of the planar projection mapping area",
		subtype="TRANSLATION",
		default=[0.0, 0.0, 0.0],
		step=1.25,
		precision=3)
	projection_size: bpy.props.FloatVectorProperty(
		name="Size",
		description="Size of the planar projection mapping area",
		subtype="TRANSLATION",
		default=[1.0, 1.0, 1.0],
		step=1.25,
		precision=3)
	projection_space: bpy.props.EnumProperty(
		name='Space',
		description='Planar projection coordinate space',
		items=[
			('L', 'Local', 'Projection using local space'),
			('W', 'World', 'Projection using world space')
			],
		default='L')
	projection_rotation: bpy.props.EnumProperty(
		name='Rotation',
		description='Planar projection axis',
		items=[
			('+XY', '0°', 'XY orientation projection'),
			('+YX', '90', 'YX orientation projection'),
			('-XY', '180', '-XY orientation projection'),
			('-YX', '270', '-YX orientation projection')
			],
		default='+XY')
	projection_flip: bpy.props.EnumProperty(
		name='Flip',
		description='Planar projection axis',
		items=[
			('1.0', 'Front', 'Projection from positive direction'),
			('-1.0', 'Back', 'Projection from negative direction')
			],
		default='1.0')
	projection_align: bpy.props.EnumProperty(
		name='Alignment',
		description='UV map alignment',
		items=[
			('0.5', 'Image', 'Align mapped geometry centre to UV 0.5, 0.5'),
			('0.0', 'Zero', 'Align mapped geometry centre to UV 0.0, 0.0')
			],
		default='0.5')
	
	
	
	########## Point Array ##########
	
	array_type: bpy.props.EnumProperty(
		name='Array Type',
		description='The style of point array to create',
		items=[
			('GRID', 'Cubic Grid', 'Cubic array of points'),
			('GOLDEN', 'Golden Angle', 'Spherical area, will be disabled if any of the dimensions are smaller than the maximum point size'),
			('PACK', 'Poisson Disc', 'Generates random points while deleting any that overlap'),
			(None),
			('REC', 'Rectangular Array', 'Rectangular layout of square points'),
			('TRI', 'Triangular Array', 'Triangular layout of triangular points'),
			('TRIHEX', 'Tri-Hex Array', 'Hexagonal layout of triangular points'),
			('HEX', 'Hexagonal Array', 'Hexagonal layout of hexagonal points (will not subdivide without gaps)'),
			('WALK', 'Random Walk', 'Generates a random string of points'),
			(None),
			('QR', 'QR Code', 'Generates a QR code as a mesh of vertices and edges'),
			],
		default='GRID')
	
	# Global point settings
	scale_random: bpy.props.BoolProperty(
		name="Random Radius",
		description="Randomise scale between maximum and minimum",
		default=False)
	scale_minimum: bpy.props.FloatProperty(
		name="Radius",
		description="Minimum scale of the generated points",
		default=0.2,
		step=10,
		precision=4,
		soft_min=0.1,
		soft_max=1.0,
		min=0.0001,
		max=10.0,)
	scale_maximum: bpy.props.FloatProperty(
		name="Radius",
		description="Maximum scale of the generated points",
		default=0.4,
		step=10,
		precision=4,
		soft_min=0.1,
		soft_max=1.0,
		min=0.0001,
		max=10.0,)
	rotation_random: bpy.props.BoolProperty(
		name="Random Rotation",
		description="Rotate each generated point randomly",
		default=False)
	polyline: bpy.props.BoolProperty(
		name="Polyline",
		description="Sequentially connect data points as a polygon line",
		default=False)

	# QR Code settings
	qr_string: bpy.props.StringProperty(
		name="Text",
		description="String to encode in the QR code (URL, text, or any data)",
		default="https://github.com/jeinselen/Blender-MeshKit")
	qr_error: bpy.props.EnumProperty(
		name='Error Correction',
		description='Amount of redundancy added so the code stays readable when partially obscured (higher levels create larger, denser codes)',
		items=[
			('L', 'Low (7%)', 'Recovers roughly 7% of damaged data'),
			('M', 'Medium (15%)', 'Recovers roughly 15% of damaged data'),
			('Q', 'Quartile (25%)', 'Recovers roughly 25% of damaged data'),
			('H', 'High (30%)', 'Recovers roughly 30% of damaged data'),
			],
		default='M')
	qr_invert: bpy.props.EnumProperty(
		name='Invert',
		description='Generate the dark modules of the code, or the light modules instead',
		items=[
			('FOREGROUND', 'Foreground', 'Generate a module for each dark cell of the code'),
			('BACKGROUND', 'Background', 'Generate a module for each light cell instead (the inverted negative space)'),
			],
		default='FOREGROUND')
	qr_output: bpy.props.EnumProperty(
		name='Output',
		description='Geometry created for each module',
		items=[
			('POINTS', 'Points', 'One vertex per module, with adjacent modules joined by edges'),
			('POLYGONS', 'Polygons', 'One solid quad face per module, producing a flat scannable code with no modifier'),
			],
		default='POINTS')
	qr_corners: bpy.props.EnumProperty(
		name='Corners',
		description='How the three finder patterns (positioning markers) are represented',
		items=[
			('MESH', 'Mesh', 'Finder patterns follow the Output setting, tagged via the "region" attribute'),
			('POINT', 'Point', 'Collapse each finder pattern to a single point (region 3) for instancing a custom marker'),
			],
		default='MESH')

	# Cubic Grid settings
	grid_count: bpy.props.IntVectorProperty(
		name="Count",
		subtype="XYZ",
		description="Number of points created in each dimension",
		default=[4, 4, 4],
		step=1,
		soft_min=1,
		soft_max=32,
		min=1,
		max=1024)
	grid_ground: bpy.props.BoolProperty(
		name="Grounded",
		description="Align the base of the cubic grid to Z = 0.0",
		default=False)
	
	# Golden Angle settings
	# Often goes by Fibonacci or Vogel spiral, a specific type of Fermat spiral using the golden angle
	golden_count: bpy.props.IntProperty(
		name="Count",
		description="Number of points to create in the golden angle spiral",
		default=128,
		step=32,
		soft_min=10,
		soft_max=10000,
		min=1,
		max=100000,)
	golden_fill: bpy.props.BoolProperty(
		name="Fill Gap",
		description="Starts the pattern with an extra point near the middle, better filling the visual gap that occurs in a true Vogel array",
		default=False)
	
	# Poisson Disc settings
	area_shape: bpy.props.EnumProperty(
		name='Area Shape',
		description='Mask for the area where points will be created',
		items=[
			('BOX', 'Box', 'Cubic area, setting one of the dimensions to 0 will create a flat square or rectangle'),
			('CYLINDER', 'Cylinder', 'Cylindrical area, setting the Z dimension to 0 will create a flat circle or oval'),
			('SPHERE', 'Sphere', 'Spherical area, will be disabled if any of the dimensions are smaller than the maximum point size'),
			('HULL', 'Hull', 'Spherical hull, adding points just to the surface of a spherical area'),
			],
		default='BOX')
	area_size: bpy.props.FloatVectorProperty(
		name="Dimensions",
		subtype="XYZ",
		description="Size of the area where points will be created",
		default=[4.0, 4.0, 4.0],
		step=10,
		soft_min=0.0,
		soft_max=10.0,
		min=0.0,
		max=1000.0)
	area_alignment: bpy.props.EnumProperty(
		name='Alignment',
		description='Sets how points align to the boundary of the array',
		items=[
			('CENTER', 'Center', 'Points will be contained within the area, but the radius will extend beyond the boundary'),
			('RADIUS', 'Radius', 'Fits the point radius within the boundary area (if the radius is larger than a dimension, it will still extend beyond)')
			],
		default='CENTER')
	area_truncate: bpy.props.FloatProperty(
		name="Truncate",
		description="Trims the extent of the hull starting at -Z",
		default=0.0,
		step=10,
		soft_min=0.0,
		soft_max=1.0,
		min=0.0,
		max=1.0)
	# Point generation limits
	max_elements: bpy.props.IntProperty(
		name="Points",
		description="The maximum number of points that can be created (higher numbers will attempt to fill the space more)",
		default=1000,
		step=10,
		soft_min=10,
		soft_max=1000,
		min=1,
		max=10000,)
	max_failures: bpy.props.IntProperty(
		name="Failures",
		description="The maximum number of consecutive failures before quitting (higher numbers won't give up when the odds are poor)",
		default=10000,
		step=100,
		soft_min=100,
		soft_max=100000,
		min=10,
		max=1000000,)
	max_attempts: bpy.props.IntProperty(
		name="Attempts",
		description="The maximum number of placement attempts before quitting (higher numbers can take minutes to process)",
		default=1000000,
		step=1000,
		soft_min=1000,
		soft_max=10000000,
		min=100,
		max=100000000,)
	# Persistent feedback data
	feedback_elements: bpy.props.StringProperty(
		name="Feedback",
		description="Stores the total points from the last created array",
		default="",)
	feedback_failures: bpy.props.StringProperty(
		name="Feedback",
		description="Stores the maximum number of consecutive failures from the last created array",
		default="",)
	feedback_attempts: bpy.props.StringProperty(
		name="Feedback",
		description="Stores the total attempts from the last created array",
		default="",)
	feedback_time: bpy.props.StringProperty(
		name="Feedback",
		description="Stores the total time spent processing the last created array",
		default="",)

	# Shared array count (Rectangular uses both X and Y, Triangular/Tri-Hex/Hexagonal use only the first value)
	array_count: bpy.props.IntVectorProperty(
		name="Count",
		subtype="XYZ",
		size=2,
		description="Number of starting elements (Rectangular uses X and Y, other arrays use only the first value)",
		default=[8, 8],
		step=1,
		soft_min=1,
		soft_max=20,
		min=1,
		max=100)

	# Shared subdivision settings (Rectangular, Triangular, Tri-Hex, Hexagonal)
	division_levels: bpy.props.IntProperty(
		name="Divisions",
		description="The number of times the algorithm will loop through dividing points",
		default=2,
		step=1,
		soft_min=0,
		soft_max=4,
		min=0,
		max=8,)
	division_percentage: bpy.props.FloatProperty(
		name="Percentage",
		description="Percentage chance that points will be selected for division",
		default=0.5,
		step=10,
		precision=3,
		soft_min=0.0,
		soft_max=1.0,
		min=0.0,
		max=1.0,)

	# Random Walk settings
	walk_dimensions: bpy.props.EnumProperty(
		name='Dimensions',
		description='Dimensions in which points will be created',
		items=[
			('2D', '2D', 'Randomly walk in only X and Y dimensions'),
			('3D', '3D', 'Randomly generate points in all 3 dimensions'),
			],
		default='3D')
	walk_directionality: bpy.props.FloatProperty(
		name="Directionality",
		description="Amount to favour the specified vector when generating each step",
		default=0.0,
		step=10,
		precision=3,
		soft_min=0.0,
		soft_max=1.0,
		min=0.0,
		max=1.0,)
	walk_vector: bpy.props.FloatVectorProperty(
		name="Vector",
		subtype="XYZ",
		description="Vector to favour when generating each step",
		default=[1.0, 0.0, 0.0],
		soft_min=-1.0,
		soft_max=1.0,
		min=-1.0,
		max=1.0,)
	walk_rotation: bpy.props.EnumProperty(
		name='Rotation',
		description='How rotation is assigned to each generated point',
		items=[
			('RANDOM', 'Random', 'Assign a random rotation to each point'),
			('AHEAD', 'Look Ahead', 'Each point will aim at the next point in the sequence'),
			('BEHIND', 'Look Behind', 'Each point will aim at the previous point in the sequence'),
			],
		default='RANDOM')
	walk_decay: bpy.props.BoolProperty(
		name="Radius Decay",
		description='Linearly reduces the maximum radius based on the number of elements created and the maximum number of elements',
		default=False)



	########## Radial Offset ##########
	
	offset_position: bpy.props.EnumProperty(
		name='Position',
		description='Centre point of the transform operation',
		items=[
			('OBJECT', 'Object', 'Offsets from the local mesh object root position'),
			('BOUNDING', 'Selection', 'Offsets from the middle of the selected vertices bounding box'),
#			('ACTIVE', 'Active Vertex', 'Offsets from the active vertex position'),
			('CUSTOM', 'Coordinates', 'Offsets using custom coordinates as the starting point'),
			('CURSOR', '3D Cursor', 'Scales using the 3D cursor position')
			],
		default='OBJECT')
	offset_position_custom: bpy.props.FloatVectorProperty(
		name="Custom",
		description="Position to scale from",
		subtype="TRANSLATION",
		default=[0.0, 0.0, 0.0],
		step=1.25,
		precision=3,
		soft_min=-1.0,
		soft_max=1.0)
	offset_distance: bpy.props.FloatVectorProperty(
		name="Offset",
		description="Radial offset without scaling distortion",
		subtype="TRANSLATION",
		default=[0.1, 0.1, 0.0],
		step=1.25,
		precision=3,
		soft_min=-1.0,
		soft_max=1.0)
	
	
	
	########## Segment Mesh ##########
	
	tile_size: bpy.props.FloatVectorProperty(
		name='Size',
		description='Size of each X/Y tile',
		subtype='XYZ_LENGTH',
		size=2,
		default=(100.0, 100.0),
		step=1,
		precision=2,
		soft_min=1.0,
		soft_max=1000.0,
		min=0.0,
		max=10000.0,
		update=segment_mesh.meshkit_segment_mesh_preview)
	tile_count: bpy.props.IntVectorProperty(
		name="Count",
		description="Number of X/Y tiles",
		subtype="XYZ",
		size=2,
		default=[4, 4],
		step=1,
		soft_min=2,
		soft_max=8,
		min=1,
		max=64,
		update=segment_mesh.meshkit_segment_mesh_preview)
	tile_bounds: bpy.props.EnumProperty(
		name = 'Include',
		description = 'Specify if geometry outside the tile area will be included in the nearest tile or not',
		items = [
			('IN', 'Only Inside', 'Limits tile content to only the elements that fall within each tile boundary'),
			('OUT', 'Extend Edges', 'Includes content beyond the edges of the tile array, ensuring nothing is left out')
			],
		default = 'OUT')
	tile_segment: bpy.props.EnumProperty(
		name = 'Segment',
		description = 'Segment mesh by individual polygons or connected mesh islands',
		items = [
			('POLY', 'Per Polygon', 'Segment mesh by individual polygons (cuts apart merged elements)'),
			('AVERAGE', 'Island Average', 'Segment mesh based on the average vertex positions of each contiguous island (maintains merged elements)'),
			('WEIGHTED', 'Island Weighted', 'Segment mesh based on the weighted polygon positions of each contiguous island (maintains merged elements)')
			],
		default = 'WEIGHTED')
	tile_origin: bpy.props.EnumProperty(
		name = 'Origin',
		description = 'Choose the desired origin for each tile',
		items = [
			('ZERO', 'Zero', 'Leave each tile origin at the local zero point (not ideal in cases where culling algorithms take origin into account)'),
			('TILE', 'Tile', 'Set each tile origin to the centre of the tile space (best for predictable placement but may not be as ideal for transparency sorting in some cases)'),
			('BOX', 'Bounding Box', 'Set each tile origin to the geometry bounding box'),
			('MEDIAN', 'Median', 'Set each tile origin to the geometry median'),
			('MASS', 'Mass', 'Set each tile origin to the geometry mass'),
			('VOLUME', 'Volume', 'Set each tile origin to the geometry volume')
			],
		default = 'TILE')
	show_preview: bpy.props.BoolProperty(
		name="Preview",
		description="Enable preview grid mesh",
		default=False,
		update=segment_mesh.meshkit_segment_mesh_preview)
	
	
	
	########## UV to Mesh ##########
	
	uv_mesh_map: bpy.props.EnumProperty(
		name="UV Map",
		description="UV map to convert into a new mesh, read from the active object's evaluated mesh (including Geometry Nodes output)",
		items=uv_mesh.get_uv_map_items)
	uv_mesh_separator: bpy.props.StringProperty(
		name="Separator",
		description="Separator between the object name and the UV map name used to name the new mesh and object",
		default="_",
		maxlen=16)
	uv_mesh_weld_distance: bpy.props.FloatProperty(
		name="Weld Distance",
		description="Maximum distance for merging coincident UV vertices along seams (equivalent to Merge by Distance)",
		default=0.000001,
		min=0.0,
		soft_min=0.0,
		soft_max=0.001,
		precision=6)
	
	
	
	########## Vertex Quantize ##########
	
	vert_dimensions: bpy.props.EnumProperty(
		name='Vertex Quantization',
		description='Planar projection coordinate space',
		items=[
			('True', 'Uniform', 'Use uniform XYZ dimension snapping'),
			('False', 'Separate', 'Use non-uniform snapping with separate XYZ values')
			],
		default='True')
	vert_uniform: bpy.props.FloatProperty(
		name="Uniform Quantization Value",
		description="Uniform snapping across XYZ axis",
		subtype="DISTANCE",
		default=0.025,
		step=1.25,
		precision=3,
		min=0.0,
		soft_min=0.0,
		soft_max=1.0)
	vert_xyz: bpy.props.FloatVectorProperty(
		name="XYZ Quantization",
		description="XYZ snapping distances",
		subtype="TRANSLATION",
		size=3,
		default=[0.025, 0.025, 0.025],
		step=1.25,
		precision=3,
		min=0,
		soft_min=0.0,
		soft_max=1.0)
	uv_type: bpy.props.EnumProperty(
		name='Space',
		description='Planar projection coordinate space',
		items=[
			('DIV', 'Divisions', 'Specify snapping as UV divisions'),
			('VAL', 'Values', 'Specify snapping as UV value increments')
			],
		default='DIV')
	uv_dimensions: bpy.props.EnumProperty(
		name='Space',
		description='Planar projection coordinate space',
		items=[
			('True', 'Uniform', 'Use uniform UV dimension snapping'),
			('False', 'Separate', 'Use non-uniform snapping with separate UV values')
			],
		default='True')
	uv_div_uniform: bpy.props.IntProperty(
		name="UV Quantization",
		description="UV snapping grid division",
		subtype="NONE",
		default=10,
		step=1,
		min=0,
		soft_min=1,
		soft_max=100)
	uv_div: bpy.props.IntVectorProperty(
		name="UV Quantization",
		description="UV snapping grid divisions",
		subtype="NONE",
		size=2,
		default=[10, 10],
		step=1,
		min=0,
		soft_min=1,
		soft_max=100)
	uv_val_uniform: bpy.props.FloatProperty(
		name="UV Quantization",
		description="UV snapping grid value increment",
		subtype="NONE",
		default=0.1,
		step=1,
		precision=3,
		min=0,
		soft_min=0,
		soft_max=1)
	uv_val: bpy.props.FloatVectorProperty(
		name="UV Quantization",
		description="UV snapping grid value increments",
		subtype="NONE",
		size=2,
		default=[0.1, 0.1],
		step=1,
		precision=3,
		min=0,
		soft_min=0,
		soft_max=1)





###########################################################################
# Addon registration functions
# •Define classes being registered
# •Registration function
# •Unregistration function

classes = (MeshKitPreferences, MeshKitSettings)



def register():
	# Register classes
	for cls in classes:
		bpy.utils.register_class(cls)

	# Add extension settings reference
	bpy.types.Scene.mesh_kit_settings = bpy.props.PointerProperty(type=MeshKitSettings)

	########## Register Components ##########
	copy_paste.register()
	planar_uv.register()
	point_array.register()
	radial_offset.register()
	segment_mesh.register()
	edit_attribute.register()
	mesh_align.register()
	uv_mesh.register()
	vertex_quantize.register()



def unregister():
	########## Unregister Components ##########
	vertex_quantize.unregister()
	uv_mesh.unregister()
	edit_attribute.unregister()
	mesh_align.unregister()
	segment_mesh.unregister()
	radial_offset.unregister()
	point_array.unregister()
	planar_uv.unregister()
	copy_paste.unregister()

	# Remove extension settings reference
	del bpy.types.Scene.mesh_kit_settings
	
	# Deregister classes
	for cls in reversed(classes):
		bpy.utils.unregister_class(cls)



if __name__ == "__main__":
	register()
	