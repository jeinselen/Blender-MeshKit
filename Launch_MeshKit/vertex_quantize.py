import bpy

###########################################################################
# Main class

class MeshKit_Vertex_Quantize(bpy.types.Operator):
	bl_idname = "ops.meshkit_vertex_quantize"
	bl_label = "Vertex Quantize"
	bl_description = "Snap vertices to custom quantization steps"
	bl_options = {'REGISTER', 'UNDO'}
	
	def execute(self, context):
		if not context.active_object.data.vertices:
			print("Error in Mesh Kit Vertex Quantize operation (vertex data not available)")
			return {'FINISHED'}
		
		# Set up local variables
		if context.scene.mesh_kit_settings.vert_dimensions == 'True':
			quantX = quantY = quantZ = context.scene.mesh_kit_settings.vert_uniform
		else:
			quantX = context.scene.mesh_kit_settings.vert_xyz[0] # X quantization
			quantY = context.scene.mesh_kit_settings.vert_xyz[1] # Y quantization
			quantZ = context.scene.mesh_kit_settings.vert_xyz[2] # Z quantization
		
		# Get current mode and save it
		mode = context.active_object.mode
		
		# Switch to object mode
		bpy.ops.object.mode_set(mode='OBJECT')
		
		# Get selected vertices
		selectedVerts = [v for v in context.active_object.data.vertices if v.select]
		
		# Process vertices
		for vert in selectedVerts:
			new_location = vert.co
			if quantX > 0.0:
				new_location[0] = round(new_location[0] / quantX) * quantX
			if quantY > 0.0:
				new_location[1] = round(new_location[1] / quantY) * quantY
			if quantZ > 0.0:
				new_location[2] = round(new_location[2] / quantZ) * quantZ
			vert.co = new_location
		
		# Reset mode to original
		bpy.ops.object.mode_set(mode=mode)
		
		# Done
		return {'FINISHED'}

class MeshKit_UV_Quantize(bpy.types.Operator):
	bl_idname = "ops.meshkit_uv_quantize"
	bl_label = "UV Quantize"
	bl_description = "Snap UV points to custom quantization steps"
	bl_options = {'REGISTER', 'UNDO'}
	
	def execute(self, context):
		if not context.active_object.data:
			print("Error in Mesh Kit UV Quantize operation (UV data not available)")
			return {'FINISHED'}
		
		# Set up local variables
		if context.scene.mesh_kit_settings.uv_type == 'DIV':
			if context.scene.mesh_kit_settings.uv_dimensions == 'True':
				quantX = quantY = float(context.scene.mesh_kit_settings.uv_div_uniform)
			else:
				quantX = float(context.scene.mesh_kit_settings.uv_div[0]) # X quantization
				quantY = float(context.scene.mesh_kit_settings.uv_div[1]) # Y quantization
		else:
			if context.scene.mesh_kit_settings.uv_dimensions == 'True':
				quantX = quantY = float(context.scene.mesh_kit_settings.uv_val_uniform)
			else:
				quantX = context.scene.mesh_kit_settings.uv_val[0] # X quantization
				quantY = context.scene.mesh_kit_settings.uv_val[1] # Y quantization
		
		# Get current mode and save it
		mode = context.active_object.mode
		
		# Switch to object mode
		bpy.ops.object.mode_set(mode='OBJECT')
		
		# Get object and active UV layer
		obj = context.active_object.data
		uv_layer = obj.uv_layers.active.data
		
		# Iterate over every polygon
		for poly in obj.polygons:
			
			# Iterate over every loop
			for loop_index in poly.loop_indices:
				
				# If selected
				if uv_layer[loop_index].select:
					uv = uv_layer[loop_index].uv
					# If the quantization is defined in divisions
					if context.scene.mesh_kit_settings.uv_type == 'DIV':
						# Only process if a value greater than zero is provided
						if quantX > 0.0:
							uv.x = round(uv.x * quantX) / quantX
						if quantY > 0.0:
							uv.y = round(uv.y * quantY) / quantY
					# If the quantization is defined in units
					else:
						# Only process if a value greater than zero is provided
						if quantX > 0.0:
							uv.x = round(uv.x / quantX) * quantX
						if quantY > 0.0:
							uv.y = round(uv.y / quantY) * quantY
		
		# Reset mode to original
		bpy.ops.object.mode_set(mode=mode)
		
		# Done
		return {'FINISHED'}

###########################################################################
# UI rendering classes

class MESHKIT_PT_vertex_quantize(bpy.types.Panel):
	bl_space_type = "VIEW_3D"
	bl_region_type = "UI"
	bl_category = "Launch"
	bl_order = 8
	bl_options = {'DEFAULT_CLOSED'}
	bl_label = "Vertex Quantize"
	bl_idname = "MESHKIT_PT_vertex_quantize"
	
	@classmethod
	def poll(cls, context):
		if context.area.ui_type == 'VIEW_3D' and context.active_object and context.active_object.type == 'MESH':
			return True
		return False
	
	def draw_header(self, context):
		try:
			layout = self.layout
		except Exception as exc:
			print(str(exc) + " | Error in Mesh Kit Vertex Quantize panel header")
	
	def draw(self, context):
		try:
			layout = self.layout
			layout.use_property_decorate = False # No animation
			
			# Display settings
			col = layout.column(align=True)
			row = col.row(align=True)
			row.prop(context.scene.mesh_kit_settings, 'vert_dimensions', expand=True)
			if context.scene.mesh_kit_settings.vert_dimensions == 'True':
				col.prop(context.scene.mesh_kit_settings, 'vert_uniform', text='')
			else:
				row = col.row(align=True)
				row.prop(context.scene.mesh_kit_settings, 'vert_xyz', text='')
			
			# Display button
			layout.operator(MeshKit_Vertex_Quantize.bl_idname)
		except Exception as exc:
			print(str(exc) + " | Error in Mesh Kit Vertex Quantize panel")

class MESHKIT_PT_uv_quantize(bpy.types.Panel):
	bl_space_type = "IMAGE_EDITOR"
	bl_region_type = "UI"
	bl_category = 'Image'
	bl_order = 10
	bl_options = {'DEFAULT_CLOSED'}
	bl_label = "UV Quantize"
	bl_idname = "MESHKIT_PT_uv_quantize"
	
	@classmethod
	def poll(cls, context):
		if context.area.ui_type == 'UV' and context.active_object and context.active_object.type == 'MESH' and context.object.data.uv_layers:
			return True
		return False
	
	def draw_header(self, context):
		try:
			layout = self.layout
		except Exception as exc:
			print(str(exc) + " | Error in Mesh Kit UV Quantize panel header")
			
	def draw(self, context):
		try:
			layout = self.layout
			layout.use_property_decorate = False # No animation
			
			# Display settings
			col = layout.column(align=True)
			row = col.row(align=True)
			row.prop(context.scene.mesh_kit_settings, 'uv_type', expand=True)
			row = col.row(align=True)
			row.prop(context.scene.mesh_kit_settings, 'uv_dimensions', expand=True)
			if context.scene.mesh_kit_settings.uv_type == 'DIV':
				row = col.row(align=True)
				if context.scene.mesh_kit_settings.uv_dimensions == 'True':
					row.prop(context.scene.mesh_kit_settings, 'uv_div_uniform', text='')
				else:
					row.prop(context.scene.mesh_kit_settings, 'uv_div', text='')
			else:
				row = col.row(align=True)
				if context.scene.mesh_kit_settings.uv_dimensions == 'True':
					row.prop(context.scene.mesh_kit_settings, 'uv_val_uniform', text='')
				else:
					row.prop(context.scene.mesh_kit_settings, 'uv_val', text='')
			
			# Display button
			layout.operator(MeshKit_UV_Quantize.bl_idname)
		except Exception as exc:
			print(str(exc) + " | Error in Mesh Kit UV Quantize panel")
