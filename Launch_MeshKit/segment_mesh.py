import bpy
import bmesh
from mathutils import Vector
from mathutils import Matrix
from bpy.app.handlers import persistent

###########################################################################
# Main class

class MeshKit_Segment_Mesh(bpy.types.Operator):
	bl_idname = "object.meshkit_segment_mesh"
	bl_label = "Segment Mesh"
	bl_description = "Divide large meshes into grid-based components for more efficient rendering in realtime game engines"
	bl_options = {'REGISTER', 'UNDO'}
	
	def invoke(self, context, event):
		return context.window_manager.invoke_props_dialog(self)
	
	def draw(self, context):
		try:
			layout = self.layout
			layout.label(text="Blender will be unresponsive while processing, proceed?")
		except Exception as exc:
			print(str(exc) + ' | Error in Mesh Kit Segment Mesh: Begin segmentation confirmation')
	
	def execute(self, context):
		# Set up local variables
		sizeX = context.scene.mesh_kit_settings.tile_size[0]
		sizeY = context.scene.mesh_kit_settings.tile_size[1]
		countX = context.scene.mesh_kit_settings.tile_count[0]
		countY = context.scene.mesh_kit_settings.tile_count[1]
		startX = sizeX * float(countX) * -0.5
		startY = sizeY * float(countY) * -0.5
		segment = context.scene.mesh_kit_settings.tile_segment
		origin = context.scene.mesh_kit_settings.tile_origin
		bounds = True if context.scene.mesh_kit_settings.tile_bounds == "OUT" else False
		attribute_name = "island_position"
		
		# Get active object by name instead of by active reference (so the source object doesn't change during processing)
		object_name = str(context.active_object.name)
		mesh_object = bpy.data.objects[object_name]
		
		# Deselect all
		bpy.ops.object.mode_set(mode='EDIT')
		bpy.ops.mesh.select_all(action='DESELECT')
		bpy.ops.object.mode_set(mode='OBJECT')
		
		# Apply all transforms (otherwise world-space calculations are going to be all off)
		bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
		
		# May need to apply all modifiers if significant changes are made to the geometry via modifiers
#		bpy.ops.object.apply_all_modifiers()
		
		# Calculate island positions using Geometry Nodes (more than hundreds of times faster than manual BMesh calculation)
		if segment != "POLY":
			mod = mesh_object.modifiers.new(name="MeshKit-StoreIslandAttributes-TEMP", type='NODES')
			mod.node_group = store_island_attributes_node_group()
			bpy.ops.object.modifier_apply(modifier="MeshKit-StoreIslandAttributes-TEMP")
			bpy.data.node_groups.remove(bpy.data.node_groups["MeshKit-StoreIslandAttributes-TEMP"])
		
		# Save current 3D cursor location and pivot point
		original_cursor = context.scene.cursor.matrix
		original_pivot = context.tool_settings.transform_pivot_point
		
		# Track names of each created object
		separated_collection = []
		
		# Loop through each grid space
		for x in range(countX):
			# Define min/max for X
			min_x = startX + (x * sizeX)
			max_x = min_x + sizeX
			loc_x = (max_x + min_x) / 2
			if bounds:
				if x == 0:
					min_x = float('-inf')
				elif x == countX-1:
					max_x = float('inf')
			
			for y in range(countY):
				# Define min/max for Y
				min_y = startY + (y * sizeY)
				max_y = min_y + sizeY
				loc_y = (max_y + min_y) / 2
				if bounds:
					if y == 0:
						min_y = float('-inf')
					elif y == countY-1:
						max_y = float('inf')
				
				# Prevent out-of-range errors (seems like the attribute indices aren't updated after splitting geometry)
				mesh_object.data.update()
				
				# Re-get the mesh data to ensure everything is up-to-date
				mesh_data = mesh_object.data
				
				# Get attribute data if needed
				if segment == "AVERAGE":
					island_info = "island_mean"
				elif segment == "WEIGHTED":
					island_info = "island_weighted"
				else:
					island_info = False
				
				# Create tile name
				tile_name = mesh_object.name + "-Tile-" + str(x) + "-" + str(y)
				
				# Count how many polygons have been selected
				count = 0
				
				# Select polygons within the specified XYZ area
				for polygon in mesh_data.polygons:
					if island_info:
						# Get precalculated island position
						element_position = mesh_data.attributes[island_info].data[polygon.index].vector
					else:
						# Find average vertex location of individual polygon
						element_position = Vector((0, 0, 0))
						for vertice_index in polygon.vertices:
							element_position += mesh_data.vertices[vertice_index].co
						element_position /= len(polygon.vertices)
					
					# Check element position against min/max
					if min_x <= element_position.x <= max_x and min_y <= element_position.y <= max_y:
						polygon.select = True
						count += 1
				
				# Only create a new segment if there are 1 or more polygons selected
				if count > 0:
					# Separate selected polygons into a new object
					context.view_layer.objects.active = mesh_object
					mesh_object.select_set(True)
					bpy.ops.object.mode_set(mode='EDIT')
					bpy.ops.mesh.separate(type='SELECTED')
					bpy.ops.object.mode_set(mode='OBJECT')
					
					# Rename the separated object and mesh
					separated_object = context.selected_objects[1]
					separated_object.name = tile_name
					separated_mesh = separated_object.data
					separated_mesh.name = tile_name
					separated_object.select_set(False)
					separated_collection.append(tile_name)
					
					# Apply transforms, set the origin, and set the position of the separated object
					with context.temp_override(
							active_object=separated_object,
							editable_objects=[separated_object],
							object=separated_object,
							selectable_objects=[separated_object],
							selected_editable_objects=[separated_object],
							selected_objects=[separated_object]):
						
						if origin == "TILE":
							context.scene.cursor.matrix = Matrix(((1.0, 0.0, 0.0, loc_x),(0.0, 1.0, 0.0, loc_y),(-0.0, 0.0, 1.0, 0.0),(0.0, 0.0, 0.0, 1.0)))
							bpy.ops.object.origin_set(type='ORIGIN_CURSOR')
						elif origin == "BOX":
							context.tool_settings.transform_pivot_point = "BOUNDING_BOX_CENTER"
							bpy.ops.object.origin_set(type='ORIGIN_GEOMETRY')
						elif origin == "MEDIAN":
							context.tool_settings.transform_pivot_point = "MEDIAN_POINT"
							bpy.ops.object.origin_set(type='ORIGIN_GEOMETRY')
						elif origin == "MASS":
							bpy.ops.object.origin_set(type='ORIGIN_CENTER_OF_MASS')
						elif origin == "VOLUME":
							bpy.ops.object.origin_set(type='ORIGIN_CENTER_OF_VOLUME')
		
		# Select all newly created segments
		for name in separated_collection:
			bpy.data.objects[name].select_set(True)
		
		# If no elements remain in the original source, remove it and set the first tile to active
		if len(mesh_object.data.vertices) == 0:
			bpy.data.meshes.remove(mesh_object.data)
			context.view_layer.objects.active = bpy.data.objects[separated_collection[0]]
		
		# Restore original 3D cursor position and pivot point
		context.scene.cursor.matrix = original_cursor
		context.tool_settings.transform_pivot_point = original_pivot
		
		# Done
		return {'FINISHED'}



# Many thanks to Brendan Parmer for making this easy https://github.com/BrendanParmer/NodeToPython
@persistent
def store_island_attributes_node_group():
	store_island_attributes= bpy.data.node_groups.new(type = 'GeometryNodeTree', name = "MeshKit-StoreIslandAttributes-TEMP")
	
	#initialize store_island_attributes nodes
	#store_island_attributes outputs
	#output Geometry
	store_island_attributes.outputs.new('NodeSocketGeometry', "Geometry")
	store_island_attributes.outputs[0].attribute_domain = 'POINT'
	
	
	#node Group Output
	group_output = store_island_attributes.nodes.new("NodeGroupOutput")
	
	#store_island_attributes inputs
	#input Geometry
	store_island_attributes.inputs.new('NodeSocketGeometry', "Geometry")
	store_island_attributes.inputs[0].attribute_domain = 'POINT'
	
	
	#node Group Input
	group_input = store_island_attributes.nodes.new("NodeGroupInput")
	
	#node Mesh Island
	mesh_island = store_island_attributes.nodes.new("GeometryNodeInputMeshIsland")
	
	#node Position
	position = store_island_attributes.nodes.new("GeometryNodeInputPosition")
	
	#node Face Area
	face_area = store_island_attributes.nodes.new("GeometryNodeInputMeshFaceArea")
	
	#node Accumulate Field
	accumulate_field = store_island_attributes.nodes.new("GeometryNodeAccumulateField")
	accumulate_field.data_type = 'FLOAT_VECTOR'
	accumulate_field.domain = 'POINT'
	#Value Float
	accumulate_field.inputs[1].default_value = 1.0
	#Value Int
	accumulate_field.inputs[2].default_value = 1
	
	#node Accumulate Field.001
	accumulate_field_001 = store_island_attributes.nodes.new("GeometryNodeAccumulateField")
	accumulate_field_001.data_type = 'INT'
	accumulate_field_001.domain = 'POINT'
	#Value Vector
	accumulate_field_001.inputs[0].default_value = (1.0, 1.0, 1.0)
	#Value Float
	accumulate_field_001.inputs[1].default_value = 1.0
	#Value Int
	accumulate_field_001.inputs[2].default_value = 1
	
	#node Accumulate Field.002
	accumulate_field_002 = store_island_attributes.nodes.new("GeometryNodeAccumulateField")
	accumulate_field_002.data_type = 'FLOAT_VECTOR'
	accumulate_field_002.domain = 'FACE'
	#Value Float
	accumulate_field_002.inputs[1].default_value = 1.0
	#Value Int
	accumulate_field_002.inputs[2].default_value = 1
	
	#node Accumulate Field.003
	accumulate_field_003 = store_island_attributes.nodes.new("GeometryNodeAccumulateField")
	accumulate_field_003.data_type = 'FLOAT'
	accumulate_field_003.domain = 'FACE'
	#Value Vector
	accumulate_field_003.inputs[0].default_value = (1.0, 1.0, 1.0)
	#Value Int
	accumulate_field_003.inputs[2].default_value = 1
	
	#node Vector Math
	vector_math = store_island_attributes.nodes.new("ShaderNodeVectorMath")
	vector_math.operation = 'DIVIDE'
	#Vector_002
	vector_math.inputs[2].default_value = (0.0, 0.0, 0.0)
	#Scale
	vector_math.inputs[3].default_value = 1.0
	
	#node Vector Math.001
	vector_math_001 = store_island_attributes.nodes.new("ShaderNodeVectorMath")
	vector_math_001.operation = 'SCALE'
	#Vector_001
	vector_math_001.inputs[1].default_value = (0.0, 0.0, 0.0)
	#Vector_002
	vector_math_001.inputs[2].default_value = (0.0, 0.0, 0.0)
	
	#node Vector Math.002
	vector_math_002 = store_island_attributes.nodes.new("ShaderNodeVectorMath")
	vector_math_002.operation = 'DIVIDE'
	#Vector_002
	vector_math_002.inputs[2].default_value = (0.0, 0.0, 0.0)
	#Scale
	vector_math_002.inputs[3].default_value = 1.0
	
	#node Store Named Attribute
	store_named_attribute = store_island_attributes.nodes.new("GeometryNodeStoreNamedAttribute")
	store_named_attribute.data_type = 'INT'
	store_named_attribute.domain = 'FACE'
	#Selection
	store_named_attribute.inputs[1].default_value = True
	#Name
	store_named_attribute.inputs[2].default_value = "island_index"
	#Value_Vector
	store_named_attribute.inputs[3].default_value = (0.0, 0.0, 0.0)
	#Value_Float
	store_named_attribute.inputs[4].default_value = 0.0
	#Value_Color
	store_named_attribute.inputs[5].default_value = (0.0, 0.0, 0.0, 0.0)
	#Value_Bool
	store_named_attribute.inputs[6].default_value = False
	
	#node Store Named Attribute.002
	store_named_attribute_002 = store_island_attributes.nodes.new("GeometryNodeStoreNamedAttribute")
	store_named_attribute_002.data_type = 'FLOAT_VECTOR'
	store_named_attribute_002.domain = 'FACE'
	#Selection
	store_named_attribute_002.inputs[1].default_value = True
	#Name
	store_named_attribute_002.inputs[2].default_value = "island_mean"
	#Value_Float
	store_named_attribute_002.inputs[4].default_value = 0.0
	#Value_Color
	store_named_attribute_002.inputs[5].default_value = (0.0, 0.0, 0.0, 0.0)
	#Value_Bool
	store_named_attribute_002.inputs[6].default_value = False
	#Value_Int
	store_named_attribute_002.inputs[7].default_value = 0
	
	#node Store Named Attribute.003
	store_named_attribute_003 = store_island_attributes.nodes.new("GeometryNodeStoreNamedAttribute")
	store_named_attribute_003.data_type = 'FLOAT_VECTOR'
	store_named_attribute_003.domain = 'FACE'
	#Selection
	store_named_attribute_003.inputs[1].default_value = True
	#Name
	store_named_attribute_003.inputs[2].default_value = "island_weighted"
	#Value_Float
	store_named_attribute_003.inputs[4].default_value = 0.0
	#Value_Color
	store_named_attribute_003.inputs[5].default_value = (0.0, 0.0, 0.0, 0.0)
	#Value_Bool
	store_named_attribute_003.inputs[6].default_value = False
	#Value_Int
	store_named_attribute_003.inputs[7].default_value = 0
	
	
	#Set locations
	group_output.location = (0.0, 0.0)
	group_input.location = (-720.0, 0.0)
	mesh_island.location = (-720.0, -100.0)
	position.location = (-900.0, -220.0)
	face_area.location = (-1080.0, -720.0)
	accumulate_field.location = (-720.0, -220.0)
	accumulate_field_001.location = (-720.0, -440.0)
	accumulate_field_002.location = (-720.0, -660.0)
	accumulate_field_003.location = (-720.0, -880.0)
	vector_math.location = (-540.0, -220.0)
	vector_math_001.location = (-900.0, -660.0)
	vector_math_002.location = (-540.0, -660.0)
	store_named_attribute.location = (-540.0, 0.0)
	store_named_attribute_002.location = (-360.0, 0.0)
	store_named_attribute_003.location = (-180.0, 0.0)
	
	#Set dimensions
	group_output.width, group_output.height = 140.0, 100.0
	group_input.width, group_input.height = 140.0, 100.0
	mesh_island.width, mesh_island.height = 140.0, 100.0
	position.width, position.height = 140.0, 100.0
	face_area.width, face_area.height = 140.0, 100.0
	accumulate_field.width, accumulate_field.height = 140.0, 100.0
	accumulate_field_001.width, accumulate_field_001.height = 140.0, 100.0
	accumulate_field_002.width, accumulate_field_002.height = 140.0, 100.0
	accumulate_field_003.width, accumulate_field_003.height = 140.0, 100.0
	vector_math.width, vector_math.height = 140.0, 100.0
	vector_math_001.width, vector_math_001.height = 140.0, 100.0
	vector_math_002.width, vector_math_002.height = 140.0, 100.0
	store_named_attribute.width, store_named_attribute.height = 140.0, 100.0
	store_named_attribute_002.width, store_named_attribute_002.height = 140.0, 100.0
	store_named_attribute_003.width, store_named_attribute_003.height = 140.0, 100.0
	
	#initialize store_island_attributes links
	#store_named_attribute_003.Geometry -> group_output.Geometry
	store_island_attributes.links.new(store_named_attribute_003.outputs[0], group_output.inputs[0])
	#face_area.Area -> accumulate_field_003.Value
	store_island_attributes.links.new(face_area.outputs[0], accumulate_field_003.inputs[1])
	#vector_math_001.Vector -> accumulate_field_002.Value
	store_island_attributes.links.new(vector_math_001.outputs[0], accumulate_field_002.inputs[0])
	#accumulate_field_002.Total -> vector_math_002.Vector
	store_island_attributes.links.new(accumulate_field_002.outputs[6], vector_math_002.inputs[0])
	#accumulate_field_003.Total -> vector_math_002.Vector
	store_island_attributes.links.new(accumulate_field_003.outputs[7], vector_math_002.inputs[1])
	#accumulate_field.Total -> vector_math.Vector
	store_island_attributes.links.new(accumulate_field.outputs[6], vector_math.inputs[0])
	#accumulate_field_001.Total -> vector_math.Vector
	store_island_attributes.links.new(accumulate_field_001.outputs[8], vector_math.inputs[1])
	#face_area.Area -> vector_math_001.Scale
	store_island_attributes.links.new(face_area.outputs[0], vector_math_001.inputs[3])
	#position.Position -> accumulate_field.Value
	store_island_attributes.links.new(position.outputs[0], accumulate_field.inputs[0])
	#group_input.Geometry -> store_named_attribute.Geometry
	store_island_attributes.links.new(group_input.outputs[0], store_named_attribute.inputs[0])
	#store_named_attribute.Geometry -> store_named_attribute_002.Geometry
	store_island_attributes.links.new(store_named_attribute.outputs[0], store_named_attribute_002.inputs[0])
	#store_named_attribute_002.Geometry -> store_named_attribute_003.Geometry
	store_island_attributes.links.new(store_named_attribute_002.outputs[0], store_named_attribute_003.inputs[0])
	#mesh_island.Island Index -> store_named_attribute.Value
	store_island_attributes.links.new(mesh_island.outputs[0], store_named_attribute.inputs[7])
	#vector_math.Vector -> store_named_attribute_002.Value
	store_island_attributes.links.new(vector_math.outputs[0], store_named_attribute_002.inputs[3])
	#vector_math_002.Vector -> store_named_attribute_003.Value
	store_island_attributes.links.new(vector_math_002.outputs[0], store_named_attribute_003.inputs[3])
	#mesh_island.Island Index -> accumulate_field.Group ID
	store_island_attributes.links.new(mesh_island.outputs[0], accumulate_field.inputs[3])
	#mesh_island.Island Index -> accumulate_field_001.Group ID
	store_island_attributes.links.new(mesh_island.outputs[0], accumulate_field_001.inputs[3])
	#mesh_island.Island Index -> accumulate_field_002.Group ID
	store_island_attributes.links.new(mesh_island.outputs[0], accumulate_field_002.inputs[3])
	#mesh_island.Island Index -> accumulate_field_003.Group ID
	store_island_attributes.links.new(mesh_island.outputs[0], accumulate_field_003.inputs[3])
	#position.Position -> vector_math_001.Vector
	store_island_attributes.links.new(position.outputs[0], vector_math_001.inputs[0])
	return store_island_attributes



@persistent
def meshkit_segment_mesh_preview(self, context):
	mesh_name = "MeshKit-SegmentMeshPreview-TEMP"
	
	# Remove existing mesh data block (and associated object) if it exists
	if mesh_name in bpy.data.meshes:
		bpy.data.meshes.remove(bpy.data.meshes[mesh_name])
	
	# Stop now if the preview mesh is disabled
	if not context.scene.mesh_kit_settings.show_preview:
		# Done
		return None
	
	# Set up local variables
	sizeX = context.scene.mesh_kit_settings.tile_size[0]
	sizeY = context.scene.mesh_kit_settings.tile_size[1]
	countX = context.scene.mesh_kit_settings.tile_count[0]
	countY = context.scene.mesh_kit_settings.tile_count[1]
	
	# Save the current object selection
	active_object_name = str(context.active_object.name) if context.active_object else False
	selected_objects = [obj for obj in context.selected_objects]
	
	# Create primitive grid
	bpy.ops.mesh.primitive_grid_add(
		x_subdivisions=countX,
		y_subdivisions=countY,
		size=1,
		enter_editmode=False,
		align='WORLD',
		location=(0.0, 0.0, 0.0),
		rotation=(0.0, 0.0, 0.0),
		scale=(sizeX * countX, sizeY * countY, 1.0))
	
	# Set scale
	context.active_object.scale = (sizeX * countX, sizeY * countY, 1.0)
	bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
	
	# Convert to wireframe and disable for rendering
	bpy.ops.object.modifier_add(type='WIREFRAME')
	context.object.modifiers["Wireframe"].thickness = float(max(sizeX, sizeY)) * 0.05
#	bpy.ops.object.modifier_apply()
	context.object.hide_render = True
		
	# Rename object and mesh data block
	context.active_object.name = mesh_name
	context.active_object.data.name = mesh_name
	
	# Reset selection
	context.active_object.select_set(False)
	if active_object_name:
		context.view_layer.objects.active = bpy.data.objects[active_object_name]
	# If one or more objects were originally selected, restore that selection set
	if len(selected_objects) >= 1:
		# Re-select previously selected objects
		for obj in selected_objects:
			obj.select_set(True)
	
	# Done
	return None



###########################################################################
# UI rendering class

class MESHKIT_PT_segment_mesh(bpy.types.Panel):
	bl_space_type = "VIEW_3D"
	bl_region_type = "UI"
	bl_category = "Launch"
	bl_order = 20
	bl_options = {'DEFAULT_CLOSED'}
	bl_label = "Segment Mesh"
	bl_idname = "MESHKIT_PT_segment_mesh"
	
	@classmethod
	def poll(cls, context):
		return True
	
	def draw_header(self, context):
		try:
			layout = self.layout
		except Exception as exc:
			print(str(exc) + " | Error in Mesh Kit Segment Mesh panel header")
			
	def draw(self, context):
		try:
			# Check if mesh object is selected
			if context.active_object and context.active_object.type == 'MESH' and len(context.active_object.data.polygons) > 0:
				button_enable = True
				button_title = "Create " + str(context.scene.mesh_kit_settings.tile_count[0] * context.scene.mesh_kit_settings.tile_count[1]) + " Segments"
				button_icon = "MESH_GRID"
			else:
				button_enable = False
				button_title = "Select Mesh"
				button_icon = "OUTLINER_DATA_MESH"
			
			# UI Layout
			layout = self.layout
			layout.use_property_decorate = False # No animation
			layout.use_property_split = True
			
			layout.prop(context.scene.mesh_kit_settings, 'tile_size')
			layout.prop(context.scene.mesh_kit_settings, 'tile_count')
			col = layout.column(align=True)
			col.prop(context.scene.mesh_kit_settings, 'tile_bounds')
			col.prop(context.scene.mesh_kit_settings, 'tile_segment')
			col.prop(context.scene.mesh_kit_settings, 'tile_origin')
			layout.prop(context.scene.mesh_kit_settings, 'show_preview')
						
			if button_enable:
				layout.operator(MeshKit_Segment_Mesh.bl_idname, text = button_title, icon = button_icon)
			else:
				disabled = layout.row()
				disabled.active = False
				disabled.enabled = False
				disabled.operator(MeshKit_Segment_Mesh.bl_idname, text = button_title, icon = button_icon)
			
		except Exception as exc:
			print(str(exc) + " | Error in Mesh Kit Segment Mesh panel")
