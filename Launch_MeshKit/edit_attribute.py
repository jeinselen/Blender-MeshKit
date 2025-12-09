bl_info = {
	"name": "Edit Attribute Values in Edit Mode",
	"author": "ChatGPT",
	"version": (1, 0, 0),
	"blender": (5, 0, 0),
	"location": "View3D > Sidebar > Attributes",
	"description": "Set mesh attribute values on selected elements and apply gradients in Edit Mode.",
	"category": "Mesh",
}

import bpy
import bmesh
from mathutils import Vector
from bpy.props import (
	EnumProperty,
	FloatProperty,
	FloatVectorProperty,
	PointerProperty,
)

# ------------------------------------------------------------------------
# Helper mappings and functions
# ------------------------------------------------------------------------

# Map attribute domains to BMesh element sequences.
DOMAIN_TO_BMSEQ = {
	"POINT": "verts",  # Vertex domain
	"EDGE": "edges",   # Edge domain
	"FACE": "faces",   # Face domain (polygons)
}


# Map attribute data types to BMesh custom-data layer collections.
DATA_TYPE_TO_LAYER = {
	"FLOAT": "float",            # Scalar value
	"FLOAT_VECTOR": "float_vector",  # 3D vector
	"FLOAT_COLOR": "float_color",    # Float color (RGBA)
	"BYTE_COLOR": "color",           # Byte color (RGBA)
}



def get_bmesh_domain_seq(bm, domain):
	"""Return the BMesh element sequence (verts/edges/faces) for a given attribute domain."""
	seq_name = DOMAIN_TO_BMSEQ.get(domain)
	if not seq_name:
		return None
	return getattr(bm, seq_name, None)



def get_bmesh_layer(domain_seq, data_type, attr_name):
	"""Return the BMesh custom-data layer for this attribute name and data type."""
	layer_type = DATA_TYPE_TO_LAYER.get(data_type)
	if not layer_type:
		return None
	layers = getattr(domain_seq.layers, layer_type, None)
	if layers is None:
		return None
	return layers.get(attr_name)



def smoothstep(t):
	"""Standard smoothstep interpolation (clamped)."""
	t = max(0.0, min(1.0, t))
	return t * t * (3.0 - 2.0 * t)



def smootherstep(t):
	"""Standard smootherstep interpolation (clamped)."""
	t = max(0.0, min(1.0, t))
	return t * t * t * (t * (6.0 * t - 15.0) + 10.0)



def apply_constant_to_attribute(context, settings, which):
	"""
	Apply a constant Input A or Input B value to the selected elements
	of the currently selected attribute on the active mesh in Edit Mode.

	Returns:
		None on success, or an error string.
	"""
	obj = context.active_object
	if obj is None or obj.type != "MESH" or obj.mode != "EDIT":
		return "Active object must be a Mesh in Edit Mode."
	
	mesh = obj.data
	
	attr_name = settings.edit_attribute_name
	if not attr_name:
		return "No attribute selected."
	
	attr = mesh.attributes.get(attr_name)
	if attr is None:
		return "Selected attribute not found on mesh."
	
	if attr.domain not in DOMAIN_TO_BMSEQ:
		return "Attribute domain must be vertex, edge, or face."
	
	if attr.data_type not in DATA_TYPE_TO_LAYER:
		return "Attribute data type must be value, vector, or color."
	
	# Resolve the value to apply based on type and A/B selection.
	dt = attr.data_type
	if dt == "FLOAT":
		value = settings.edit_attribute_float_a if which == "A" else settings.edit_attribute_float_b
	elif dt == "FLOAT_VECTOR":
		value = Vector(settings.edit_attribute_vector_a if which == "A" else settings.edit_attribute_vector_b)
	elif dt in {"FLOAT_COLOR", "BYTE_COLOR"}:
		value = Vector(settings.edit_attribute_color_a if which == "A" else settings.edit_attribute_color_b)
	else:
		return "Unsupported attribute data type."
	
	bm = bmesh.from_edit_mesh(mesh)
	domain_seq = get_bmesh_domain_seq(bm, attr.domain)
	if domain_seq is None:
		return "Could not resolve BMesh domain for attribute."
	
	layer = get_bmesh_layer(domain_seq, attr.data_type, attr.name)
	if layer is None:
		return "Could not find BMesh layer for attribute."
	
	# Assign constant value to all selected elements in this domain.
	for elem in domain_seq:
		if getattr(elem, "select", False):
			elem[layer] = value
			
	bmesh.update_edit_mesh(mesh, loop_triangles=False, destructive=False)
	return None  # Success



def apply_gradient_to_attribute(context, settings):
	"""
	Apply a gradient between Input A and Input B to the selected elements
	of the currently selected attribute on the active mesh in Edit Mode.

	Gradient is computed in world space along the line between Item A and Item B.
	Interpolation is clamped to [0, 1] and can be linear, smoothstep, or smootherstep.

	Returns:
		None on success, or an error string.
	"""
	obj = context.active_object
	if obj is None or obj.type != "MESH" or obj.mode != "EDIT":
		return "Active object must be a Mesh in Edit Mode."
	
	mesh = obj.data
	
	attr_name = settings.edit_attribute_name
	if not attr_name:
		return "No attribute selected."
	
	attr = mesh.attributes.get(attr_name)
	if attr is None:
		return "Selected attribute not found on mesh."
	
	if attr.domain not in DOMAIN_TO_BMSEQ:
		return "Attribute domain must be vertex, edge, or face."
	
	if attr.data_type not in DATA_TYPE_TO_LAYER:
		return "Attribute data type must be value, vector, or color."
	
	obj_a = settings.edit_attribute_item_a
	obj_b = settings.edit_attribute_item_b
	if obj_a is None or obj_b is None:
		return "Both Item A and Item B must be set."
	
	# World-space positions of gradient endpoints (object origins).
	pa = obj_a.matrix_world.translation
	pb = obj_b.matrix_world.translation
	
	direction = pb - pa
	length = direction.length
	if length == 0.0:
		return "Item A and Item B must not be at the same position."
	
	dir_normalized = direction / length
	
	dt = attr.data_type
	if dt == "FLOAT":
		edit_attribute_float_a = settings.edit_attribute_float_a
		edit_attribute_float_b = settings.edit_attribute_float_b
	elif dt == "FLOAT_VECTOR":
		edit_attribute_float_a = Vector(settings.edit_attribute_vector_a)
		edit_attribute_float_b = Vector(settings.edit_attribute_vector_b)
	elif dt in {"FLOAT_COLOR", "BYTE_COLOR"}:
		edit_attribute_float_a = Vector(settings.edit_attribute_color_a)
		edit_attribute_float_b = Vector(settings.edit_attribute_color_b)
	else:
		return "Unsupported attribute data type."
	
	interp_mode = settings.edit_attribute_interpolation
	
	bm = bmesh.from_edit_mesh(mesh)
	domain_seq = get_bmesh_domain_seq(bm, attr.domain)
	if domain_seq is None:
		return "Could not resolve BMesh domain for attribute."
	
	layer = get_bmesh_layer(domain_seq, attr.data_type, attr.name)
	if layer is None:
		return "Could not find BMesh layer for attribute."
	
	mat = obj.matrix_world
	
	# Iterate over selected elements and assign gradient values.
	for elem in domain_seq:
		if not getattr(elem, "select", False):
			continue
		
		# Compute element position in world space depending on domain.
		if attr.domain == "POINT":
			# Vertex position.
			p_local = elem.co
		elif attr.domain == "EDGE":
			# Edge midpoint.
			p_local = (elem.verts[0].co + elem.verts[1].co) * 0.5
		elif attr.domain == "FACE":
			# Face center (median).
			p_local = elem.calc_center_median()
		else:
			# Should not happen, already filtered domains.
			continue
		
		p_world = mat @ p_local
		
		# Parameter t along the A->B segment, clamped to [0, 1].
		# Projection of (p - pa) onto the direction vector.
		t = (p_world - pa).dot(dir_normalized) / length
		t = max(0.0, min(1.0, t))
		
		# Apply interpolation mode to t.
		if interp_mode == "SMOOTH":
			f = smoothstep(t)
		elif interp_mode == "SMOOTHER":
			f = smootherstep(t)
		else:
			f = t  # Linear
			
		# Interpolate between Input A and Input B.
		if dt == "FLOAT":
			value = (1.0 - f) * edit_attribute_float_a + f * edit_attribute_float_b
		else:
			value = edit_attribute_float_a.lerp(edit_attribute_float_b, f)
			
		elem[layer] = value
		
	bmesh.update_edit_mesh(mesh, loop_triangles=False, destructive=False)
	return None  # Success



# ------------------------------------------------------------------------
# Operators
# ------------------------------------------------------------------------
	
class MESH_OT_attribute_apply_constant(bpy.types.Operator):
	"""
	Apply Input A or Input B as a constant value to the selected elements
	of the chosen attribute in Edit Mode.
	"""
	bl_idname = "mesh.attribute_apply_constant"
	bl_label = "Apply Attribute Value"
	bl_options = {"REGISTER", "UNDO"}
	
	which: EnumProperty(
		name="Input",
		description="Which input value to apply",
		items=[
			("A", "A", "Apply Input A"),
			("B", "B", "Apply Input B"),
		],
		default="A",
	)
	
	@classmethod
	def poll(cls, context):
		obj = context.active_object
		return obj is not None and obj.type == "MESH" and obj.mode == "EDIT"
	
	def execute(self, context):
		settings = context.scene.mesh_kit_settings
		err = apply_constant_to_attribute(context, settings, self.which)
		if err is not None:
			self.report({"ERROR"}, err)
			return {"CANCELLED"}
		return {"FINISHED"}
	
	
class MESH_OT_attribute_apply_gradient(bpy.types.Operator):
	"""
	Apply a gradient between Input A and Input B to the selected elements
	of the chosen attribute in Edit Mode.
	"""
	bl_idname = "mesh.attribute_apply_gradient"
	bl_label = "Apply Attribute Gradient"
	bl_options = {"REGISTER", "UNDO"}
	
	@classmethod
	def poll(cls, context):
		obj = context.active_object
		return obj is not None and obj.type == "MESH" and obj.mode == "EDIT"
	
	def execute(self, context):
		settings = context.scene.mesh_kit_settings
		err = apply_gradient_to_attribute(context, settings)
		if err is not None:
			self.report({"ERROR"}, err)
			return {"CANCELLED"}
		return {"FINISHED"}
	
	
# ------------------------------------------------------------------------
# Panel
# ------------------------------------------------------------------------
	
class MESHKIT_PT_edit_attribute(bpy.types.Panel):
	"""
	Panel in the 3D Viewport sidebar to control attribute editing in Edit Mode.
	Works in vertex, edge, and face selection modes.
	"""
	bl_idname = "MESHKIT_PT_edit_attribute"
	bl_label = "Edit Attribute"
	bl_space_type = "VIEW_3D"
	bl_region_type = "UI"
	bl_category = 'Launch'
	bl_options = {'DEFAULT_CLOSED'}
	bl_order = 12
	
	@classmethod
	def poll(cls, context):
		obj = context.active_object
		return obj is not None and obj.type == "MESH" and obj.mode == "EDIT"
	
	def draw(self, context):
		settings = context.scene.mesh_kit_settings
		
		# UI Layout
		layout = self.layout
		layout.use_property_decorate = False  # No animation
		col = layout.column(align=True)
		
		# Attribute selection
		col.prop(settings, "edit_attribute_name", text="")
		
		# Attribute compatibility warning
		obj = context.active_object
		mesh = obj.data if obj and obj.type == "MESH" else None
		attr = mesh.attributes.get(settings.edit_attribute_name) if mesh and settings.edit_attribute_name else None
		if attr is None:
			layout.label(text="Select a compatible attribute", icon="INFO")
			return
		
		# Attribute type label
		domain_label_map = {
			"POINT": "Vertex",
			"EDGE": "Edge",
			"FACE": "Face",
		}
		type_label_map = {
			"FLOAT": "Value",
			"FLOAT_VECTOR": "Vector",
			"FLOAT_COLOR": "Color",
			"BYTE_COLOR": "Color",
		}
		domain_label = domain_label_map.get(attr.domain, attr.domain.title())
		type_label = type_label_map.get(attr.data_type, attr.data_type.title())
		
		row = col.row(align=False)
		row.label(text=f"Domain: {domain_label}")
		row.label(text=f"Type: {type_label}")
		
		# Gap
		col.separator()
		
		# Data inputs
		grid = col.grid_flow(row_major=True, columns=3, even_columns=True, even_rows=True, align=True)
		
		apply_icon="WARNING_LARGE"
		if attr.data_type == "FLOAT":
			grid.prop(settings, "edit_attribute_float_a", text="")
			grid.separator()
			grid.prop(settings, "edit_attribute_float_b", text="")
			apply_icon="NODE_SOCKET_FLOAT"
		elif attr.data_type == "FLOAT_VECTOR":
			grid.prop(settings, "edit_attribute_vector_a", text="")
			grid.separator()
			grid.prop(settings, "edit_attribute_vector_b", text="")
			apply_icon="NODE_SOCKET_VECTOR"
		elif attr.data_type in {"FLOAT_COLOR", "BYTE_COLOR"}:
			grid.prop(settings, "edit_attribute_color_a", text="")
			grid.separator()
			grid.prop(settings, "edit_attribute_color_b", text="")
			apply_icon="NODE_SOCKET_RGBA"
		else:
			row.label(text="Unsupported attribute type", icon="ERROR")
			return
		
		# Apply buttons
		op_a = grid.operator("mesh.attribute_apply_constant", text="A", icon=apply_icon) # ADD REC IMPORT CURRENT_FILE EDITMODE_HLT
		op_a.which = "A"
		
		grid.operator("mesh.attribute_apply_gradient", text="Gradient", icon=apply_icon)
		
		op_b = grid.operator("mesh.attribute_apply_constant", text="B", icon=apply_icon)
		op_b.which = "B"
		
		# Gradient controls
		grid.prop(settings, "edit_attribute_item_a", text="")
		grid.prop(settings, "edit_attribute_interpolation", text="")
		grid.prop(settings, "edit_attribute_item_b", text="")



# ------------------------------------------------------------------------
# Registration
# ------------------------------------------------------------------------
		
classes = (
	MESH_OT_attribute_apply_constant,
	MESH_OT_attribute_apply_gradient,
	MESHKIT_PT_edit_attribute,
)

def register():
	for cls in classes:
		bpy.utils.register_class(cls)

def unregister():
	for cls in reversed(classes):
		bpy.utils.unregister_class(cls)

if __name__ == "__main__":
	register()