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
	StringProperty,
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
# BOOLEAN is intentionally absent: bmesh exposes no bool layer accessor, so mesh
# BOOLEAN attributes are written via a brief object-mode toggle instead.
DATA_TYPE_TO_LAYER = {
	"FLOAT": "float",            # Scalar value
	"INT": "int",                # Integer value
	"FLOAT_VECTOR": "float_vector",  # 3D vector
	"FLOAT_COLOR": "float_color",    # Float color (RGBA)
	"BYTE_COLOR": "color",           # Byte color (RGBA)
}

# Curves (hair) datablocks store attribute values directly on
# `attr.data[i].<field>`. Meshes in Object Mode use the very same per-element
# fields (no bmesh copy in play), so both direct-data paths share this map.
CURVES_FIELD_FOR_TYPE = {
	"FLOAT": "value",
	"INT": "value",
	"BOOLEAN": "value",
	"FLOAT_VECTOR": "vector",
	"FLOAT_COLOR": "color",
	"BYTE_COLOR": "color",
}

ALL_SUPPORTED_TYPES = set(CURVES_FIELD_FOR_TYPE.keys())


# Domains the panel can edit, by object type.
_VALID_DOMAINS_BY_TYPE = {
	"MESH": {"POINT", "EDGE", "FACE"},
	"CURVES": {"POINT", "CURVE"},
}


def has_compatible_attributes(obj):
	"""True if `obj` exposes at least one attribute the editor can act on."""
	if obj is None:
		return False
	valid_domains = _VALID_DOMAINS_BY_TYPE.get(obj.type)
	if valid_domains is None:
		return False
	for attr in obj.data.attributes:
		if attr.name.startswith("."):
			continue
		if attr.domain in valid_domains and attr.data_type in ALL_SUPPORTED_TYPES:
			return True
	return False



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



def _validate_target(context, settings):
	"""Common pre-flight check for apply operators.

	Returns (obj, data, attr, err). On error, err is a string and the rest may be None.
	"""
	obj = context.active_object
	if obj is None or obj.type not in {"MESH", "CURVES"}:
		return None, None, None, "Active object must be a Mesh or Curves."
	data = obj.data
	attr_name = settings.edit_attribute_name
	if not attr_name:
		return obj, data, None, "No attribute selected."
	attr = data.attributes.get(attr_name)
	if attr is None:
		return obj, data, None, "Selected attribute not found."
	valid_domains = {"POINT", "EDGE", "FACE"} if obj.type == "MESH" else {"POINT", "CURVE"}
	if attr.domain not in valid_domains:
		return obj, data, attr, "Attribute domain not supported for this object type."
	if attr.data_type not in ALL_SUPPORTED_TYPES:
		return obj, data, attr, "Attribute data type not supported."
	return obj, data, attr, None


def _resolve_value(settings, dt, which):
	"""Resolve the user-input value for the given data type and A/B selector."""
	s = "_a" if which == "A" else "_b"
	if dt == "FLOAT":
		return float(getattr(settings, "edit_attribute_float" + s))
	if dt == "INT":
		return int(getattr(settings, "edit_attribute_int" + s))
	if dt == "BOOLEAN":
		return bool(getattr(settings, "edit_attribute_bool" + s))
	if dt == "FLOAT_VECTOR":
		return Vector(getattr(settings, "edit_attribute_vector" + s))
	if dt in {"FLOAT_COLOR", "BYTE_COLOR"}:
		return Vector(getattr(settings, "edit_attribute_color" + s))
	return None


def _lerp_typed(va, vb, f, dt):
	"""Interpolate by data type. INT rounds; BOOLEAN thresholds at f >= 0.5."""
	if dt == "FLOAT":
		return (1.0 - f) * va + f * vb
	if dt == "INT":
		return int(round((1.0 - f) * va + f * vb))
	if dt == "BOOLEAN":
		return vb if f >= 0.5 else va
	# FLOAT_VECTOR / FLOAT_COLOR / BYTE_COLOR — Vector.lerp
	return va.lerp(vb, f)


def _interp(t, mode):
	if mode == "SMOOTH":
		return smoothstep(t)
	if mode == "SMOOTHER":
		return smootherstep(t)
	return t  # LINEAR


def _gradient_t(p_world, pa, dir_norm, length):
	t = (p_world - pa).dot(dir_norm) / length
	return max(0.0, min(1.0, t))


def _curves_selection_truthy(item):
	"""The .selection attribute can be BOOLEAN or FLOAT — treat >0.5 / True as selected."""
	v = getattr(item, "value", False)
	if isinstance(v, bool):
		return v
	try:
		return float(v) > 0.5
	except (TypeError, ValueError):
		return False


def _curves_domain_length(curves, domain):
	if domain == "POINT":
		return len(curves.points)
	if domain == "CURVE":
		return len(curves.curves)
	return 0


def _curves_target_indices(curves, domain):
	"""Indices to edit on a Curves object — filtered by .selection when its domain matches."""
	total = _curves_domain_length(curves, domain)
	sel = curves.attributes.get(".selection")
	if sel is not None and sel.domain == domain and len(sel.data) == total:
		return [i for i in range(total) if _curves_selection_truthy(sel.data[i])]
	return list(range(total))


def _curves_position_local(curves, domain, idx, pos_attr):
	"""Local-space position of a curves element (point or curve center).

	The per-curve range API has had name churn across Blender versions;
	probe known variants and fall back to a `points` collection if exposed.
	"""
	if domain == "POINT":
		return Vector(pos_attr.data[idx].vector)
	# CURVE: average of the curve's points.
	curve = curves.curves[idx]
	start = getattr(curve, "first_point_index", None)
	if start is None:
		start = getattr(curve, "points_first", None)
	count = getattr(curve, "points_length", None)
	if count is None:
		count = getattr(curve, "points_num", None)
	if start is not None and count and count > 0:
		acc = Vector((0.0, 0.0, 0.0))
		for j in range(start, start + count):
			acc += Vector(pos_attr.data[j].vector)
		return acc / count
	# Final fallback: per-curve points collection, if exposed.
	pts = getattr(curve, "points", None)
	if pts:
		acc = Vector((0.0, 0.0, 0.0))
		n = 0
		for p in pts:
			pos = getattr(p, "position", None) or getattr(p, "co", None)
			if pos is None:
				continue
			acc += Vector(pos)
			n += 1
		if n > 0:
			return acc / n
	return Vector((0.0, 0.0, 0.0))


# ------------------------------------------------------------------------
# Apply: constant
# ------------------------------------------------------------------------


def apply_constant_to_attribute(context, settings, which):
	"""Apply a constant value (Input A or B) to selected elements of the chosen attribute."""
	obj, data, attr, err = _validate_target(context, settings)
	if err:
		return err
	value = _resolve_value(settings, attr.data_type, which)
	if value is None:
		return "Unsupported attribute data type."
	if obj.type == "MESH":
		if obj.mode == "EDIT":
			return _apply_constant_mesh(obj, data, attr, value)
		return _apply_constant_mesh_object_mode(data, attr, value)
	# Curves: direct attribute access works in both Edit and Object Mode.
	return _apply_constant_curves(data, attr, value)


def _apply_constant_mesh(obj, mesh, attr, value):
	dt = attr.data_type
	if dt == "BOOLEAN":
		return _apply_mesh_boolean_constant(obj, mesh, attr, bool(value))
	bm = bmesh.from_edit_mesh(mesh)
	domain_seq = get_bmesh_domain_seq(bm, attr.domain)
	if domain_seq is None:
		return "Could not resolve BMesh domain for attribute."
	layer = get_bmesh_layer(domain_seq, dt, attr.name)
	if layer is None:
		return "Could not find BMesh layer for attribute."
	for elem in domain_seq:
		if getattr(elem, "select", False):
			elem[layer] = value
	bmesh.update_edit_mesh(mesh, loop_triangles=False, destructive=False)
	return None


def _mesh_selected_indices(mesh, domain):
	"""Collect selected element indices in mesh Edit Mode using bmesh."""
	bm = bmesh.from_edit_mesh(mesh)
	domain_seq = get_bmesh_domain_seq(bm, domain)
	if domain_seq is None:
		return []
	domain_seq.ensure_lookup_table()
	return [i for i, elem in enumerate(domain_seq) if getattr(elem, "select", False)]


def _apply_mesh_boolean_constant(obj, mesh, attr, value):
	"""bmesh has no bool layer — collect selection in edit mode, write in object mode."""
	indices = _mesh_selected_indices(mesh, attr.domain)
	if not indices:
		return None
	attr_name = attr.name
	bpy.ops.object.mode_set(mode="OBJECT")
	try:
		data_attr = mesh.attributes.get(attr_name)
		if data_attr is None:
			return "Attribute disappeared during mode toggle."
		for i in indices:
			data_attr.data[i].value = value
	finally:
		bpy.ops.object.mode_set(mode="EDIT")
	return None


def _apply_constant_curves(curves, attr, value):
	field = CURVES_FIELD_FOR_TYPE[attr.data_type]
	for i in _curves_target_indices(curves, attr.domain):
		setattr(attr.data[i], field, value)
	curves.update_tag()
	return None


# ------------------------------------------------------------------------
# Apply: gradient
# ------------------------------------------------------------------------


def apply_gradient_to_attribute(context, settings):
	"""Apply a world-space gradient between Item A and Item B across selected elements."""
	obj, data, attr, err = _validate_target(context, settings)
	if err:
		return err

	value_a = _resolve_value(settings, attr.data_type, "A")
	value_b = _resolve_value(settings, attr.data_type, "B")
	if value_a is None or value_b is None:
		return "Unsupported attribute data type."

	obj_a = settings.edit_attribute_item_a
	obj_b = settings.edit_attribute_item_b
	if obj_a is None or obj_b is None:
		return "Both Item A and Item B must be set."
	pa = obj_a.matrix_world.translation
	pb = obj_b.matrix_world.translation
	direction = pb - pa
	length = direction.length
	if length == 0.0:
		return "Item A and Item B must not be at the same position."
	dir_norm = direction / length
	interp_mode = settings.edit_attribute_interpolation

	if obj.type == "MESH":
		if obj.mode == "EDIT":
			return _apply_gradient_mesh(obj, data, attr, value_a, value_b, pa, dir_norm, length, interp_mode)
		return _apply_gradient_mesh_object_mode(obj, data, attr, value_a, value_b, pa, dir_norm, length, interp_mode)
	return _apply_gradient_curves(obj, data, attr, value_a, value_b, pa, dir_norm, length, interp_mode)


def _apply_gradient_mesh(obj, mesh, attr, value_a, value_b, pa, dir_norm, length, interp_mode):
	dt = attr.data_type
	mat = obj.matrix_world

	if dt == "BOOLEAN":
		# Compute per-element f in edit mode, then write in object mode.
		bm = bmesh.from_edit_mesh(mesh)
		domain_seq = get_bmesh_domain_seq(bm, attr.domain)
		if domain_seq is None:
			return "Could not resolve BMesh domain for attribute."
		domain_seq.ensure_lookup_table()
		writes = []
		for i, elem in enumerate(domain_seq):
			if not getattr(elem, "select", False):
				continue
			p_local = _bmesh_elem_position(elem, attr.domain)
			if p_local is None:
				continue
			f = _interp(_gradient_t(mat @ p_local, pa, dir_norm, length), interp_mode)
			writes.append((i, _lerp_typed(value_a, value_b, f, dt)))
		if not writes:
			return None
		attr_name = attr.name
		bpy.ops.object.mode_set(mode="OBJECT")
		try:
			data_attr = mesh.attributes.get(attr_name)
			if data_attr is None:
				return "Attribute disappeared during mode toggle."
			for i, v in writes:
				data_attr.data[i].value = bool(v)
		finally:
			bpy.ops.object.mode_set(mode="EDIT")
		return None

	bm = bmesh.from_edit_mesh(mesh)
	domain_seq = get_bmesh_domain_seq(bm, attr.domain)
	if domain_seq is None:
		return "Could not resolve BMesh domain for attribute."
	layer = get_bmesh_layer(domain_seq, dt, attr.name)
	if layer is None:
		return "Could not find BMesh layer for attribute."

	for elem in domain_seq:
		if not getattr(elem, "select", False):
			continue
		p_local = _bmesh_elem_position(elem, attr.domain)
		if p_local is None:
			continue
		f = _interp(_gradient_t(mat @ p_local, pa, dir_norm, length), interp_mode)
		elem[layer] = _lerp_typed(value_a, value_b, f, dt)

	bmesh.update_edit_mesh(mesh, loop_triangles=False, destructive=False)
	return None


def _bmesh_elem_position(elem, domain):
	if domain == "POINT":
		return elem.co
	if domain == "EDGE":
		return (elem.verts[0].co + elem.verts[1].co) * 0.5
	if domain == "FACE":
		return elem.calc_center_median()
	return None


# ------------------------------------------------------------------------
# Object Mode (mesh): direct attribute-data path
#
# Edit Mode mesh edits live in a bmesh copy, so they route through the bmesh
# layers above. In Object Mode there is no bmesh — values are written straight
# to `mesh.attributes[name].data[i]`, whose index lines up with the domain's
# element collection. Selection comes from the persisted `.select` flags, and
# BOOLEAN needs no special-casing here (no bmesh-layer limitation), so every
# type uses the same field map as curves.
# ------------------------------------------------------------------------


def _mesh_object_mode_elements(mesh, domain):
	"""Element collection whose index matches the attribute data for this domain."""
	if domain == "POINT":
		return mesh.vertices
	if domain == "EDGE":
		return mesh.edges
	if domain == "FACE":
		return mesh.polygons
	return None


def _mesh_object_elem_position(elem, mesh, domain):
	"""Local-space position of a mesh element in Object Mode."""
	if domain == "POINT":
		return elem.co
	if domain == "EDGE":
		verts = mesh.vertices
		return (verts[elem.vertices[0]].co + verts[elem.vertices[1]].co) * 0.5
	if domain == "FACE":
		return elem.center
	return None


def _apply_constant_mesh_object_mode(mesh, attr, value):
	elements = _mesh_object_mode_elements(mesh, attr.domain)
	if elements is None:
		return "Unsupported attribute domain for this mesh."
	field = CURVES_FIELD_FOR_TYPE[attr.data_type]
	for i, elem in enumerate(elements):
		if elem.select:
			setattr(attr.data[i], field, value)
	mesh.update_tag()
	return None


def _apply_gradient_mesh_object_mode(obj, mesh, attr, value_a, value_b, pa, dir_norm, length, interp_mode):
	elements = _mesh_object_mode_elements(mesh, attr.domain)
	if elements is None:
		return "Unsupported attribute domain for this mesh."
	dt = attr.data_type
	field = CURVES_FIELD_FOR_TYPE[dt]
	mat = obj.matrix_world
	for i, elem in enumerate(elements):
		if not elem.select:
			continue
		p_local = _mesh_object_elem_position(elem, mesh, attr.domain)
		if p_local is None:
			continue
		f = _interp(_gradient_t(mat @ p_local, pa, dir_norm, length), interp_mode)
		setattr(attr.data[i], field, _lerp_typed(value_a, value_b, f, dt))
	mesh.update_tag()
	return None


def _apply_gradient_curves(obj, curves, attr, value_a, value_b, pa, dir_norm, length, interp_mode):
	dt = attr.data_type
	field = CURVES_FIELD_FOR_TYPE[dt]
	pos_attr = curves.attributes.get("position")
	if pos_attr is None:
		return "Curves object is missing its position attribute."
	mat = obj.matrix_world

	for i in _curves_target_indices(curves, attr.domain):
		try:
			p_local = _curves_position_local(curves, attr.domain, i, pos_attr)
		except (AttributeError, IndexError):
			continue
		f = _interp(_gradient_t(mat @ p_local, pa, dir_norm, length), interp_mode)
		setattr(attr.data[i], field, _lerp_typed(value_a, value_b, f, dt))

	curves.update_tag()
	return None



# ------------------------------------------------------------------------
# Operators
# ------------------------------------------------------------------------
	
def _new_attribute_domain_items(self, context):
	"""Dynamic domain enum based on the active object's type.

	Restricted to the domains the editor itself supports so creating an
	attribute never produces something invisible in the panel dropdown.
	"""
	obj = getattr(context, "active_object", None) if context else None
	if obj is not None and obj.type == "CURVES":
		return [
			("POINT", "Point", "Per-point attribute"),
			("CURVE", "Curve", "Per-curve attribute"),
		]
	return [
		("POINT", "Vertex", "Per-vertex attribute"),
		("EDGE", "Edge", "Per-edge attribute"),
		("FACE", "Face", "Per-face attribute"),
	]


class MESH_OT_attribute_add(bpy.types.Operator):
	"""Create a new attribute on the active object's data and select it for editing."""
	bl_idname = "mesh.attribute_add"
	bl_label = "New Attribute"
	bl_options = {"REGISTER", "UNDO"}

	name: StringProperty(
		name="Name",
		description="Name of the new attribute",
		default="Attribute",
	)

	domain: EnumProperty(
		name="Domain",
		description="Attribute domain",
		items=_new_attribute_domain_items,
	)

	data_type: EnumProperty(
		name="Type",
		description="Attribute data type",
		items=[
			("FLOAT", "Float", "Scalar value"),
			("INT", "Integer", "Integer value"),
			("BOOLEAN", "Boolean", "Boolean value"),
			("FLOAT_VECTOR", "Vector", "3D vector"),
			("FLOAT_COLOR", "Color", "Float color (RGBA)"),
			("BYTE_COLOR", "Byte Color", "Byte color (RGBA)"),
		],
		default="FLOAT",
	)

	@classmethod
	def poll(cls, context):
		obj = context.active_object
		return obj is not None and obj.type in {"MESH", "CURVES"}

	def invoke(self, context, event):
		return context.window_manager.invoke_props_dialog(self)

	def execute(self, context):
		obj = context.active_object
		name = (self.name or "").strip() or "Attribute"
		try:
			bpy.ops.geometry.attribute_add(
				name=name,
				domain=self.domain,
				data_type=self.data_type,
			)
		except RuntimeError as e:
			self.report({"ERROR"}, f"Could not create attribute: {e}")
			return {"CANCELLED"}

		# Auto-select the new attribute (Blender may have suffixed the name to dedupe).
		new_attr = obj.data.attributes.active
		if new_attr is not None:
			try:
				context.scene.mesh_kit_settings.edit_attribute_name = new_attr.name
			except TypeError:
				# Type not yet whitelisted by the panel's enum filter — silently skip.
				pass
		return {"FINISHED"}


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
		return obj is not None and obj.type in {"MESH", "CURVES"}

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
		return obj is not None and obj.type in {"MESH", "CURVES"}

	def execute(self, context):
		settings = context.scene.mesh_kit_settings
		err = apply_gradient_to_attribute(context, settings)
		if err is not None:
			self.report({"ERROR"}, err)
			return {"CANCELLED"}
		return {"FINISHED"}
	
	
class MESH_OT_convert_legacy_curve(bpy.types.Operator):
	"""Convert the active legacy Curve (Bézier/NURBS/Poly) into a modern Curves
	object so its points and curves expose editable attributes."""
	bl_idname = "mesh.convert_legacy_curve_to_curves"
	bl_label = "Convert to Curves"
	bl_options = {"REGISTER", "UNDO"}

	@classmethod
	def poll(cls, context):
		obj = context.active_object
		return obj is not None and obj.type == "CURVE"

	def execute(self, context):
		obj = context.active_object
		# object.convert only polls in Object Mode, so drop out of Edit first.
		was_edit = obj.mode == "EDIT"
		if was_edit:
			bpy.ops.object.mode_set(mode="OBJECT")
		try:
			bpy.ops.object.convert(target="CURVES")
		except RuntimeError as e:
			self.report({"ERROR"}, f"Could not convert to Curves: {e}")
			return {"CANCELLED"}
		# Return to Edit Mode on the converted object if that's where the user was.
		if was_edit and context.active_object is not None:
			bpy.ops.object.mode_set(mode="EDIT")
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
	bl_order = 35

	@classmethod
	def poll(cls, context):
		# Always show for meshes/curves (legacy CURVE included so we can offer a
		# conversion). The panel works in both Object and Edit Mode.
		obj = context.active_object
		return obj is not None and obj.type in {"MESH", "CURVES", "CURVE"}

	def draw(self, context):
		settings = context.scene.mesh_kit_settings
		
		# UI Layout
		layout = self.layout
		layout.use_property_decorate = False  # No animation

		obj = context.active_object

		# Legacy Curve (Bézier/NURBS/Poly) has no attribute system at all. Offer
		# a one-click conversion to the modern Curves object instead.
		if obj is not None and obj.type == "CURVE":
			col = layout.column(align=True)
			col.label(text="Legacy curves have no attributes.", icon="INFO")
			col.label(text="Convert to a Curves object to edit.")
			layout.operator("mesh.convert_legacy_curve_to_curves", icon="OUTLINER_OB_CURVES")
			return

		# Attribute selection + create
		data = obj.data if obj and obj.type in {"MESH", "CURVES"} else None
		any_compatible = has_compatible_attributes(obj)

		row = layout.row(align=True)
		if any_compatible:
			row.prop(settings, "edit_attribute_name", text="")
		else:
			# Empty enum would emit an RNA warning every redraw — show a placeholder instead.
			sub = row.row()
			sub.enabled = False
			sub.label(text="No compatible attributes")
		row.operator("mesh.attribute_add", text="", icon="ADD")

		if not any_compatible:
			return

		attr = data.attributes.get(settings.edit_attribute_name) if data and settings.edit_attribute_name else None
		if attr is None:
			layout.label(text="Select a compatible attribute", icon="INFO")
			return

		# Data inputs
		row = layout.row(align=False)
		colA = row.column(align=True)
		colB = row.column(align=True)

		apply_icon = "WARNING_LARGE"
		if attr.data_type == "FLOAT":
			colA.prop(settings, "edit_attribute_float_a", text="")
			colB.prop(settings, "edit_attribute_float_b", text="")
			apply_icon = "NODE_SOCKET_FLOAT"
		elif attr.data_type == "INT":
			colA.prop(settings, "edit_attribute_int_a", text="")
			colB.prop(settings, "edit_attribute_int_b", text="")
			apply_icon = "NODE_SOCKET_INT"
		elif attr.data_type == "BOOLEAN":
			colA.prop(settings, "edit_attribute_bool_a", text="A")
			colB.prop(settings, "edit_attribute_bool_b", text="B")
			apply_icon = "NODE_SOCKET_BOOLEAN"
		elif attr.data_type == "FLOAT_VECTOR":
			colA.prop(settings, "edit_attribute_vector_a", text="")
			colB.prop(settings, "edit_attribute_vector_b", text="")
			apply_icon = "NODE_SOCKET_VECTOR"
		elif attr.data_type in {"FLOAT_COLOR", "BYTE_COLOR"}:
			colA.prop(settings, "edit_attribute_color_a", text="")
			colB.prop(settings, "edit_attribute_color_b", text="")
			apply_icon = "NODE_SOCKET_RGBA"
		else:
			layout.label(text="Unsupported attribute type", icon="ERROR")
			return
		
		# Apply buttons
		op_a = colA.operator("mesh.attribute_apply_constant", text="Apply A", icon=apply_icon) # ADD REC IMPORT CURRENT_FILE EDITMODE_HLT
		op_a.which = "A"
		op_b = colB.operator("mesh.attribute_apply_constant", text="Apply B", icon=apply_icon)
		op_b.which = "B"
		
		# Gradient controls
		col = layout.column(align=True)
		row = col.row(align=True)
		row.prop(settings, "edit_attribute_item_a", text="")
		row.prop(settings, "edit_attribute_item_b", text="")
		col.prop(settings, "edit_attribute_interpolation", text="")
		col.operator("mesh.attribute_apply_gradient", text="Apply Gradient", icon=apply_icon)
		
		# Attribute type label
		is_curves = obj.type == "CURVES"
		domain_label_map = {
			"POINT": "Point" if is_curves else "Vertex",
			"EDGE": "Edge",
			"FACE": "Face",
			"CURVE": "Curve",
		}
		type_label_map = {
			"FLOAT": "Value",
			"INT": "Integer",
			"BOOLEAN": "Boolean",
			"FLOAT_VECTOR": "Vector",
			"FLOAT_COLOR": "Color",
			"BYTE_COLOR": "Color",
		}
		domain_label = domain_label_map.get(attr.domain, attr.domain.title())
		type_label = type_label_map.get(attr.data_type, attr.data_type.title())
		row = col.row(align=False)
		row.label(text=f"Domain: {domain_label}")
		row.label(text=f"Type: {type_label}")



# ------------------------------------------------------------------------
# Registration
# ------------------------------------------------------------------------
		
classes = (
	MESH_OT_attribute_add,
	MESH_OT_convert_legacy_curve,
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