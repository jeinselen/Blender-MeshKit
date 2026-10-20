import bpy
import math
import os
import random

from array import array
from pathlib import Path

from bpy_extras.io_utils import ImportHelper

from . import utility_panel


NODE_GROUP_TAG = "meshkit_image_shader_group"
MATERIAL_TAG = "meshkit_image_material"
TEXTURE_NODE_TAG = "meshkit_image_source_texture"
NODE_GROUP_NAME = "MeshKit Shader"
TEXTURE_NODE_NAME = "MeshKit Texture"
SOURCE_PROPERTY = "MeshKit Texture"


###########################################################################
# Raster segmentation helpers

def _content_bbox(mask, width, height, bounds=None):
	if bounds is None:
		x0, y0, x1, y1 = 0, 0, width, height
	else:
		x0, y0, x1, y1 = bounds

	min_x, min_y = x1, y1
	max_x = max_y = -1
	for y in range(y0, y1):
		row_start = y * width
		found = mask.find(b"\x01", row_start + x0, row_start + x1)
		if found < 0:
			continue
		min_y = min(min_y, y)
		max_y = max(max_y, y)
		first_x = found - row_start
		min_x = min(min_x, first_x)
		for x in range(x1 - 1, first_x - 1, -1):
			if mask[row_start + x]:
				max_x = max(max_x, x)
				break

	if max_x < min_x or max_y < min_y:
		return None
	return (min_x, min_y, max_x + 1, max_y + 1)


def _qualifying_runs(flags, start, end, threshold):
	"""Return half-open runs whose length is strictly greater than threshold."""
	runs = []
	run_start = None
	for value in range(start, end):
		if flags(value):
			if run_start is None:
				run_start = value
		elif run_start is not None:
			if value - run_start > threshold:
				runs.append((run_start, value))
			run_start = None
	if run_start is not None and end - run_start > threshold:
		runs.append((run_start, end))
	return runs


def _ranges_between(start, end, gaps):
	if not gaps:
		return [(start, end)]
	ranges = []
	cursor = start
	for gap_start, gap_end in gaps:
		if cursor < gap_start:
			ranges.append((cursor, gap_start))
		cursor = gap_end
	if cursor < end:
		ranges.append((cursor, end))
	return ranges


def _rectilinear_regions(mask, width, height, threshold, iterations):
	initial = _content_bbox(mask, width, height)
	if initial is None:
		return []
	regions = [initial]

	for _iteration in range(iterations):
		changed = False
		next_regions = []
		for region in regions:
			bbox = _content_bbox(mask, width, height, region)
			if bbox is None:
				continue
			x0, y0, x1, y1 = bbox

			def row_empty(y):
				start = y * width + x0
				return mask.find(b"\x01", start, y * width + x1) < 0

			def column_empty(x):
				for y in range(y0, y1):
					if mask[y * width + x]:
						return False
				return True

			y_gaps = _qualifying_runs(row_empty, y0, y1, threshold)
			x_gaps = _qualifying_runs(column_empty, x0, x1, threshold)
			x_ranges = _ranges_between(x0, x1, x_gaps)
			y_ranges = _ranges_between(y0, y1, y_gaps)
			if len(x_ranges) > 1 or len(y_ranges) > 1:
				changed = True

			for child_y0, child_y1 in y_ranges:
				for child_x0, child_x1 in x_ranges:
					child = _content_bbox(
						mask,
						width,
						height,
						(child_x0, child_y0, child_x1, child_y1),
					)
					if child is not None:
						next_regions.append(child)
		regions = next_regions
		if not changed:
			break

	return regions


def _crop_mask(mask, width, bounds):
	x0, y0, x1, y1 = bounds
	crop_width = x1 - x0
	crop_height = y1 - y0
	result = bytearray(crop_width * crop_height)
	for local_y, source_y in enumerate(range(y0, y1)):
		source_start = source_y * width + x0
		target_start = local_y * crop_width
		result[target_start:target_start + crop_width] = mask[source_start:source_start + crop_width]
	return result, crop_width, crop_height


def _dilate_mask(mask, width, height, threshold):
	"""Square dilation with exact gap behavior and half-pixel rounding for odd values."""
	low = threshold // 2
	high = threshold - low
	horizontal = bytearray(width * height)

	for y in range(height):
		row = y * width
		count = 0
		for source_x in range(0, min(width, low + 1)):
			count += mask[row + source_x]
		for x in range(width):
			if x > 0:
				remove_x = x - 1 - high
				add_x = x + low
				if remove_x >= 0:
					count -= mask[row + remove_x]
				if add_x < width:
					count += mask[row + add_x]
			horizontal[row + x] = 1 if count else 0

	result = bytearray(width * height)
	for x in range(width):
		count = 0
		for source_y in range(0, min(height, low + 1)):
			count += horizontal[source_y * width + x]
		for y in range(height):
			if y > 0:
				remove_y = y - 1 - high
				add_y = y + low
				if remove_y >= 0:
					count -= horizontal[remove_y * width + x]
				if add_y < height:
					count += horizontal[add_y * width + x]
			result[y * width + x] = 1 if count else 0
	return result


def _polygon_area(points):
	return 0.5 * sum(
		a[0] * b[1] - b[0] * a[1]
		for a, b in zip(points, points[1:] + points[:1])
	)


def _remove_collinear(points):
	if len(points) < 4:
		return points
	result = []
	for index, point in enumerate(points):
		previous = points[index - 1]
		following = points[(index + 1) % len(points)]
		cross = (
			(point[0] - previous[0]) * (following[1] - point[1])
			- (point[1] - previous[1]) * (following[0] - point[0])
		)
		if cross != 0:
			result.append(point)
	return result


def _trace_mask(mask, width, height):
	"""Trace all outer boundaries without storing every component pixel as Python objects."""
	edges = set()
	for index, occupied in enumerate(mask):
		if not occupied:
			continue
		x = index % width
		y = index // width
		if y == 0 or not mask[index - width]:
			edges.add(((x, y), (x + 1, y)))
		if x + 1 == width or not mask[index + 1]:
			edges.add(((x + 1, y), (x + 1, y + 1)))
		if y + 1 == height or not mask[index + width]:
			edges.add(((x + 1, y + 1), (x, y + 1)))
		if x == 0 or not mask[index - 1]:
			edges.add(((x, y + 1), (x, y)))

	outgoing = {}
	for edge in edges:
		outgoing.setdefault(edge[0], []).append(edge[1])

	unused = set(edges)
	loops = []
	direction_index = {(1, 0): 0, (0, 1): 1, (-1, 0): 2, (0, -1): 3}
	turn_priority = {1: 0, 0: 1, 3: 2, 2: 3}

	while unused:
		start_edge = min(unused)
		start_point, current = start_edge
		unused.remove(start_edge)
		loop = [start_point]
		previous = start_point

		while current != start_point:
			loop.append(current)
			candidates = [end for end in outgoing.get(current, []) if (current, end) in unused]
			if not candidates:
				loop = []
				break
			incoming = direction_index[(current[0] - previous[0], current[1] - previous[1])]

			def candidate_key(end):
				outgoing_direction = direction_index[(end[0] - current[0], end[1] - current[1])]
				turn = (outgoing_direction - incoming) % 4
				return turn_priority[turn]

			next_point = min(candidates, key=candidate_key)
			unused.remove((current, next_point))
			previous, current = current, next_point

		if len(loop) >= 3:
			loops.append(_remove_collinear(loop))

	return [loop for loop in loops if len(loop) >= 3 and _polygon_area(loop) > 0]


def _distance_to_segment(point, start, end):
	dx = end[0] - start[0]
	dy = end[1] - start[1]
	if dx == 0 and dy == 0:
		return math.hypot(point[0] - start[0], point[1] - start[1])
	t = ((point[0] - start[0]) * dx + (point[1] - start[1]) * dy) / (dx * dx + dy * dy)
	t = max(0.0, min(1.0, t))
	closest_x = start[0] + t * dx
	closest_y = start[1] + t * dy
	return math.hypot(point[0] - closest_x, point[1] - closest_y)


def _rdp_open(points, tolerance):
	if len(points) <= 2:
		return points
	start = points[0]
	end = points[-1]
	max_distance = -1.0
	max_index = 0
	for index in range(1, len(points) - 1):
		distance = _distance_to_segment(points[index], start, end)
		if distance > max_distance:
			max_distance = distance
			max_index = index
	if max_distance > tolerance:
		left = _rdp_open(points[:max_index + 1], tolerance)
		right = _rdp_open(points[max_index:], tolerance)
		return left[:-1] + right
	return [start, end]


def _simplify_closed(points, tolerance):
	if len(points) <= 4 or tolerance <= 0:
		return points
	min_x_index = min(range(len(points)), key=lambda index: (points[index][0], points[index][1]))
	max_x_index = max(range(len(points)), key=lambda index: (points[index][0], points[index][1]))
	if min_x_index == max_x_index:
		return points
	if min_x_index > max_x_index:
		min_x_index, max_x_index = max_x_index, min_x_index
	chain_a = points[min_x_index:max_x_index + 1]
	chain_b = points[max_x_index:] + points[:min_x_index + 1]
	simplified = _rdp_open(chain_a, tolerance)[:-1] + _rdp_open(chain_b, tolerance)[:-1]
	if len(simplified) < 3:
		return points
	if _polygon_area(simplified) < 0:
		simplified.reverse()
	return simplified


def _contour_regions(mask, width, height, threshold, detail, bounds):
	cropped, crop_width, crop_height = _crop_mask(mask, width, bounds)
	dilated = _dilate_mask(cropped, crop_width, crop_height, threshold)
	x_offset, y_offset = bounds[0], bounds[1]
	polygons = []
	for loop in _trace_mask(dilated, crop_width, crop_height):
		loop = _simplify_closed(loop, float(detail))
		polygons.append([(x + x_offset, y + y_offset) for x, y in loop])
	return polygons


def _rect_polygon(bounds, padding, width, height):
	x0, y0, x1, y1 = bounds
	x0 = max(0.0, x0 - padding)
	y0 = max(0.0, y0 - padding)
	x1 = min(float(width), x1 + padding)
	y1 = min(float(height), y1 + padding)
	return [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]


def _sort_polygons(polygons, sort_mode, seed, width, height):
	def bounds(poly):
		xs = [point[0] for point in poly]
		ys = [point[1] for point in poly]
		return min(xs), min(ys), max(xs), max(ys)

	if sort_mode == "RANDOM":
		result = list(polygons)
		random.Random(seed).shuffle(result)
		return result

	center_x = width * 0.5
	center_y = height * 0.5

	def key(poly):
		min_x, min_y, max_x, max_y = bounds(poly)
		if sort_mode == "LR_TD":
			return (-max_y, min_x)
		if sort_mode == "RL_TD":
			return (-max_y, -max_x)
		if sort_mode == "LR_BU":
			return (min_y, min_x)
		if sort_mode == "RL_BU":
			return (min_y, -max_x)
		poly_center_x = (min_x + max_x) * 0.5
		poly_center_y = (min_y + max_y) * 0.5
		distance = (poly_center_x - center_x) ** 2 + (poly_center_y - center_y) ** 2
		angle = math.atan2(poly_center_y - center_y, poly_center_x - center_x)
		if sort_mode == "EDGE_IN":
			return (-distance, angle)
		return (distance, angle)

	return sorted(polygons, key=key)


def build_polygons(mask, width, height, settings):
	mode = settings.image_mesh_segmentation
	threshold = settings.image_mesh_threshold
	if mode == "NONE":
		return [[(0.0, 0.0), (float(width), 0.0), (float(width), float(height)), (0.0, float(height))]]

	if not any(mask):
		return []

	if mode in {"RECTILINEAR", "BOTH"}:
		regions = _rectilinear_regions(
			mask,
			width,
			height,
			threshold,
			settings.image_mesh_iterations,
		)
	else:
		regions = [(0, 0, width, height)]

	polygons = []
	if mode == "RECTILINEAR":
		padding = threshold * 0.5
		polygons = [_rect_polygon(region, padding, width, height) for region in regions]
	else:
		for region in regions:
			if mode == "BOTH":
				padding = (threshold + 1) // 2
				region = (
					max(0, region[0] - padding),
					max(0, region[1] - padding),
					min(width, region[2] + padding),
					min(height, region[3] + padding),
				)
			polygons.extend(
				_contour_regions(
					mask,
					width,
					height,
					threshold,
					settings.image_mesh_detail,
					region,
				)
			)

	return _sort_polygons(
		polygons,
		settings.image_mesh_sort,
		settings.image_mesh_seed,
		width,
		height,
	)


###########################################################################
# Blender image, mesh, and material helpers

def _alpha_mask(image):
	width, height = image.size[:]
	if width < 1 or height < 1:
		raise ValueError("Image has no pixel data")
	pixels = array("f", [0.0]) * (width * height * 4)
	image.pixels.foreach_get(pixels)
	mask = bytearray(width * height)
	for index in range(width * height):
		mask[index] = 1 if pixels[index * 4 + 3] > 0.0 else 0
	return mask, width, height


def _alignment_offset(alignment, width, height):
	if alignment.endswith("LEFT") or alignment == "LEFT":
		x = 0.0
	elif alignment.endswith("RIGHT") or alignment == "RIGHT":
		x = -float(width)
	else:
		x = -float(width) * 0.5

	if alignment.startswith("TOP") or alignment == "TOP":
		y = -float(height)
	elif alignment.startswith("BOTTOM") or alignment == "BOTTOM":
		y = 0.0
	else:
		y = -float(height) * 0.5
	return x, y


def _build_mesh(name, polygons, width, height, pixels_per_meter, alignment):
	offset_x, offset_y = _alignment_offset(alignment, width, height)
	vertices = []
	uvs = []
	faces = []
	for polygon in polygons:
		if len(polygon) < 3:
			continue
		face = []
		for x, y in polygon:
			face.append(len(vertices))
			vertices.append(((x + offset_x) / pixels_per_meter, (y + offset_y) / pixels_per_meter, 0.0))
			uvs.append((x / width, y / height))
		faces.append(face)

	if not faces:
		raise ValueError("No visible image regions were found")

	mesh = bpy.data.meshes.new(name)
	try:
		mesh.from_pydata(vertices, [], faces)
		mesh.update(calc_edges=True)
		uv_layer = mesh.uv_layers.new(name="UVMap")
		for loop in mesh.loops:
			uv_layer.uv[loop.index].vector = uvs[loop.vertex_index]
		return mesh
	except Exception:
		bpy.data.meshes.remove(mesh)
		raise


def _find_shader_group():
	for group in bpy.data.node_groups:
		if group.bl_idname == "ShaderNodeTree" and group.get(NODE_GROUP_TAG):
			return group
	return None


def _ensure_shader_group():
	group = _find_shader_group()
	if group is not None:
		return group

	group = bpy.data.node_groups.new(NODE_GROUP_NAME, "ShaderNodeTree")
	group[NODE_GROUP_TAG] = True
	group.interface.new_socket(name="Color", in_out="INPUT", socket_type="NodeSocketColor")
	group.interface.new_socket(name="Alpha", in_out="INPUT", socket_type="NodeSocketFloat")
	group.interface.new_socket(name="Shader", in_out="OUTPUT", socket_type="NodeSocketShader")

	nodes = group.nodes
	links = group.links
	input_node = nodes.new("NodeGroupInput")
	input_node.location = (-420, 80)
	transparent = nodes.new("ShaderNodeBsdfTransparent")
	transparent.location = (-180, -80)
	emission = nodes.new("ShaderNodeEmission")
	emission.location = (-180, 120)
	mix = nodes.new("ShaderNodeMixShader")
	mix.location = (80, 80)
	output_node = nodes.new("NodeGroupOutput")
	output_node.location = (320, 80)

	links.new(input_node.outputs["Color"], emission.inputs["Color"])
	links.new(input_node.outputs["Alpha"], mix.inputs[0])
	links.new(transparent.outputs[0], mix.inputs[1])
	links.new(emission.outputs[0], mix.inputs[2])
	links.new(mix.outputs[0], output_node.inputs["Shader"])
	return group


def _create_material(name, image):
	material = bpy.data.materials.new(name=name)
	material[MATERIAL_TAG] = True
	material.use_nodes = True
	if hasattr(material, "surface_render_method"):
		material.surface_render_method = "DITHERED"

	nodes = material.node_tree.nodes
	nodes.clear()
	texture = nodes.new("ShaderNodeTexImage")
	texture.name = TEXTURE_NODE_NAME
	texture.label = "Image Mesh Source"
	texture[TEXTURE_NODE_TAG] = True
	texture.image = image
	texture.location = (-440, 80)
	group_node = nodes.new("ShaderNodeGroup")
	group_node.node_tree = _ensure_shader_group()
	group_node.location = (-140, 80)
	output = nodes.new("ShaderNodeOutputMaterial")
	output.location = (180, 80)

	links = material.node_tree.links
	links.new(texture.outputs["Color"], group_node.inputs["Color"])
	links.new(texture.outputs["Alpha"], group_node.inputs["Alpha"])
	links.new(group_node.outputs["Shader"], output.inputs["Surface"])
	return material


def _source_texture_node(material):
	if material is None or not material.use_nodes or material.node_tree is None:
		return None
	for node in material.node_tree.nodes:
		if node.bl_idname == "ShaderNodeTexImage" and node.get(TEXTURE_NODE_TAG):
			return node
	return None


def _material_is_shared(material, target_object):
	for obj in bpy.data.objects:
		if obj == target_object or obj.type != "MESH" or obj.data is None:
			continue
		if any(slot == material for slot in obj.data.materials):
			return True
	return False


def _stored_path(filepath):
	# Resolve Blender's // prefix before using os.path. Calling os.path.abspath
	# directly on a Blender-relative path treats it as an OS-rooted path and can
	# rewrite a valid source to the wrong location after the first update.
	absolute = _absolute_path(filepath)
	if bpy.data.filepath:
		return bpy.path.relpath(absolute)
	return absolute


def _absolute_path(filepath):
	return os.path.abspath(bpy.path.abspath(filepath))


def _load_and_build(filepath, settings, mesh_name):
	absolute = _absolute_path(filepath)
	if not os.path.isfile(absolute):
		raise FileNotFoundError(f"Source image not found: {absolute}")
	image = bpy.data.images.load(absolute, check_existing=False)
	try:
		mask, width, height = _alpha_mask(image)
		polygons = build_polygons(mask, width, height, settings)
		mesh = _build_mesh(
			mesh_name,
			polygons,
			width,
			height,
			settings.image_mesh_scale,
			settings.image_mesh_alignment,
		)
		image.filepath = _stored_path(absolute)
		return image, mesh, len(polygons)
	except Exception:
		bpy.data.images.remove(image)
		raise


def _source_path(obj):
	if obj is None or obj.type != "MESH":
		return None
	value = obj.get(SOURCE_PROPERTY)
	return value.strip() if isinstance(value, str) and value.strip() else None


def _set_source_path(obj, filepath):
	obj[SOURCE_PROPERTY] = _stored_path(filepath)
	obj.id_properties_ui(SOURCE_PROPERTY).update(
		description="Source image used to rebuild this Image Mesh object",
		subtype="FILE_PATH",
	)


def _managed_objects(objects):
	return [obj for obj in objects if _source_path(obj) is not None]


def _replace_managed_object(obj, filepath, settings):
	if obj is None or obj.type != "MESH":
		raise ValueError("Managed object is missing or is no longer a mesh")
	material = None
	texture_node = None
	for candidate in obj.data.materials:
		candidate_node = _source_texture_node(candidate)
		if candidate_node is not None:
			material = candidate
			texture_node = candidate_node
			break
	if material is None or texture_node is None:
		raise ValueError(f"{obj.name}: managed source texture node is missing")

	image, new_mesh, island_count = _load_and_build(filepath, settings, obj.data.name)
	old_mesh = obj.data
	old_image = texture_node.image
	new_material = material
	texture_replaced = False

	try:
		if _material_is_shared(material, obj):
			new_material = material.copy()
			new_material.name = material.name
			texture_node = _source_texture_node(new_material)
			if texture_node is None:
				raise ValueError(f"{obj.name}: copied material lost its source texture node")

		for slot_material in old_mesh.materials:
			new_mesh.materials.append(new_material if slot_material == material else slot_material)
		if not new_mesh.materials:
			new_mesh.materials.append(new_material)
		source_slot = next(
			(index for index, slot_material in enumerate(new_mesh.materials) if slot_material == new_material),
			0,
		)
		for polygon in new_mesh.polygons:
			polygon.material_index = source_slot

		texture_node.image = image
		texture_replaced = True
		obj.data = new_mesh
		_set_source_path(obj, filepath)
	except Exception:
		if texture_replaced and new_material == material:
			texture_node.image = old_image
		bpy.data.meshes.remove(new_mesh)
		if image.users == 0:
			bpy.data.images.remove(image)
		if new_material != material and new_material.users == 0:
			bpy.data.materials.remove(new_material)
		raise

	if old_mesh.users == 0:
		bpy.data.meshes.remove(old_mesh)
	if old_image is not None and old_image.users == 0:
		bpy.data.images.remove(old_image)
	return island_count


###########################################################################
# Operators

class OBJECT_OT_image_mesh_import(bpy.types.Operator, ImportHelper):
	"""Import one or more images as managed, segmented mesh objects"""
	bl_idname = "object.image_mesh_import"
	bl_label = "Import Images"
	bl_description = "Import one or more images as mesh objects using the current Image Mesh settings"
	bl_options = {"REGISTER", "UNDO"}

	filename_ext = ""
	filter_glob: bpy.props.StringProperty(
		default="*.bmp;*.cin;*.dds;*.dpx;*.exr;*.hdr;*.jpeg;*.jpg;*.jp2;*.png;*.psd;*.sgi;*.tga;*.tif;*.tiff;*.webp",
		options={"HIDDEN"},
	)
	files: bpy.props.CollectionProperty(type=bpy.types.OperatorFileListElement, options={"HIDDEN", "SKIP_SAVE"})
	directory: bpy.props.StringProperty(subtype="DIR_PATH", options={"HIDDEN", "SKIP_SAVE"})

	@classmethod
	def poll(cls, context):
		return context.mode == "OBJECT"

	def execute(self, context):
		settings = context.scene.mesh_kit_settings
		paths = [os.path.join(self.directory, item.name) for item in self.files]
		if not paths and self.filepath:
			paths = [self.filepath]
		created = []
		failures = []

		for filepath in paths:
			base_name = Path(filepath).stem
			image = mesh = material = obj = None
			try:
				image, mesh, _island_count = _load_and_build(filepath, settings, base_name)
				material = _create_material(base_name, image)
				mesh.materials.append(material)
				obj = bpy.data.objects.new(base_name, mesh)
				context.collection.objects.link(obj)
				obj.location = context.scene.cursor.location
				_set_source_path(obj, filepath)
				created.append(obj)
			except Exception as exc:
				if obj is not None and bpy.data.objects.get(obj.name) == obj:
					bpy.data.objects.remove(obj, do_unlink=True)
				if material is not None and material.users == 0:
					bpy.data.materials.remove(material)
				if mesh is not None and mesh.users == 0:
					bpy.data.meshes.remove(mesh)
				if image is not None and image.users == 0:
					bpy.data.images.remove(image)
				failures.append(f"{base_name}: {exc}")

		if created:
			for obj in context.selected_objects:
				obj.select_set(False)
			for obj in created:
				obj.select_set(True)
			context.view_layer.objects.active = created[-1]

		if failures:
			self.report({"WARNING"}, f"Imported {len(created)} image(s); {len(failures)} failed. See console")
			for failure in failures:
				print(f"Image Mesh import failed | {failure}")
		elif created:
			self.report({"INFO"}, f"Imported {len(created)} image mesh object(s)")

		return {"FINISHED"} if created else {"CANCELLED"}


class OBJECT_OT_image_mesh_update_selected(bpy.types.Operator):
	"""Rebuild selected managed image meshes from their source files"""
	bl_idname = "object.image_mesh_update_selected"
	bl_label = "Update Selected"
	bl_description = "Rebuild every selected Image Mesh object with the current settings"
	bl_options = {"REGISTER", "UNDO"}

	@classmethod
	def poll(cls, context):
		return context.mode == "OBJECT" and any(
			_source_path(obj) is not None for obj in context.selected_objects
		)

	def execute(self, context):
		settings = context.scene.mesh_kit_settings
		return _update_objects(self, _managed_objects(context.selected_objects), settings)


class OBJECT_OT_image_mesh_replace_active(bpy.types.Operator, ImportHelper):
	"""Replace the active managed image mesh with a different source image"""
	bl_idname = "object.image_mesh_replace_active"
	bl_label = "Replace Active"
	bl_description = "Choose a new source image for the active managed object, preserving its object and customized material"
	bl_options = {"REGISTER", "UNDO"}

	filename_ext = ""
	filter_glob: bpy.props.StringProperty(
		default="*.bmp;*.cin;*.dds;*.dpx;*.exr;*.hdr;*.jpeg;*.jpg;*.jp2;*.png;*.psd;*.sgi;*.tga;*.tif;*.tiff;*.webp",
		options={"HIDDEN"},
	)

	@classmethod
	def poll(cls, context):
		return (
			context.mode == "OBJECT"
			and context.active_object is not None
			and _source_path(context.active_object) is not None
		)

	def execute(self, context):
		settings = context.scene.mesh_kit_settings
		obj = context.active_object
		if _source_path(obj) is None:
			self.report({"ERROR"}, "Active object is not a managed Image Mesh object")
			return {"CANCELLED"}
		try:
			island_count = _replace_managed_object(obj, self.filepath, settings)
		except Exception as exc:
			self.report({"ERROR"}, str(exc))
			return {"CANCELLED"}
		self.report({"INFO"}, f"Replaced active image mesh ({island_count} island(s))")
		return {"FINISHED"}


def _update_objects(operator, objects, settings):
	updated = 0
	failures = []
	for obj in objects:
		try:
			_replace_managed_object(obj, _source_path(obj), settings)
			updated += 1
		except Exception as exc:
			failures.append(f"{obj.name}: {exc}")

	if failures:
		message = f"Updated {updated} object(s); {len(failures)} failed"
		operator.report({"WARNING"}, message + ". See console")
		for failure in failures:
			print(f"Image Mesh update failed | {failure}")
	elif updated:
		operator.report({"INFO"}, f"Updated {updated} image mesh object(s)")
	return {"FINISHED"} if updated else {"CANCELLED"}


###########################################################################
# Panel

class MESHKIT_PT_image_mesh(bpy.types.Panel):
	bl_label = "Image Mesh"
	bl_idname = "MESHKIT_PT_image_mesh"
	bl_space_type = "VIEW_3D"
	bl_region_type = "UI"
	bl_category = "Launch"
	bl_order = 36
	bl_options = {"DEFAULT_CLOSED"}
	category_preference = "imagemesh_category"

	def draw(self, context):
		settings = context.scene.mesh_kit_settings
		layout = self.layout
		layout.use_property_decorate = False
		layout.use_property_split = True

		layout.prop(settings, "image_mesh_segmentation")
		row = layout.row()
		row.active = settings.image_mesh_segmentation != "NONE"
		row.prop(settings, "image_mesh_threshold")
		row = layout.row()
		row.active = settings.image_mesh_segmentation in {"RECTILINEAR", "BOTH"}
		row.prop(settings, "image_mesh_iterations")
		row = layout.row()
		row.active = settings.image_mesh_segmentation in {"CONTOUR", "BOTH"}
		row.prop(settings, "image_mesh_detail")
		row = layout.row()
		row.active = settings.image_mesh_segmentation != "NONE"
		row.prop(settings, "image_mesh_sort")
		row = layout.row()
		row.active = settings.image_mesh_segmentation != "NONE" and settings.image_mesh_sort == "RANDOM"
		row.prop(settings, "image_mesh_seed")
		layout.prop(settings, "image_mesh_scale")

		box = layout.box()
		box.label(text="Alignment")
		for values, labels in (
			(("TOP_LEFT", "TOP", "TOP_RIGHT"), ("↖", "↑", "↗")),
			(("LEFT", "CENTER", "RIGHT"), ("←", "•", "→")),
			(("BOTTOM_LEFT", "BOTTOM", "BOTTOM_RIGHT"), ("↙", "↓", "↘")),
		):
			row = box.row(align=True)
			for value, label in zip(values, labels):
				row.prop_enum(settings, "image_mesh_alignment", value, text=label)

		layout.operator(OBJECT_OT_image_mesh_import.bl_idname, icon="IMAGE_DATA")

		obj = context.active_object
		source = _source_path(obj)
		if source is not None:
			box = layout.box()
			box.label(text="Active Image Mesh", icon="OBJECT_DATA")
			box.prop(obj, f'["{SOURCE_PROPERTY}"]', text="Source")
			absolute = _absolute_path(source)
			if os.path.isfile(absolute):
				box.label(text="Source file found", icon="CHECKMARK")
			else:
				box.label(text="Source file missing", icon="ERROR")

		grid = layout.grid_flow(row_major=True, columns=2, even_columns=True, even_rows=True, align=True)
		grid.operator(OBJECT_OT_image_mesh_update_selected.bl_idname, text="Update Selected")
		grid.operator(OBJECT_OT_image_mesh_replace_active.bl_idname, text="Replace Active")


classes = (
	OBJECT_OT_image_mesh_import,
	OBJECT_OT_image_mesh_update_selected,
	OBJECT_OT_image_mesh_replace_active,
)

panels = [MESHKIT_PT_image_mesh]


def register():
	for cls in classes:
		bpy.utils.register_class(cls)
	utility_panel.register_panels(panels)


def unregister():
	utility_panel.unregister_panels(panels)
	for cls in reversed(classes):
		bpy.utils.unregister_class(cls)


if __name__ == "__main__":
	register()
