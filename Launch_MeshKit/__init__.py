import bpy
import os

# Local imports
from .copy_paste import MeshKit_Copy, MeshKit_Paste, MESHKIT_PT_copy_paste_geometry
from . import mesh_align
from .planar_uv import MeshKit_UV_Planar_Projection, MeshKit_UV_Load_Selection, MESHKIT_PT_planar_uv, MESHKIT_PT_planar_uv_advanced
from .point_array import MeshKit_Point_Grid, MeshKit_Point_Golden, MeshKit_Point_Pack, MeshKit_Import_Position_Data, MeshKit_Import_Volume_Field, MESHKIT_PT_point_array
from .radial_offset import MeshKit_Radial_Offset, MESHKIT_PT_radial_offset
from .segment_mesh import MeshKit_Segment_Mesh, meshkit_segment_mesh_preview, MESHKIT_PT_segment_mesh
from . import edit_attribute
from .vertex_quantize import MeshKit_Vertex_Quantize, MeshKit_UV_Quantize, MESHKIT_PT_vertex_quantize, MESHKIT_PT_uv_quantize



###########################################################################
# Global user preferences and UI rendering class

class MeshKitPreferences(bpy.types.AddonPreferences):
	bl_idname = __package__
	
	########## Copy Paste ##########
	
	def update_copypaste_category(self, context):
		category = bpy.context.preferences.addons[__package__].preferences.copypaste_category
		try:
			bpy.utils.unregister_class(MESHKIT_PT_copy_paste_geometry)
		except RuntimeError:
			pass
		if len(category) > 0:
			MESHKIT_PT_copy_paste_geometry.bl_category = category
			bpy.utils.register_class(MESHKIT_PT_copy_paste_geometry)
	
	copypaste_category: bpy.props.StringProperty(
		name="Copy Paste Panel",
		description="Choose a category for the panel to be placed in",
		default="Launch",
		update=update_copypaste_category)
		# Consider adding search_options=(list of currently available tabs) for easier operation
	
	########## Mesh Align ##########
	
	def update_meshalign_category(self, context):
		category = bpy.context.preferences.addons[__package__].preferences.meshalign_category
		try:
			bpy.utils.unregister_class(MESHKIT_PT_mesh_align_origin)
		except RuntimeError:
			pass
		if len(category) > 0:
			MESHKIT_PT_mesh_align_origin.bl_category = category
			bpy.utils.register_class(MESHKIT_PT_mesh_align_origin)
	
	meshalign_category: bpy.props.StringProperty(
		name="Mesh Align Panel",
		description="Choose a category for the panel to be placed in",
		default="Launch",
		update=update_meshalign_category)
		# Consider adding search_options=(list of currently available tabs) for easier operation
	
	########## Planar UV ##########
	
	def update_planaruv_category(self, context):
		category = bpy.context.preferences.addons[__package__].preferences.planaruv_category
		try:
			bpy.utils.unregister_class(MESHKIT_PT_planar_uv_advanced)
			bpy.utils.unregister_class(MESHKIT_PT_planar_uv)
		except RuntimeError:
			pass
		if len(category) > 0:
			MESHKIT_PT_planar_uv.bl_category = category
			bpy.utils.register_class(MESHKIT_PT_planar_uv)
			bpy.utils.register_class(MESHKIT_PT_planar_uv_advanced)
	
	planaruv_category: bpy.props.StringProperty(
		name="Planar UV Panel",
		description="Choose a category for the panel to be placed in",
		default="Launch",
		update=update_planaruv_category)
		# Consider adding search_options=(list of currently available tabs) for easier operation
	
	########## Point Array ##########
	
	def update_pointarray_category(self, context):
		category = bpy.context.preferences.addons[__package__].preferences.pointarray_category
		try:
			bpy.utils.unregister_class(MESHKIT_PT_point_array)
		except RuntimeError:
			pass
		if len(category) > 0:
			MESHKIT_PT_point_array.bl_category = category
			bpy.utils.register_class(MESHKIT_PT_point_array)
	
	pointarray_category: bpy.props.StringProperty(
		name="Point Array Panel",
		description="Choose a category for the panel to be placed in",
		default="Launch",
		update=update_pointarray_category)
		# Consider adding search_options=(list of currently available tabs) for easier operation
	
	########## Radial Offset ##########
	
	def update_radialoffset_category(self, context):
		category = bpy.context.preferences.addons[__package__].preferences.radialoffset_category
		try:
			bpy.utils.unregister_class(MESHKIT_PT_radial_offset)
		except RuntimeError:
			pass
		if len(category) > 0:
			MESHKIT_PT_radial_offset.bl_category = category
			bpy.utils.register_class(MESHKIT_PT_radial_offset)
	
	radialoffset_category: bpy.props.StringProperty(
		name="Radial Offset Panel",
		description="Choose a category for the panel to be placed in",
		default="Launch",
		update=update_radialoffset_category)
		# Consider adding search_options=(list of currently available tabs) for easier operation
	
	########## Segment Mesh ##########
	
	def update_segmentmesh_category(self, context):
		category = bpy.context.preferences.addons[__package__].preferences.segmentmesh_category
		try:
			bpy.utils.unregister_class(MESHKIT_PT_segment_mesh)
		except RuntimeError:
			pass
		if len(category) > 0:
			MESHKIT_PT_segment_mesh.bl_category = category
			bpy.utils.register_class(MESHKIT_PT_segment_mesh)
	
	segmentmesh_category: bpy.props.StringProperty(
		name="Segment Mesh Panel",
		description="Choose a category for the panel to be placed in",
		default="Launch",
		update=update_segmentmesh_category)
		# Consider adding search_options=(list of currently available tabs) for easier operation
	
	########## Edit Attribute ##########
	
	def update_editattribute_category(self, context):
		category = bpy.context.preferences.addons[__package__].preferences.editattribute_category
		try:
			bpy.utils.unregister_class(edit_attribute.MESHKIT_PT_edit_attribute)
		except RuntimeError:
			pass
		if len(category) > 0:
			MESHKIT_PT_copy_paste_geometry.bl_category = category
			bpy.utils.register_class(MESHKIT_PT_copy_paste_geometry)
			
	editattribute_category: bpy.props.StringProperty(
		name="Attribute Editor Panel",
		description="Choose a category for the panel to be placed in",
		default="Launch",
		update=update_editattribute_category)
		# Consider adding search_options=(list of currently available tabs) for easier operation
	
	########## Vertex Quantize ##########
	
	def update_vertexquantise_category(self, context):
		category = bpy.context.preferences.addons[__package__].preferences.vertexquantize_category
		try:
			bpy.utils.unregister_class(MESHKIT_PT_vertex_quantize)
		except RuntimeError:
			pass
		if len(category) > 0:
			MESHKIT_PT_vertex_quantize.bl_category = category
			bpy.utils.register_class(MESHKIT_PT_vertex_quantize)
	
	vertexquantize_category: bpy.props.StringProperty(
		name="Vertex Quantize Panel",
		description="Choose a category for the panel to be placed in",
		default="Launch",
		update=update_vertexquantise_category)
		# Consider adding search_options=(list of currently available tabs) for easier operation
	
	
	
	############################## Preferences UI ##############################
	
	# User Interface
	def draw(self, context):
		settings = context.scene.mesh_kit_settings
		
		layout = self.layout
#		layout.use_property_split = True
		
		########## Copy Paste ##########
		layout.label(text="Copy Paste", icon="PASTEDOWN") # COPYDOWN PASTEDOWN DUPLICATE
		layout.prop(self, "copypaste_category", text='Sidebar Tab')
		
		########## Mesh Align ##########
		layout.label(text="Mesh Align", icon="PIVOT_CURSOR") # PIVOT_CURSOR OBJECT_ORIGIN EMPTY_AXIS ORIENTATION_CURSOR PIVOT_BOUNDBOX MOD_WIREFRAME CUBE LIGHTPROBE_SPHERE
		layout.prop(self, "update_meshalign_category", text='Sidebar Tab')
		
		########## Planar UV ##########
		layout.separator(factor = 2.0)
		layout.label(text="Planar UV", icon="MOD_UVPROJECT") # UV UV_DATA GROUP_UVS MOD_UVPROJECT FACE_MAPS VIEW_ORTHO
		layout.prop(self, "planaruv_category", text='Sidebar Tab')
		
		########## Point Array ##########
		layout.separator(factor = 2.0)
		layout.label(text="Point Array", icon="GROUP_VERTEX") # GROUP_VERTEX SNAP_VERTEX OUTLINER_OB_POINTCLOUD OUTLINER_DATA_POINTCLOUD POINTCLOUD_DATA POINTCLOUD_POINT
		layout.prop(self, "pointarray_category", text='Sidebar Tab')
		
		########## Radial Offset ##########
		layout.separator(factor = 2.0)
		layout.label(text="Radial Offset", icon="SPHERE") # SPHERE PARTICLE_PATH PROP_ON PROP_CON
		layout.prop(self, "radialoffset_category", text='Sidebar Tab')
		
		########## Segment Mesh ##########
		layout.separator(factor = 2.0)
		layout.label(text="Segment Mesh", icon="MESH_GRID") # MESH_GRID GRID VIEW_ORTHO
		layout.prop(self, "segmentmesh_category", text='Sidebar Tab')
		
		########## Vertex Quantize ##########
		layout.separator(factor = 2.0)
		layout.label(text="Vertex Quantize", icon="UV_VERTEXSEL") # UV_VERTEXSEL NORMALS_VERTEX NORMALS_VERTEX_FACE SNAP_VERTEX
		layout.prop(self, "vertexquantize_category", text='Sidebar Tab')





###########################################################################
# Local project settings

class MeshKitSettings(bpy.types.PropertyGroup):
	
	
	
	########## Edit Attribute ##########
	
	def attribute_enum_items(self, context):
		"""
		Dynamic list of compatible attributes on the active mesh object.
	
		Only includes:
		- Domains: POINT (vertex), EDGE, FACE
		- Data types: FLOAT (value), FLOAT_VECTOR (vector), FLOAT_COLOR / BYTE_COLOR (color)
		"""
		items = []
		
		obj = getattr(context, "active_object", None) if context else None
		if not obj or obj.type != "MESH":
			return items
		
		mesh = obj.data
		
		for attr in mesh.attributes:
			if attr.domain not in {"POINT", "EDGE", "FACE"}:
				continue
			if attr.data_type not in {"FLOAT", "FLOAT_VECTOR", "FLOAT_COLOR", "BYTE_COLOR"}:
				continue
			# Identifier and name both use the attribute name.
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
			('DATA', 'Position Data (CSV/NPY)', 'Generates points from external files (CSV or NPY format) or internal text datablocks (CSV only)'),
			('FIELD', 'Volume Field (Unity 3D)', 'Generates points from an external VF format file')
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
	
	# Position Data import settings
	def textblocks_Enum(self,context):
		EnumItems = []
		i = 0
		for text in bpy.data.texts:
			EnumItems.append((str(i), text.name, text.lines[0].body))
			i += 1
		return EnumItems
	
	def set_data_file(self, value):
		file_path = Path(bpy.path.abspath(value))
		if file_path.is_file():
			if "csv" in file_path.suffix or "npy" in file_path.suffix:
				self["data_file"] = value
	
	def get_data_file(self):
		return self.get("data_file", bpy.context.scene.mesh_kit_settings.bl_rna.properties["data_file"].default)
	
	data_source: bpy.props.EnumProperty(
		name='Source',
		description='Create or replace object of same name, or replace currently selected object mesh data',
		items=[
			('EXT', 'External', 'Imports CSV or NPY format data from external file source'),
			('INT', 'Internal', 'Imports CSV format data from internal Blender text datablock')
			],
		default='EXT')
	data_text: bpy.props.EnumProperty(
		name = "Text",
		description = "Available text blocks",
		items = textblocks_Enum)
	data_file: bpy.props.StringProperty(
		name="File",
		description="Select external CSV or NPY data source file",
		default="",
		maxlen=4096,
		subtype="FILE_PATH",
		set=set_data_file,
		get=get_data_file)
	data_target: bpy.props.EnumProperty(
		name='Target',
		description='Create or replace object of same name, or replace currently selected object mesh data',
		items=[
			('SELECTED', 'Selected', 'Replaces currently selected object mesh data'),
			('NAME', 'Name', 'Creates or replaces an object of the same name as the data source')
			],
		default='SELECTED')
	
	# Volume Field import settings
	def set_field_file(self, value):
		file_path = Path(bpy.path.abspath(value))
		if file_path.is_file():
			if "vf" in file_path.suffix:
				self["field_file"] = value
	
	def get_field_file(self):
		return self.get("field_file", bpy.context.scene.mesh_kit_settings.bl_rna.properties["field_file"].default)
	
	field_file: bpy.props.StringProperty(
		name="File",
		description="Select external VF data source file",
		default="",
		maxlen=4096,
		subtype="FILE_PATH",
		set=set_field_file,
		get=get_field_file)
	field_target: bpy.props.EnumProperty(
		name='Target',
		description='Create or replace object of same name, or replace currently selected object mesh data',
		items=[
			('SELECTED', 'Selected', 'Replaces currently selected object mesh data'),
			('NAME', 'Name', 'Creates or replaces an object of the same name as the data source')
			],
		default='SELECTED')
	field_center: bpy.props.BoolProperty(
		name="Center",
		description="Aligns the imported data by total size instead of the lower right corner",
		default=True)
	
	
	
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
		update=meshkit_segment_mesh_preview)
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
		update=meshkit_segment_mesh_preview)
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
		update=meshkit_segment_mesh_preview)
	
	
	
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
# •Define keymap array
# •Registration function
# •Unregistration function

classes = (MeshKitPreferences, MeshKitSettings,
	MeshKit_Copy, MeshKit_Paste, MESHKIT_PT_copy_paste_geometry,
	MeshKit_UV_Planar_Projection, MeshKit_UV_Load_Selection, MESHKIT_PT_planar_uv, MESHKIT_PT_planar_uv_advanced,
	MeshKit_Point_Grid, MeshKit_Point_Golden, MeshKit_Point_Pack, MeshKit_Import_Position_Data, MeshKit_Import_Volume_Field, MESHKIT_PT_point_array,
	MeshKit_Radial_Offset, MESHKIT_PT_radial_offset,
	MeshKit_Segment_Mesh, MESHKIT_PT_segment_mesh,
	MeshKit_Vertex_Quantize, MeshKit_UV_Quantize, MESHKIT_PT_vertex_quantize, MESHKIT_PT_uv_quantize)

keymaps = []



def register():
	# Register classes
	for cls in classes:
		bpy.utils.register_class(cls)
	
	# Add extension settings reference
	bpy.types.Scene.mesh_kit_settings = bpy.props.PointerProperty(type=MeshKitSettings)
	
	########## Register Components ##########
	
	edit_attribute.register()
	mesh_align.register()
	
	# Add keymaps for project versioning and viewport shading
	wm = bpy.context.window_manager
	kc = wm.keyconfigs.addon
	if kc:
		
		########## Copy Paste ##########
		
		# Cut Windows
		km = wm.keyconfigs.addon.keymaps.new(name='3D View', space_type='VIEW_3D')
		kmi = km.keymap_items.new(MeshKit_Copy.bl_idname, 'X', 'PRESS', ctrl=True)
		kmi.properties.copy = False
		keymaps.append((km, kmi))
		
		# Cut MacOS
		km = wm.keyconfigs.addon.keymaps.new(name='3D View', space_type='VIEW_3D')
		kmi = km.keymap_items.new(MeshKit_Copy.bl_idname, 'X', 'PRESS', oskey=True)
		kmi.properties.copy = False
		keymaps.append((km, kmi))
		
		# Copy Windows
		km = wm.keyconfigs.addon.keymaps.new(name='3D View', space_type='VIEW_3D')
		kmi = km.keymap_items.new(MeshKit_Copy.bl_idname, 'C', 'PRESS', ctrl=True)
		kmi.properties.copy = True
		keymaps.append((km, kmi))
		
		# Copy MacOS
		km = wm.keyconfigs.addon.keymaps.new(name='3D View', space_type='VIEW_3D')
		kmi = km.keymap_items.new(MeshKit_Copy.bl_idname, 'C', 'PRESS', oskey=True)
		kmi.properties.copy = True
		keymaps.append((km, kmi))
		
		# Paste Windows
		km = wm.keyconfigs.addon.keymaps.new(name='3D View', space_type='VIEW_3D')
		kmi = km.keymap_items.new(MeshKit_Paste.bl_idname, 'V', 'PRESS', ctrl=True)
		keymaps.append((km, kmi))
		
		# Paste MacOS
		km = wm.keyconfigs.addon.keymaps.new(name='3D View', space_type='VIEW_3D')
		kmi = km.keymap_items.new(MeshKit_Paste.bl_idname, 'V', 'PRESS', oskey=True)
		keymaps.append((km, kmi))
		
		########## Radial Offset ##########
		
		# km = wm.keyconfigs.addon.keymaps.new(name='3D View', space_type='VIEW_3D')
		# kmi = km.keymap_items.new(MeshKit_Radial_Offset.bl_idname, type='Q', value='PRESS', shift=True)
		# keymaps.append((km, kmi))
		
		########## Vertex Quantize ##########
		
		# Quantize in 3D View
		km = wm.keyconfigs.addon.keymaps.new(name='3D View', space_type='VIEW_3D')
		kmi = km.keymap_items.new(MeshKit_Vertex_Quantize.bl_idname, type='Q', value='PRESS', shift=True)
		keymaps.append((km, kmi))
		
		# Quantize in UV Editor
		km = wm.keyconfigs.addon.keymaps.new(name='UV Editor', space_type='IMAGE_EDITOR')
		kmi = km.keymap_items.new(MeshKit_UV_Quantize.bl_idname, type='Q', value='PRESS', shift=True)
		keymaps.append((km, kmi))



def unregister():
	# Remove keymaps
	for km, kmi in keymaps:
		km.keymap_items.remove(kmi)
	keymaps.clear()
	
	# Remove extension settings reference
	del bpy.types.Scene.mesh_kit_settings
	
	########## Unregister Components ##########
	edit_attribute.unregister()
	mesh_align.unregister()
	
	# Deregister classes
	for cls in reversed(classes):
		bpy.utils.unregister_class(cls)



if __package__ == "__main__":
	register()
