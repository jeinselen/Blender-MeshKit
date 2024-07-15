import bpy
import bmesh
from mathutils import Vector

###########################################################################
# Main class

class MeshKit_UV_Planar_Projection(bpy.types.Operator):
	bl_idname = "ops.meshkit_uv_planar_projection"
	bl_label = "Set UV Map"
	bl_description = "Numerical planar projection of 3D meshes into UV space"
	bl_options = {'REGISTER', 'UNDO'}
	
	def execute(self, context):
		if not context.view_layer.objects.active.data.vertices:
			return {'CANCELLED'}
		
		# Set up local variables
		axis = context.scene.mesh_kit_settings.projection_axis
		world = True if context.scene.mesh_kit_settings.projection_space == "W" else False
		rotation = context.scene.mesh_kit_settings.projection_rotation
		flip = float(context.scene.mesh_kit_settings.projection_flip)
		align = float(context.scene.mesh_kit_settings.projection_align)
		centre = context.scene.mesh_kit_settings.projection_centre
		size = context.scene.mesh_kit_settings.projection_size
		
		# Prevent divide by zero errors
		size[0] = size[0] if size[0] > 0.0 else 1.0
		size[1] = size[1] if size[1] > 0.0 else 1.0
		size[2] = size[2] if size[2] > 0.0 else 1.0
		
		# Save current mode
		mode = context.active_object.mode
		# Switch to edit mode
		bpy.ops.object.mode_set(mode='EDIT')
		
		# Get object
		obj = context.active_object
		mat = obj.matrix_world
		bm = bmesh.from_edit_mesh(obj.data)
		# Get UV map
		uv_layer = bm.loops.layers.uv.verify()
		
		# Loop through faces
		U = 0.0
		V = 0.0
		for f in bm.faces:
			if f.select:
				for l in f.loops:
					# Process input coordinates
					# Use copy() to prevent changes to the source vertex coordinates
					pos = l.vert.co.copy()
					
					# Convert to world space if enabled
					if world:
						pos = mat @ pos
					
					pos[0] = (pos[0] - centre[0]) / size[0]
					pos[1] = (pos[1] - centre[1]) / size[1]
					pos[2] = (pos[2] - centre[2]) / size[2]
					
					# Projection Axis
					if axis == "X":
						U = pos[1]
						V = pos[2]
					elif axis == "Y":
						U = pos[0]
						V = pos[2]
					else: # axis == "Z"
						U = pos[0]
						V = pos[1]
					
					# Projection Rotation
					if "YX" in rotation:
						U, V = V, U
						U *= -1.0
					if "-" in rotation:
						U *= -1.0
						V *= -1.0
					
					# Projection Flip
					U *= flip
					
					# Set UV map values with image centre or zero point alignment
					l[uv_layer].uv = (U + align, V + align)
		
		# Update mesh
		bmesh.update_edit_mesh(obj.data)
		
		# Reset object mode to original
		bpy.ops.object.mode_set(mode=mode)
		
		# Done
		return {'FINISHED'}

class MeshKit_UV_Load_Selection(bpy.types.Operator):
	bl_idname = "ops.meshkit_uv_load_selection"
	bl_label = "Load Selection Settings"
	bl_description = "Set the Centre and Size variables to the bounding box of the selected geometry"
	bl_options = {'REGISTER', 'UNDO'}
	
	def execute(self, context):
		if not context.view_layer.objects.active.data.vertices:
			return {'CANCELLED'}
		
		# Save current mode
		mode = context.active_object.mode
		# Switch to edit mode
		bpy.ops.object.mode_set(mode='EDIT')
		
		# Get object data
		obj = context.active_object
		mat = obj.matrix_world
		mesh = bmesh.from_edit_mesh(obj.data)
		
		# Loop through selected vertices and find the minimum/maximum positions
		min_co = Vector((float("inf"), float("inf"), float("inf")))
		max_co = Vector((float("-inf"), float("-inf"), float("-inf")))
		for vert in mesh.verts:
			if vert.select:
				min_co.x = min(min_co.x, vert.co.x)
				min_co.y = min(min_co.y, vert.co.y)
				min_co.z = min(min_co.z, vert.co.z)
				max_co.x = max(max_co.x, vert.co.x)
				max_co.y = max(max_co.y, vert.co.y)
				max_co.z = max(max_co.z, vert.co.z)
		
		# Convert to world space if enabled
		if context.scene.mesh_kit_settings.projection_space == "W":
			min_co = mat @ min_co
			max_co = mat @ max_co
		
		# Calculate bounding box and centre point
		centr = (min_co + max_co) * 0.5
		max_co = max_co - min_co
		
		# Prevent zero scale entries
		if max_co.x == 0:
			max_co.x = 1.0
		if max_co.y == 0:
			max_co.y = 1.0
		if max_co.z == 0:
			max_co.z = 1.0
		
		# Set local variables
		context.scene.mesh_kit_settings.projection_centre = centr
		context.scene.mesh_kit_settings.projection_size = max_co
		
		# Reset object mode to original
		bpy.ops.object.mode_set(mode=mode)
		
		# Done
		return {'FINISHED'}

###########################################################################
# UI rendering classes

class MESHKIT_PT_planar_uv(bpy.types.Panel):
	bl_idname = "MESHKIT_PT_planar_uv"
	bl_label = "Planar UV"
	bl_space_type = "VIEW_3D"
	bl_region_type = "UI"
	bl_category = "Launch"
	bl_order = 10
	bl_options = {'DEFAULT_CLOSED'}
	
	@classmethod
	def poll(cls, context):
		return True
	
	def draw_header(self, context):
		try:
			layout = self.layout
		except Exception as exc:
			print(str(exc) + " | Error in Mesh Kit Planar UV panel header")
	
	def draw(self, context):
		try:
			layout = self.layout
			layout.use_property_split = True
			layout.use_property_decorate = False # No animation
			layout.prop(context.scene.mesh_kit_settings, 'projection_axis', expand=True)
			
			col = layout.column()
			col.prop(context.scene.mesh_kit_settings, 'projection_centre')
			col = layout.column()
			col.prop(context.scene.mesh_kit_settings, 'projection_size')
			
			layout.prop(context.scene.mesh_kit_settings, 'projection_space', expand=True)
			
			button = layout.row()
			if not (context.view_layer.objects.active and context.view_layer.objects.active.type == "MESH"):
				button.active = False
				button.enabled = False
			button.operator(MeshKit_UV_Planar_Projection.bl_idname, icon="GROUP_UVS")
		except Exception as exc:
			print(str(exc) + " | Error in Mesh Kit Planar UV panel")

class MESHKIT_PT_planar_uv_advanced(bpy.types.Panel):
	bl_idname = "MESHKIT_PT_planar_uv_advanced"
	bl_label = "Advanced"
	bl_space_type = "VIEW_3D"
	bl_region_type = "UI"
	bl_parent_id = "MESHKIT_PT_planar_uv"
	bl_options = {'DEFAULT_CLOSED'}
	
	@classmethod
	def poll(cls, context):
		return True
	
	def draw_header(self, context):
		try:
			layout = self.layout
		except Exception as exc:
			print(str(exc) + " | Error in Mesh Kit Planar UV Advanced panel header")
	
	def draw(self, context):
		try:
			layout = self.layout
			layout.use_property_split = True
			layout.use_property_decorate = False # No animation
			
			button = layout.row()
			if not (context.view_layer.objects.active and context.view_layer.objects.active.type == "MESH"):
				button.active = False
				button.enabled = False
			button.operator(MeshKit_UV_Load_Selection.bl_idname, icon="SHADING_BBOX")
			
			layout.prop(context.scene.mesh_kit_settings, 'projection_rotation', expand=True)
			layout.prop(context.scene.mesh_kit_settings, 'projection_flip', expand=True)
			layout.prop(context.scene.mesh_kit_settings, 'projection_align', expand=True)
		except Exception as exc:
			print(str(exc) + " | Error in Mesh Kit Planar UV Advanced panel")
			