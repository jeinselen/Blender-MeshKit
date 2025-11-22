import bpy


# ---- Helpers -----------------------------------------------------------------

def get_bbox_min_max(obj):
	"""
	Returns (min_x, max_x, min_y, max_y, min_z, max_z) from the object's local-space bounding box.
	Uses obj.bound_box which is already axis-aligned in local space.
	"""
	bb = obj.bound_box
	bbx = [v[0] for v in bb]
	bby = [v[1] for v in bb]
	bbz = [v[2] for v in bb]
	return min(bbx), max(bbx), min(bby), max(bby), min(bbz), max(bbz)


def compute_offsets(min_x, max_x, min_y, max_y, min_z, max_z, align_x, align_y, align_z):
	"""Compute (dx, dy, dz) needed to align mesh bounding box to origin according to settings."""
	# Horizontal
	if align_x == '+':
		dx = -min_x
	elif align_x == '0':
		dx = - (min_x + max_x) * 0.5
	elif align_x == '-':
		dx = -max_x
	else:
		dx = 0.0
	
	# Vertical (Y axis)
	if align_y == '+':
		dy = -min_y
	elif align_y == '0':
		dy = - (min_y + max_y) * 0.5
	elif align_y == '-':
		dy = -max_y
	else:
		dy = 0.0
	
	# Vertical (Z axis)
	if align_z == '+':
		dz = -min_z
	elif align_z == '0':
		dz = - (min_z + max_z) * 0.5
	elif align_z == '-':
		dz = -max_z
	else:
		dz = 0.0
	
	return dx, dy, dz


def translate_mesh_local(obj, dx, dy, dz):
	"""
	Translate all mesh vertices in local space by (dx, dy, dz).
	Handles edit/object mode safely and preserves the user's current mode.
	"""
	if obj.type != 'MESH':
		return {'CANCELLED'}
	
	# Remember mode to restore later
	current_mode = bpy.context.mode
	
	# Ensure we can edit data
	if current_mode != 'OBJECT':
		bpy.ops.object.mode_set(mode='OBJECT')
	
	# Shift all verts
	verts = obj.data.vertices
	for v in verts:
		v.co.x += dx
		v.co.y += dy
		v.co.z += dz
	
	# Update depsgraph/viewports
	obj.data.update()
	
	# Restore prior mode
	if current_mode != 'OBJECT':
		try:
			bpy.ops.object.mode_set(mode=current_mode)
		except Exception:
			pass
	
	return {'FINISHED'}


# ---- Operator -----------------------------------------------------------------

class OBJECT_OT_mesh_align_origin(bpy.types.Operator):
	"""Shift active mesh geometry so its XY bounding box aligns to the object origin"""
	bl_idname = "object.mesh_align_origin"
	bl_label = "Apply Alignment"
	bl_options = {'REGISTER', 'UNDO'}
	
	@classmethod
	def poll(cls, context):
		obj = context.active_object
		return obj is not None and obj.type == 'MESH'
	
	def execute(self, context):
		obj = context.active_object
		if not obj:
			self.report({'WARNING'}, "No active object.")
			return {'CANCELLED'}
		if obj.type != 'MESH':
			self.report({'WARNING'}, "Active object is not a mesh.")
			return {'CANCELLED'}
		
		# Get bounding box
		min_x, max_x, min_y, max_y, min_z, max_z = get_bbox_min_max(obj)
		
		# Compute offsets
		dx, dy, dz = compute_offsets(
			min_x, max_x, min_y, max_y, min_z, max_z,
			context.scene.mesh_kit_settings.mesh_align_x,
			context.scene.mesh_kit_settings.mesh_align_y,
			context.scene.mesh_kit_settings.mesh_align_z
		)
		
		# Check if mesh is already aligned
		if abs(dx) < 1e-10 and abs(dy) < 1e-10 and abs(dz) < 1e-10:
			self.report({'INFO'}, "Already aligned with the chosen settings.")
			return {'CANCELLED'}
		
		# Shift mesh
		result = translate_mesh_local(obj, dx, dy, dz)
		if 'FINISHED' in result:
			self.report({'INFO'}, f"Shifted geometry by ΔX={dx:.6f}, ΔY={dy:.6f}, ΔY={dz:.6f}.")
		return result


# ---- Panel --------------------------------------------------------------------

class MESHKIT_PT_mesh_align_origin(bpy.types.Panel):
	"""Panel for aligning geometry to origin in XY"""
	bl_idname = "MESHKIT_PT_mesh_align"
	bl_label = "Mesh Align"
	bl_space_type = 'VIEW_3D'
	bl_region_type = 'UI'
	bl_category = "Launch"
	bl_order = 12
	bl_options = {'DEFAULT_CLOSED'}
	
	@classmethod
	def poll(cls, context):
		obj = context.active_object
		return obj is not None and obj.type == 'MESH'
	
	def draw(self, context):
		layout = self.layout
		scene = context.scene
		
		col = layout.column(align=True)
		row1 = col.row(align=True)
		row1.prop(context.scene.mesh_kit_settings, 'mesh_align_x', expand=True)
		row2 = col.row(align=True)
		row2.prop(context.scene.mesh_kit_settings, 'mesh_align_y', expand=True)
		row3 = col.row(align=True)
		row3.prop(context.scene.mesh_kit_settings, 'mesh_align_z', expand=True)
		
		col.separator()
		col.operator(OBJECT_OT_mesh_align_origin.bl_idname, icon='PIVOT_CURSOR')
		# PIVOT_CURSOR OBJECT_ORIGIN EMPTY_AXIS ORIENTATION_CURSOR PIVOT_BOUNDBOX MOD_WIREFRAME CUBE LIGHTPROBE_SPHERE


# ---- Registration -------------------------------------------------------------

classes = (
	OBJECT_OT_mesh_align_origin,
	MESHKIT_PT_mesh_align_origin,
)


def register():
	for cls in classes:
		bpy.utils.register_class(cls)


def unregister():
	for cls in reversed(classes):
		bpy.utils.unregister_class(cls)


if __name__ == "__main__":
	register()
	