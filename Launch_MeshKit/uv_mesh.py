import bpy
import bmesh

from . import utility_panel

###########################################################################
# Helper functions

def get_uv_map_items(self, context):
	# Reads UV map names from the evaluated mesh (including Geometry Nodes output)
	# of the active object, so dynamically generated UV maps are available even
	# when the source mesh itself has none.
	items = []
	obj = context.active_object
	if obj and obj.type == 'MESH':
		depsgraph = context.evaluated_depsgraph_get()
		obj_eval = obj.evaluated_get(depsgraph)
		try:
			mesh_eval = obj_eval.to_mesh(preserve_all_data_layers=True, depsgraph=depsgraph)
			for index, uv_layer in enumerate(mesh_eval.uv_layers):
				items.append((uv_layer.name, uv_layer.name, "", index))
		finally:
			obj_eval.to_mesh_clear()
	if not items:
		items.append(('NONE', "No UV Maps", "Active object has no UV maps available to convert"))
	return items


def build_uv_mesh(obj, context, uv_name, weld_distance):
	# Builds a flat mesh from the object's evaluated UV map at the current frame,
	# preserving n-gons (no triangulation) and welding coincident UV vertices so
	# faces that share a UV edge share topology instead of remaining disconnected.
	# Returns a new Mesh datablock, or None if the UV map isn't available.
	depsgraph = context.evaluated_depsgraph_get()
	obj_eval = obj.evaluated_get(depsgraph)
	try:
		mesh_eval = obj_eval.to_mesh(preserve_all_data_layers=True, depsgraph=depsgraph)
		uv_layer = mesh_eval.uv_layers.get(uv_name)
		if uv_layer is None or len(mesh_eval.polygons) == 0:
			return None

		bm = bmesh.new()
		# New object's own UVMap mirrors its vertex positions (which are the source
		# UV coordinates), so images map identically to how they did on the source.
		new_uv_layer = bm.loops.layers.uv.new("UVMap")
		for polygon in mesh_eval.polygons:
			verts = []
			for loop_index in polygon.loop_indices:
				uv = uv_layer.uv[loop_index].vector
				verts.append(bm.verts.new((uv.x, uv.y, 0.0)))
			try:
				face = bm.faces.new(verts)
			except ValueError:
				# Degenerate face (should not normally happen), skip it
				continue
			for loop in face.loops:
				loop[new_uv_layer].uv = (loop.vert.co.x, loop.vert.co.y)

		bm.verts.ensure_lookup_table()
		bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=weld_distance)
		bm.normal_update()

		new_mesh = bpy.data.meshes.new(name="UVMesh")
		bm.to_mesh(new_mesh)
		bm.free()
		return new_mesh
	finally:
		obj_eval.to_mesh_clear()



###########################################################################
# Main class

class OBJECT_OT_uv_mesh(bpy.types.Operator):
	"""Convert the selected UV map into a new flat mesh object, preserving n-gons"""
	bl_idname = "object.uv_mesh"
	bl_label = "UV to Mesh"
	bl_description = "Bake the selected UV map of the evaluated mesh (including Geometry Nodes output) into a new static mesh object at the current frame"
	bl_options = {'REGISTER', 'UNDO'}

	@classmethod
	def poll(cls, context):
		return any(obj.type == 'MESH' for obj in context.selected_objects)

	def execute(self, context):
		settings = context.scene.mesh_kit_settings
		uv_name = settings.uv_mesh_map

		if not uv_name or uv_name == 'NONE':
			self.report({'ERROR'}, "No UV map selected")
			return {'CANCELLED'}

		separator = settings.uv_mesh_separator
		weld_distance = settings.uv_mesh_weld_distance

		targets = [obj for obj in context.selected_objects if obj.type == 'MESH']
		created = []
		skipped = []

		for obj in targets:
			new_mesh = build_uv_mesh(obj, context, uv_name, weld_distance)
			if new_mesh is None:
				skipped.append(obj.name)
				continue

			new_mesh.name = f"{obj.name}{separator}{uv_name}"
			new_obj = bpy.data.objects.new(new_mesh.name, new_mesh)
			context.collection.objects.link(new_obj)
			created.append(new_obj)

		for obj in context.selected_objects:
			obj.select_set(False)
		for obj in created:
			obj.select_set(True)
		if created:
			context.view_layer.objects.active = created[-1]

		if skipped:
			self.report({'WARNING'}, f"UV map '{uv_name}' not found on: {', '.join(skipped)}")

		if not created:
			return {'CANCELLED'}

		self.report({'INFO'}, f"Created {len(created)} UV mesh object(s)")
		return {'FINISHED'}



###########################################################################
# UI rendering class

class MESHKIT_PT_uvToMesh(bpy.types.Panel):
	bl_label = "UV to Mesh"
	bl_idname = "MESHKIT_PT_uvToMesh"
	bl_space_type = "VIEW_3D"
	bl_region_type = "UI"
	bl_category = 'Launch'
	bl_order = 37
	bl_options = {'DEFAULT_CLOSED'}
	category_preference = "uv_mesh_category"

	@classmethod
	def poll(cls, context):
		return True

	def draw(self, context):
		settings = context.scene.mesh_kit_settings
		try:
			layout = self.layout
			layout.use_property_decorate = False # No animation

			obj = context.active_object
			if obj and obj.type == 'MESH':
				layout.prop(settings, 'uv_mesh_map', text="UV Map")

				row = layout.row(align=True)
				row.prop(settings, 'uv_mesh_separator', text="Separator")
				layout.prop(settings, 'uv_mesh_weld_distance')

				layout.operator(OBJECT_OT_uv_mesh.bl_idname)

				mesh_targets = [o for o in context.selected_objects if o.type == 'MESH']
				box = layout.box()
				box.label(text=str(len(mesh_targets)) + " selected mesh object(s)")
			else:
				layout.label(text="Active object must be a mesh")
		except Exception as exc:
			print(str(exc) + " | Error in Mesh Kit UV to Mesh panel")



###########################################################################
# Addon registration functions

classes = (OBJECT_OT_uv_mesh,)

panels = [MESHKIT_PT_uvToMesh]


def register():
	# Register classes
	for cls in classes:
		bpy.utils.register_class(cls)
	# Register panels
	utility_panel.register_panels(panels)


def unregister():
	# Unregister panels
	utility_panel.unregister_panels(panels)
	# Unregister classes
	for cls in reversed(classes):
		bpy.utils.unregister_class(cls)


if __name__ == "__main__":
	try:
		unregister()
	except Exception:
		pass
	register()
