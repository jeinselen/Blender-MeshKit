import bpy
import bmesh
from random import uniform
from random import randint
from random import shuffle
from copy import deepcopy
from mathutils import Vector
import math
import time

from . import utility_panel

# Frequently used constant: sine of 60° (used for hexagonal/triangular spacing)
SIN60 = 0.8660254037844386467637231707529361834714026269051903140279034897

###########################################################################
# Helper functions

def subdivide_count(initial, add, mult=4):
	# Total point count estimate for a subdivided array using the current division_levels and division_percentage settings
	settings = bpy.context.scene.mesh_kit_settings
	levels = settings.division_levels
	percentage = settings.division_percentage
	point_start = initial
	point_count = initial
	i = 0
	while i < levels:
		i += 1
		point_start *= percentage
		point_start = math.ceil(point_start) # fix the floating point discrepancy between this calculation and the simple "<" comparison in the loop code
		point_count += point_start * add
		point_start *= mult
	return int(point_count)

def estimate_qr(text, error):
	# Fast QR size estimate for the UI: finds the smallest version using a byte-mode upper bound (no error correction encoding)
	# Returns (version, module_size) or None if it can't be determined
	try:
		from segno import consts
		e = {'L': consts.ERROR_LEVEL_L, 'M': consts.ERROR_LEVEL_M, 'Q': consts.ERROR_LEVEL_Q, 'H': consts.ERROR_LEVEL_H}[error]
		bits = 8 * len(text.encode('utf-8'))
		for version in range(1, 41):
			overhead = 4 + (8 if version <= 9 else 16) # mode indicator + character count indicator
			capacity = consts.SYMBOL_CAPACITY.get(version, {}).get(e)
			if capacity is not None and capacity >= overhead + bits:
				return version, version * 4 + 17
	except Exception:
		pass
	return None

###########################################################################
# Main classes

class MeshKit_Point_Grid(bpy.types.Operator):
	bl_idname = "ops.meshkit_create_point_grid"
	bl_label = "Replace Mesh"
	bl_description = "Create a grid of points using the selected options, deleting and replacing the currently selected mesh"
	bl_options = {'REGISTER', 'UNDO'}
	
	def execute(self, context):
		grid_x = bpy.context.scene.mesh_kit_settings.grid_count[0] # X distribution radius
		grid_y = bpy.context.scene.mesh_kit_settings.grid_count[1] # Y distribution radius
		grid_z = bpy.context.scene.mesh_kit_settings.grid_count[2] # Z distribution radius
		scale_random = bpy.context.scene.mesh_kit_settings.scale_random
		scale_max = bpy.context.scene.mesh_kit_settings.scale_maximum # maximum radius of the generated point
		scale_min = bpy.context.scene.mesh_kit_settings.scale_minimum # minimum radius of the generated point
		space = scale_max*2.0 # Spacing of the grid elements
		rotation_rand = bpy.context.scene.mesh_kit_settings.rotation_random
		ground = bpy.context.scene.mesh_kit_settings.grid_ground
		
		# Get the selected object
		obj = bpy.context.object
		
		# Stop processing if no valid mesh is found
		if obj is None or obj.type != 'MESH':
			print('Mesh Kit Point Array error: no mesh object selected')
			return {'CANCELLED'}
		
		# Switch out of editing mode if active
		if obj.mode != 'OBJECT':
			object_mode = obj.mode
			bpy.ops.object.mode_set(mode = 'OBJECT')
		else:
			object_mode = None
		
		# Create a new bmesh
		bm = bmesh.new()
		
		# Set up attribute layers
		# We don't need to check for an existing vertex layer because this is a fresh Bmesh
		pf = bm.verts.layers.float.new('factor')
		pix = bm.verts.layers.int.new('index_x')
		piy = bm.verts.layers.int.new('index_y')
		piz = bm.verts.layers.int.new('index_z')
		ps = bm.verts.layers.float.new('scale')
		pr = bm.verts.layers.float_vector.new('rotation')
		
		# Advanced attribute layers
		relativeX = 0.0 if grid_x == 1 else 1.0 / ((float(grid_x) - 1) * space)
		relativeY = 0.0 if grid_y == 1 else 1.0 / ((float(grid_y) - 1) * space)
		relativeZ = 0.0 if grid_z == 1 else 1.0 / ((float(grid_z) - 1) * space)
		pu = bm.verts.layers.float_vector.new('position_relative')
		pd = bm.verts.layers.float.new('position_distance')
		
		# Range setup
		count = grid_x * grid_y * grid_z - 1.0
		i = 0
		
		# Create points
		for _y in range(0, grid_y): # Swizzled channel order to support Volume Fields export to Unity
			for _z in range(0, grid_z): # Swizzled channel order to support Volume Fields export to Unity
				for _x in range(0, grid_x):
					pointX = (float(_x) - grid_x*0.5 + 0.5)*space
					pointY = (float(_y) - grid_y*0.5 + 0.5)*space
					if ground:
						pointZ = (float(_z) + 0.5)*space
						positionRelative = Vector([pointX * relativeX * 2.0, pointY * relativeY * 2.0, pointZ * relativeZ])
					else:
						pointZ = (float(_z) - grid_z*0.5 + 0.5)*space
						positionRelative = Vector([pointX * relativeX * 2.0, pointY * relativeY * 2.0, pointZ * relativeZ * 2.0])
					v = bm.verts.new((pointX, pointY, pointZ))
					v[pf] = 0.0 if i == 0.0 else i / count
					v[pix] = _x
					v[piy] = _y
					v[piz] = _z
					v[ps] = scale_max if not scale_random else uniform(scale_min, scale_max)
					v[pr] = Vector([0.0, 0.0, 0.0]) if not rotation_rand else Vector([uniform(-math.pi, math.pi), uniform(-math.pi, math.pi), uniform(-math.pi, math.pi)])
					v[pu] = positionRelative
					v[pd] = positionRelative.length
					i += 1
		
		# Connect vertices
		if bpy.context.scene.mesh_kit_settings.polyline:
			bm.verts.ensure_lookup_table()
			for i in range(len(bm.verts)-1):
				bm.edges.new([bm.verts[i], bm.verts[i+1]])
		
		# Replace object with new mesh data
		bm.to_mesh(obj.data)
		bm.free()
		obj.data.update() # This ensures the viewport updates
		
		# Store the grid settings to custom mesh properties
		if obj.type == 'MESH':
			mesh = obj.data
			mesh['MeshKit_Point_Grid_x'] = grid_x
			mesh['MeshKit_Point_Grid_y'] = grid_y
			mesh['MeshKit_Point_Grid_z'] = grid_z
		
		# Reset to original mode
		if object_mode is not None:
			bpy.ops.object.mode_set(mode = object_mode)
		
		return {'FINISHED'}



class MeshKit_Point_Golden(bpy.types.Operator):
	bl_idname = "ops.meshkit_create_point_golden"
	bl_label = "Replace Mesh"
	bl_description = "Create a flat array of points using the golden angle, deleting and replacing the currently selected mesh"
	bl_options = {'REGISTER', 'UNDO'}
	
	def execute(self, context):
		count = bpy.context.scene.mesh_kit_settings.golden_count # X distribution radius
		scale_random = bpy.context.scene.mesh_kit_settings.scale_random
		scale_max = bpy.context.scene.mesh_kit_settings.scale_maximum # maximum radius of the generated point
		scale_min = bpy.context.scene.mesh_kit_settings.scale_minimum # minimum radius of the generated point
		space = scale_max # Spacing of the grid elements
		rotation_rand = bpy.context.scene.mesh_kit_settings.rotation_random
		fill = bpy.context.scene.mesh_kit_settings.golden_fill
		
		# Get the selected object
		obj = bpy.context.object
		
		# Stop processing if no valid mesh is found
		if obj is None or obj.type != 'MESH':
			print('Mesh Kit Point Array error: no mesh object selected')
			return {'CANCELLED'}
		
		# Switch out of editing mode if active
		if obj.mode != 'OBJECT':
			object_mode = obj.mode
			bpy.ops.object.mode_set(mode = 'OBJECT')
		else:
			object_mode = None
		
		# Create a new bmesh
		bm = bmesh.new()
		
		# Set up attribute layers
		pf = bm.verts.layers.float.new('factor')
		ps = bm.verts.layers.float.new('scale')
		pr = bm.verts.layers.float_vector.new('rotation')
		
		if fill:
			v = bm.verts.new((space * 0.8660254037844386467637231707529361834714026269051903140279034897, 0.0, 0.0)) # Magic value: sin(60°)
			v[pf] = 0
			v[ps] = scale_max if not scale_random else uniform(scale_min, scale_max)
			v[pr] = Vector([0.0, 0.0, 0.0]) if not rotation_rand else Vector([uniform(-math.pi, math.pi), uniform(-math.pi, math.pi), uniform(-math.pi, math.pi)])
			count -= 1
		
		for i in range(1, count+1): # The original code incorrectly set the starting vertex at 0...and while Fermat's Spiral can benefit from an extra point near the start, the exact centre does not work
			#theta = i * math.radians(137.5)
			theta = i * 2.3999632297286533222315555066336138531249990110581150429351127507 # many thanks to WolframAlpha for the numerical accuracy
			r = space * math.sqrt(i)
			v = bm.verts.new((math.cos(theta) * r, math.sin(theta) * r, 0.0))
			v[pf] = i / count if bpy.context.scene.mesh_kit_settings.golden_fill else (0.0 if i == 1 else (i - 1.0) / (count - 1.0))
			v[ps] = scale_max if not scale_random else uniform(scale_min, scale_max)
			v[pr] = Vector([0.0, 0.0, 0.0]) if not rotation_rand else Vector([uniform(-math.pi, math.pi), uniform(-math.pi, math.pi), uniform(-math.pi, math.pi)])
		
		# Connect vertices
		if bpy.context.scene.mesh_kit_settings.polyline:
			bm.verts.ensure_lookup_table()
			for i in range(len(bm.verts)-1):
				bm.edges.new([bm.verts[i], bm.verts[i+1]])
		
		# Replace object with new mesh data
		bm.to_mesh(obj.data)
		bm.free()
		obj.data.update() # This ensures the viewport updates
		
		# Reset to original mode
		if object_mode is not None:
			bpy.ops.object.mode_set(mode = object_mode)
		
		return {'FINISHED'}



class MeshKit_Point_Pack(bpy.types.Operator):
	bl_idname = "ops.meshkit_create_point_pack"
	bl_label = "Replace Mesh"
	bl_description = "Create points using the selected options, deleting and replacing the currently selected mesh"
	bl_options = {'REGISTER', 'UNDO'}
	
	def execute(self, context):
		elements = bpy.context.scene.mesh_kit_settings.max_elements # target number of points
		failures = bpy.context.scene.mesh_kit_settings.max_failures # maximum number of consecutive failures
		attempts = bpy.context.scene.mesh_kit_settings.max_attempts # maximum number of iterations to try and meet the target number of points
		shapeX = bpy.context.scene.mesh_kit_settings.area_size[0] * 0.5 # X distribution radius
		shapeY = bpy.context.scene.mesh_kit_settings.area_size[1] * 0.5 # Y distribution radius
		shapeZ = bpy.context.scene.mesh_kit_settings.area_size[2] * 0.5 # Z distribution radius
		circular = True if bpy.context.scene.mesh_kit_settings.area_shape == "CYLINDER" else False # enable circular masking
		spherical = True if bpy.context.scene.mesh_kit_settings.area_shape == "SPHERE" else False # enable spherical masking
		hull = True if bpy.context.scene.mesh_kit_settings.area_shape == "HULL" else False # enable spherical hull masking
		trim = bpy.context.scene.mesh_kit_settings.area_truncate * 2.0 - 1.0 # trim hull extent
		within = True if bpy.context.scene.mesh_kit_settings.area_alignment == "RADIUS" else False # enable radius compensation to force all elements to fit within the shape boundary
		scale_random = bpy.context.scene.mesh_kit_settings.scale_random
		scale_max = bpy.context.scene.mesh_kit_settings.scale_maximum # maximum radius of the generated point
		scale_min = scale_max if not scale_random else bpy.context.scene.mesh_kit_settings.scale_minimum # minimum radius of the generated point
		rotation_rand = bpy.context.scene.mesh_kit_settings.rotation_random
		
		# Get the selected object
		obj = bpy.context.object
		
		# Stop processing if no valid mesh is found
		if obj is None or obj.type != 'MESH':
			print('Mesh Kit Point Array error: no mesh object selected')
			return {'CANCELLED'}
		
		# Switch out of editing mode if active
		if obj.mode != 'OBJECT':
			object_mode = obj.mode
			bpy.ops.object.mode_set(mode = 'OBJECT')
		else:
			object_mode = None
		
		# Create a new bmesh
		bm = bmesh.new()
		
		# Set up attribute layers
		pf = bm.verts.layers.float.new('factor')
		ps = bm.verts.layers.float.new('scale')
		pr = bm.verts.layers.float_vector.new('rotation')
		
		# Advanced attribute layers...designed for some pretty specific projects, but may be helpful in others
		relativeX = 0.0 if shapeX == 0.0 else 1.0 / shapeX
		relativeY = 0.0 if shapeY == 0.0 else 1.0 / shapeY
		relativeZ = 0.0 if shapeZ == 0.0 else 1.0 / shapeZ
		pu = bm.verts.layers.float_vector.new('position_relative')
		pd = bm.verts.layers.float.new('position_distance')
		
		# Start timer
		timer = str(time.time())
		
		# Create points with poisson disc sampling
		points = []
		count = 0
		failmax = 0 # This is entirely for reporting purposes and is not needed structurally
		iteration = 0
		
		# Loop until we're too tired to continue...
		while len(points) < elements and count < failures and iteration < attempts:
			iteration += 1
			count += 1
			# Create check system (this prevents unnecessary cycles by exiting early if possible)
			check = 0
			
			# Generate random radius
			radius = uniform(scale_min, scale_max)
			
			# Create volume
			x = shapeX
			y = shapeY
			z = shapeZ
			
			if hull:
				# Create normalised vector for the hull shape
				# This is a super easy way to generate random, albeit NOT evenly random, hulls...only works at full size, and begins to exhibit corner density when the trim value is above -1
				temp = Vector([uniform(-1.0, 1.0), uniform(-1.0, 1.0), uniform(trim, 1.0)]).normalized()
				# Check to see if the point is too far out of bounds
				if (temp[2] < trim):
					check = 1
				# Create point definition with radius
				point = [temp[0]*x, temp[1]*y, temp[2]*z, radius]
			else:
				# Set up edge limits (if enabled)
				if within:
					x -= radius
					y -= radius
					z -= radius
				# Prevent divide-by-zero errors
				x = max(x, 0.0000001)
				y = max(y, 0.0000001)
				z = max(z, 0.0000001)
				# Create point definition with radius
				point = [uniform(-x, x), uniform(-y, y), uniform(-z, z), radius]
				# Check if point is within circular or spherical bounds (if enabled)
				if spherical:
					check = int(Vector([point[0]/x, point[1]/y, point[2]/z]).length)
				elif circular:
					check = int(Vector([point[0]/x, point[1]/y, 0.0]).length)
			
			# Check if it overlaps with other radii
			i = 0
			while i < len(points) and check == 0:
				if Vector([points[i][0]-point[0], points[i][1]-point[1], points[i][2]-point[2]]).length < (points[i][3] + point[3]):
					check = 1
				i += 1
			
			# If no collisions are detected, add the point to the list and reset the failure counter
			if check == 0:
				points.append(point)
				failmax = max(failmax, count) # This is entirely for reporting purposes and is not needed structurally
				# if count > failuresHalf: # This is a hard-coded efficiency attempt, dropping the maximum scale if we're getting a lot of failures
				# 	scale_max = mediumR
				count = 0
		
		# One last check, in case the stop cause was maximum failure count and this value wasn't updated in a successful check status
		failmax = max(failmax, count) # This is entirely for reporting purposes and is not needed structurally
		
		# Range setup
		count = len(points) - 1.0
		i = 0.0
		
		# This creates vertices from the points list
		for p in points:
			v = bm.verts.new((p[0], p[1], p[2]))
			v[pf] = 0.0 if i == 0.0 else i / count
			i += 1.0
			v[ps] = p[3]
			v[pr] = Vector([0.0, 0.0, 0.0]) if not rotation_rand else Vector([uniform(-math.pi, math.pi), uniform(-math.pi, math.pi), uniform(-math.pi, math.pi)])
			positionRelative = Vector([p[0] * relativeX, p[1] * relativeY, p[2] * relativeZ])
			v[pu] = positionRelative
			v[pd] = positionRelative.length
		
		# Update the feedback strings
		context.scene.mesh_kit_settings.feedback_elements = str(len(points))
		context.scene.mesh_kit_settings.feedback_failures = str(failmax)
		context.scene.mesh_kit_settings.feedback_attempts = str(iteration)
		context.scene.mesh_kit_settings.feedback_time = str(round(time.time() - float(timer), 2))
		
		# Connect vertices
		if bpy.context.scene.mesh_kit_settings.polyline:
			bm.verts.ensure_lookup_table()
			for i in range(len(bm.verts)-1):
				bm.edges.new([bm.verts[i], bm.verts[i+1]])
		
		# Replace object with new mesh data
		bm.to_mesh(obj.data)
		bm.free()
		obj.data.update() # This ensures the viewport updates
		
		# Reset to original mode
		if object_mode is not None:
			bpy.ops.object.mode_set(mode = object_mode)
		
		return {'FINISHED'}



class MeshKit_Point_Rectangle(bpy.types.Operator):
	bl_idname = "ops.meshkit_create_point_rectangle"
	bl_label = "Replace Mesh"
	bl_description = "Create a rectangular array of subdividing square points, deleting and replacing the currently selected mesh"
	bl_options = {'REGISTER', 'UNDO'}

	def execute(self, context):
		# Properties settings
		grid_x = bpy.context.scene.mesh_kit_settings.array_count[0]
		grid_y = bpy.context.scene.mesh_kit_settings.array_count[1]
		radius = bpy.context.scene.mesh_kit_settings.scale_maximum
		rotation_rand = bpy.context.scene.mesh_kit_settings.rotation_random
		# Recursion settings
		recursion = bpy.context.scene.mesh_kit_settings.division_levels
		percentage = bpy.context.scene.mesh_kit_settings.division_percentage

		# Get the selected object
		obj = bpy.context.object

		# Stop processing if no valid mesh is found
		if obj is None or obj.type != 'MESH':
			print('Mesh Kit Point Array error: no mesh object selected')
			return {'CANCELLED'}

		# Switch out of editing mode if active
		if obj.mode != 'OBJECT':
			object_mode = obj.mode
			bpy.ops.object.mode_set(mode = 'OBJECT')
		else:
			object_mode = None

		# Create a new bmesh
		bm = bmesh.new()

		# Set up attribute layers
		pf = bm.verts.layers.float.new('factor')
		ps = bm.verts.layers.float.new('scale')
		pr = bm.verts.layers.float_vector.new('rotation')

		# Create initial grid
		grid = []
		for x in range(0, grid_x):
			for y in range(0, grid_y):
				grid.append([(float(x) - grid_x*0.5 + 0.5)*radius*2, (float(y) - grid_y*0.5 + 0.5)*radius*2, 0.0, radius])

		# Subdivide the grid
		rec = 0
		gridA = []
		gridB = []
		while rec < recursion:
			rec += 1
			shuffle(grid)
			for i, p in enumerate(grid):
				if float(i) / float(len(grid)) < percentage:
					gridA.append([p[0] + (p[3] * 0.5), p[1] - (p[3] * 0.5), p[2], p[3] * 0.5])
					gridA.append([p[0] + (p[3] * 0.5), p[1] + (p[3] * 0.5), p[2], p[3] * 0.5])
					gridA.append([p[0] - (p[3] * 0.5), p[1] + (p[3] * 0.5), p[2], p[3] * 0.5])
					gridA.append([p[0] - (p[3] * 0.5), p[1] - (p[3] * 0.5), p[2], p[3] * 0.5])
				else:
					gridB.append(p)
			grid = deepcopy(gridA)
			gridA.clear()

		shuffle(grid)
		gridB.extend(grid)

		# Create vertices from the points list
		for i, p in enumerate(gridB):
			v = bm.verts.new((p[0], p[1], p[2]))
			v[pf] = 0.0 if i == 0 else float(i) / float(len(gridB) - 1)
			v[ps] = p[3]
			if rotation_rand:
				v[pr] = Vector([0.0, 0.0, float(randint(0, 3)) * 1.570796326794896619231321691639751]) # 90° in radians
			else:
				v[pr] = Vector([0.0, 0.0, 0.0])

		# Connect vertices
		if bpy.context.scene.mesh_kit_settings.polyline:
			bm.verts.ensure_lookup_table()
			for i in range(len(bm.verts)-1):
				bm.edges.new([bm.verts[i], bm.verts[i+1]])

		# Replace object with new mesh data
		bm.to_mesh(obj.data)
		bm.free()
		obj.data.update() # This ensures the viewport updates

		# Reset to original mode
		if object_mode is not None:
			bpy.ops.object.mode_set(mode = object_mode)

		return {'FINISHED'}



class MeshKit_Point_Triangle(bpy.types.Operator):
	bl_idname = "ops.meshkit_create_point_triangle"
	bl_label = "Replace Mesh"
	bl_description = "Create a triangular array of subdividing triangular points, deleting and replacing the currently selected mesh"
	bl_options = {'REGISTER', 'UNDO'}

	def execute(self, context):
		# Properties settings
		count = bpy.context.scene.mesh_kit_settings.array_count[0]
		radius = bpy.context.scene.mesh_kit_settings.scale_maximum
		rotation_rand = bpy.context.scene.mesh_kit_settings.rotation_random
		offset = count * radius
		# Recursion settings
		recursion = bpy.context.scene.mesh_kit_settings.division_levels
		percentage = bpy.context.scene.mesh_kit_settings.division_percentage
		# Positional variables
		x = radius * SIN60 # sine 60°
		y = radius * 0.5 # cosine 60°

		# Get the selected object
		obj = bpy.context.object

		# Stop processing if no valid mesh is found
		if obj is None or obj.type != 'MESH':
			print('Mesh Kit Point Array error: no mesh object selected')
			return {'CANCELLED'}

		# Switch out of editing mode if active
		if obj.mode != 'OBJECT':
			object_mode = obj.mode
			bpy.ops.object.mode_set(mode = 'OBJECT')
		else:
			object_mode = None

		# Create a new bmesh
		bm = bmesh.new()

		# Set up attribute layers
		pf = bm.verts.layers.float.new('factor')
		ps = bm.verts.layers.float.new('scale')
		pr = bm.verts.layers.float_vector.new('rotation')

		# Create initial grid
		grid = []
		for a in range(0, count):
			for b in range(0, a * 2 + 1):
				# Hexagonal grid points with triangular directions are created, and then shifted in counter-clockwise directions to fill out each row
				# A = column start
				# B = row offset
				odd = math.floor(b % 2)
				rotation = math.pi if odd == 0 else 0.0 # determine the orientation of the element
					# Triangular array (just the top-middle of the Tri-Hex pattern)
				grid.append([(float(a) - float(b)) * x, (float(a) * 1.5 + 1.0 - odd * 0.5) * radius - offset, 0.0, radius, rotation])

		# Subdivide the grid (same as the Tri-Hex pattern)
		rec = 0
		gridA = []
		gridB = []
		while rec < recursion:
			rec += 1
			shuffle(grid)
			for i, p in enumerate(grid):
				if (float(i) / float(len(grid))) < percentage:
					# Recursion variables
					s = 1.0 if p[4] < 1.0 else -1.0 # determine the orientation of the element, which will flip all of our coordinates as needed
					s /= (2.0 ** float(rec)) # scale multiplier based on the current recursion level
					r = radius * abs(s) # calculate radius for this recursion level
					rotationA = math.pi if s < 0.0 else 0.0 # invert the rotation of the original point
					rotationB = math.pi if rotationA == 0.0 else 0.0 # invert it again
					# Divide triangular space into four elements
						# middle
					gridA.append([p[0], p[1], 0.0, r, rotationB])
						# top
					gridA.append([p[0], p[1] + radius * s, 0.0, r, rotationA])
						# lower left
					gridA.append([p[0] + x * s, p[1] - radius * s * 0.5, 0.0, r, rotationA])
						# lower right
					gridA.append([p[0] - x * s, p[1] - radius * s * 0.5, 0.0, r, rotationA])
				else:
					gridB.append(p)
			grid = deepcopy(gridA)
			gridA.clear()

		shuffle(grid)
		gridB.extend(grid)

		# Create vertices from the points list
		for i, p in enumerate(gridB):
			v = bm.verts.new((p[0], p[1], p[2]))
			v[pf] = 0.0 if i == 0 else float(i) / float(len(gridB) - 1)
			v[ps] = p[3]
			if rotation_rand:
				v[pr] = Vector([0.0, 0.0, p[4] + float(randint(0, 2)) * 2.094395102393195492308428922186335]) # 120° in radians
			else:
				v[pr] = Vector([0.0, 0.0, p[4]])

		# Connect vertices
		if bpy.context.scene.mesh_kit_settings.polyline:
			bm.verts.ensure_lookup_table()
			for i in range(len(bm.verts)-1):
				bm.edges.new([bm.verts[i], bm.verts[i+1]])

		# Replace object with new mesh data
		bm.to_mesh(obj.data)
		bm.free()
		obj.data.update() # This ensures the viewport updates

		# Reset to original mode
		if object_mode is not None:
			bpy.ops.object.mode_set(mode = object_mode)

		return {'FINISHED'}



class MeshKit_Point_TriHex(bpy.types.Operator):
	bl_idname = "ops.meshkit_create_point_trihex"
	bl_label = "Replace Mesh"
	bl_description = "Create a hexagonal array of subdividing triangular points, deleting and replacing the currently selected mesh"
	bl_options = {'REGISTER', 'UNDO'}

	def execute(self, context):
		# Properties settings
		count = bpy.context.scene.mesh_kit_settings.array_count[0]
		radius = bpy.context.scene.mesh_kit_settings.scale_maximum
		rotation_rand = bpy.context.scene.mesh_kit_settings.rotation_random
		# Recursion settings
		recursion = bpy.context.scene.mesh_kit_settings.division_levels
		percentage = bpy.context.scene.mesh_kit_settings.division_percentage
		# Positional variables
		x = radius * SIN60 # sine 60°
		y = radius * 0.5 # cosine 60°

		# Get the selected object
		obj = bpy.context.object

		# Stop processing if no valid mesh is found
		if obj is None or obj.type != 'MESH':
			print('Mesh Kit Point Array error: no mesh object selected')
			return {'CANCELLED'}

		# Switch out of editing mode if active
		if obj.mode != 'OBJECT':
			object_mode = obj.mode
			bpy.ops.object.mode_set(mode = 'OBJECT')
		else:
			object_mode = None

		# Create a new bmesh
		bm = bmesh.new()

		# Set up attribute layers
		pf = bm.verts.layers.float.new('factor')
		ps = bm.verts.layers.float.new('scale')
		pr = bm.verts.layers.float_vector.new('rotation')

		# Create initial grid
		grid = []
		for a in range(0, count):
			for b in range(0, a * 2 + 1):
				# Hexagonal grid points with triangular directions are created, and then shifted in counter-clockwise directions to fill out each row
				# A = column start
				# B = row offset
				odd = math.floor(b % 2)
				rotA = 0.0 if odd == 0 else math.pi # determine the orientation of the element
				rotB = math.pi if odd == 0 else 0.0 # determine the orientation of the element
					# top-middle
				grid.append([(float(a) - float(b)) * x, (float(a) * 1.5 + 1.0 - odd * 0.5) * radius, 0.0, radius, rotB])
					# top-right
				grid.append([(float(a * 2 + 1) - math.floor(float(b) * 0.5 + 0.5)) * x, (float(b) * 1.5 + 1.0 - odd * 0.5) * 0.5 * radius, 0.0, radius, rotA])
					# top-left (x-mirror of top-right)
				grid.append([(float(a * 2 + 1) - math.floor(float(b) * 0.5 + 0.5)) * -x, (float(b) * 1.5 + 1.0 - odd * 0.5) * 0.5 * radius, 0.0, radius, rotA])
					# bottom-middle (y-mirror of top-middle)
				grid.append([(float(a) - float(b)) * x, (float(a) * 1.5 + 1.0 - odd * 0.5) * -radius, 0.0, radius, rotA])
					# bottom-right (y-mirror of top-right)
				grid.append([(float(a * 2 + 1) - math.floor(float(b) * 0.5 + 0.5)) * x, (float(b) * 1.5 + 1.0 - odd * 0.5) * 0.5 * -radius, 0.0, radius, rotB])
					# bottom-left (x&y-mirror of top-right)
				grid.append([(float(a * 2 + 1) - math.floor(float(b) * 0.5 + 0.5)) * -x, (float(b) * 1.5 + 1.0 - odd * 0.5) * 0.5 * -radius, 0.0, radius, rotB])

		# Subdivide the grid
		rec = 0
		gridA = []
		gridB = []
		while rec < recursion:
			rec += 1
			shuffle(grid)
			for i, p in enumerate(grid):
				if (float(i) / float(len(grid))) < percentage:
					# Recursion variables
					s = 1.0 if p[4] < 1.0 else -1.0 # determine the orientation of the element, which will flip all of our coordinates as needed
					s /= (2.0 ** float(rec)) # scale multiplier based on the current recursion level
					r = radius * abs(s) # calculate radius for this recursion level
					rotationA = math.pi if s < 0.0 else 0.0 # invert the rotation of the original point
					rotationB = math.pi if rotationA == 0.0 else 0.0 # invert it again
					# Divide triangular space into four elements
						# middle
					gridA.append([p[0], p[1], 0.0, r, rotationB])
						# top
					gridA.append([p[0], p[1] + radius * s, 0.0, r, rotationA])
						# lower left
					gridA.append([p[0] + x * s, p[1] - radius * s * 0.5, 0.0, r, rotationA])
						# lower right
					gridA.append([p[0] - x * s, p[1] - radius * s * 0.5, 0.0, r, rotationA])
				else:
					gridB.append(p)
			grid = deepcopy(gridA)
			gridA.clear()

		shuffle(grid)
		gridB.extend(grid)

		# Create vertices from the points list
		for i, p in enumerate(gridB):
			v = bm.verts.new((p[0], p[1], p[2]))
			v[pf] = 0.0 if i == 0 else float(i) / float(len(gridB) - 1)
			v[ps] = p[3]
			if rotation_rand:
				v[pr] = Vector([0.0, 0.0, p[4] + float(randint(0, 2)) * 2.094395102393195492308428922186335]) # 120° in radians
			else:
				v[pr] = Vector([0.0, 0.0, p[4]])

		# Connect vertices
		if bpy.context.scene.mesh_kit_settings.polyline:
			bm.verts.ensure_lookup_table()
			for i in range(len(bm.verts)-1):
				bm.edges.new([bm.verts[i], bm.verts[i+1]])

		# Replace object with new mesh data
		bm.to_mesh(obj.data)
		bm.free()
		obj.data.update() # This ensures the viewport updates

		# Reset to original mode
		if object_mode is not None:
			bpy.ops.object.mode_set(mode = object_mode)

		return {'FINISHED'}



class MeshKit_Point_Hexagon(bpy.types.Operator):
	bl_idname = "ops.meshkit_create_point_hexagon"
	bl_label = "Replace Mesh"
	bl_description = "Create a hexagonal array of subdividing hexagonal points, deleting and replacing the currently selected mesh"
	bl_options = {'REGISTER', 'UNDO'}

	def execute(self, context):
		# Properties settings
		count = bpy.context.scene.mesh_kit_settings.array_count[0]
		radius = bpy.context.scene.mesh_kit_settings.scale_maximum
		rotation_rand = bpy.context.scene.mesh_kit_settings.rotation_random
		space = radius * 2.0 * SIN60 # compensate the spacing for a "furthest-point" radius (which is how hexagons are generated using Cylinders in Blender) not a "flat side" radius (which is a larger object)
		# Recursion settings
		recursion = bpy.context.scene.mesh_kit_settings.division_levels
		percentage = bpy.context.scene.mesh_kit_settings.division_percentage
		# Positional variables
		x = space * 0.5 # cosine 60°
		y = space * SIN60 # sine 60°

		# Get the selected object
		obj = bpy.context.object

		# Stop processing if no valid mesh is found
		if obj is None or obj.type != 'MESH':
			print('Mesh Kit Point Array error: no mesh object selected')
			return {'CANCELLED'}

		# Switch out of editing mode if active
		if obj.mode != 'OBJECT':
			object_mode = obj.mode
			bpy.ops.object.mode_set(mode = 'OBJECT')
		else:
			object_mode = None

		# Create a new bmesh
		bm = bmesh.new()

		# Set up attribute layers
		pf = bm.verts.layers.float.new('factor')
		ps = bm.verts.layers.float.new('scale')
		pr = bm.verts.layers.float_vector.new('rotation')

		# Create initial grid
		grid = []
		grid.append([0.0, 0.0, 0.0, radius])
		for a in range(1, count):
			for b in range(0, a):
				# Hexagonal grid points are created, and then shifted in counter-clockwise directions to fill out each row
				# A = column start
				# B = row offset
					# upper left column and row
				grid.append([float(a) * x - float(b) * space, float(a) * y, 0.0, radius])
					# left
				grid.append([float(a) * space - float(b) * x, float(b) * y, 0.0, radius])
					# lower left
				grid.append([float(a + b) * x, float(-a + b) * y, 0.0, radius])
					# lower right
				grid.append([float(-a) * x + float(b) * space, float(-a) * y, 0.0, radius])
					# right
				grid.append([float(-a) * space + float(b) * x, float(-b) * y, 0.0, radius])
					# upper right
				grid.append([float(-a - b) * x, float(a - b) * y, 0.0, radius])

		# Subdivide the grid
		rec = 0
		gridA = []
		gridB = []
		while rec < recursion:
			rec += 1
			shuffle(grid)
			for i, p in enumerate(grid):
				# Recursion scaler (Euler's Constant is the magic number that fixes everything)
				s = (1.0 / (2.0 ** float(rec))) * 0.57721566490153286060651209008240243104215933593992
				if rotation_rand and randint(0, 1) == 0: # randomly flip the layout values to prevent recursive triangle formations (thanks to hexagons not dividing into more hexagons)
					s = -s
				r = p[3] * 0.5
				if float(i) / float(len(grid)) < percentage:
					# Divide hexagon space into three (hexagons don't evenly divide into more hexagons, so this is the compromise we're making)
						# top
					gridA.append([p[0], p[1] + space * s, 0.0, r])
						# lower left
					gridA.append([p[0] + y * s, p[1] - x * s, 0.0, r])
						# lower right
					gridA.append([p[0] - y * s, p[1] - x * s, 0.0, r])
				else:
					gridB.append(p)
			grid = deepcopy(gridA)
			gridA.clear()

		shuffle(grid)
		gridB.extend(grid)

		# Create vertices from the points list
		for i, p in enumerate(gridB):
			v = bm.verts.new((p[0], p[1], p[2]))
			v[pf] = 0.0 if i == 0 else float(i) / float(len(gridB) - 1)
			v[ps] = p[3]
			if rotation_rand:
				v[pr] = Vector([0.0, 0.0, float(randint(0, 5)) * 1.047197551196597746154214461093168]) # 60° in radians
			else:
				v[pr] = Vector([0.0, 0.0, 0.0])

		# Connect vertices
		if bpy.context.scene.mesh_kit_settings.polyline:
			bm.verts.ensure_lookup_table()
			for i in range(len(bm.verts)-1):
				bm.edges.new([bm.verts[i], bm.verts[i+1]])

		# Replace object with new mesh data
		bm.to_mesh(obj.data)
		bm.free()
		obj.data.update() # This ensures the viewport updates

		# Reset to original mode
		if object_mode is not None:
			bpy.ops.object.mode_set(mode = object_mode)

		return {'FINISHED'}



class MeshKit_Point_Walk(bpy.types.Operator):
	bl_idname = "ops.meshkit_create_point_walk"
	bl_label = "Replace Mesh"
	bl_description = "Create a random walk string of points using poisson disc sampling, deleting and replacing the currently selected mesh"
	bl_options = {'REGISTER', 'UNDO'}

	def execute(self, context):
		# Recursion settings
		elements = bpy.context.scene.mesh_kit_settings.max_elements # target number of points
		failures = bpy.context.scene.mesh_kit_settings.max_failures # maximum number of consecutive failures
		attempts = bpy.context.scene.mesh_kit_settings.max_attempts # maximum number of iterations to try and meet the target number of points
		# Properties settings
		dimensions = True if bpy.context.scene.mesh_kit_settings.walk_dimensions == "3D" else False
		directionality = bpy.context.scene.mesh_kit_settings.walk_directionality
		direction_vector = bpy.context.scene.mesh_kit_settings.walk_vector
		rotation = bpy.context.scene.mesh_kit_settings.walk_rotation
		scale_random = bpy.context.scene.mesh_kit_settings.scale_random
		rMaximum = bpy.context.scene.mesh_kit_settings.scale_maximum # maximum radius of the generated point
		rMinimum = bpy.context.scene.mesh_kit_settings.scale_minimum if scale_random else rMaximum # minimum radius of the generated point
		rDecay = bpy.context.scene.mesh_kit_settings.walk_decay

		# Get the selected object
		obj = bpy.context.object

		# Stop processing if no valid mesh is found
		if obj is None or obj.type != 'MESH':
			print('Mesh Kit Point Array error: no mesh object selected')
			return {'CANCELLED'}

		# Switch out of editing mode if active
		if obj.mode != 'OBJECT':
			object_mode = obj.mode
			bpy.ops.object.mode_set(mode = 'OBJECT')
		else:
			object_mode = None

		# Create a new bmesh
		bm = bmesh.new()

		# Set up attribute layers
		pf = bm.verts.layers.float.new('factor')
		ps = bm.verts.layers.float.new('scale')
		pr = bm.verts.layers.float_vector.new('rotation')

		# Start timer
		timer = str(time.time())

		# Create points with poisson disc sampling
		points = []
		count = 0
		failmax = 0 # This is entirely for reporting purposes and is not needed structurally
		iteration = 0
		rPrevious = 0.0 # This stores the radius of the previous iteration so we can offset the current iteration correctly
		pPrevious = Vector([0.0, 0.0, 0.0])

		# Loop until we're too tired to continue...
		while len(points) < elements and count < failures and iteration < attempts:
			iteration += 1
			count += 1

			# Create check system (this prevents unnecessary cycles by exiting early if possible)
			check = 0

			# Generate random radius
			if rDecay:
				lerp = len(points) / elements
				radius = uniform(rMinimum, (rMinimum * lerp) + (rMaximum * (1.0 - lerp)))
			else:
				radius = uniform(rMinimum, rMaximum)

			# If this is the first iteration, just add a point at 0,0,0
			if len(points) == 0:
				points.append([0.0, 0.0, 0.0, radius])
				rPrevious = radius
				# And quit early (no need to check anything)
				continue

			# Generate random vector
			if dimensions:
				vec = Vector([uniform(-1.0, 1.0), uniform(-1.0, 1.0), uniform(-1.0, 1.0)])
			else:
				vec = Vector([uniform(-1.0, 1.0), uniform(-1.0, 1.0), 0.0])
			# Blend
			if directionality > 0.0:
				vec = vec.lerp(direction_vector, directionality)
			# Normalise
			vec = vec.normalized()

			# Scale and offset the random vector using the radius of the previous iteration and the current iteration, along with the previous position
			vec *= radius + rPrevious
			vec += pPrevious
			# Don't replace the previous radius and position variables until after we've determined if this current point is going to work

			# Create point data array
			point = [vec[0], vec[1], vec[2], radius]

			# Check if it overlaps with other radii
			i = 0
			while i < len(points) and check == 0:
				if Vector([points[i][0]-point[0], points[i][1]-point[1], points[i][2]-point[2]]).length < (points[i][3] + point[3]):
					check = 1
				i += 1

			# If no collisions are detected, add the point to the list and reset the failure counter
			if check == 0:
				points.append(point)
				# Finally, we have a winner! We can replace the previous radius and position variables
				rPrevious = radius
				pPrevious = vec
				# And now some data housekeeping
				failmax = max(failmax, count) # This is entirely for reporting purposes and is not needed structurally
				count = 0

		# One last check, in case the stop cause was maximum failure count and this value wasn't updated in a successful check status
		failmax = max(failmax, count) # This is entirely for reporting purposes and is not needed structurally

		pointsEnd = len(points) - 1
		# Create vertices from the points list
		for i, p in enumerate(points):
			v = bm.verts.new((p[0], p[1], p[2]))
			v[pf] = 0.0 if i == 0 else float(i) / float(len(points) - 1)
			v[ps] = p[3]
			# Point rotations
			tempX = 0.0
			tempY = 0.0
			tempZ = 0.0
			if rotation == "AHEAD":
				if i < pointsEnd:
					tempX = points[i+1][0] - p[0]
					tempY = points[i+1][1] - p[1]
					tempZ = points[i+1][2] - p[2]
				v[pr] = Vector([tempX, tempY, tempZ]).to_track_quat('X', 'Z').to_euler()
			elif rotation == "BEHIND":
				if i == 0:
					if pointsEnd > 0:
						tempX = points[1][0] - p[0]
						tempY = points[1][1] - p[1]
						tempZ = points[1][2] - p[2]
				else:
					tempX = p[0] - points[i-1][0]
					tempY = p[1] - points[i-1][1]
					tempZ = p[2] - points[i-1][2]
				v[pr] = Vector([tempX, tempY, tempZ]).to_track_quat('-X', 'Z').to_euler()
			else:
				v[pr] = Vector([uniform(-math.pi, math.pi), uniform(-math.pi, math.pi), uniform(-math.pi, math.pi)])

		# Update the feedback strings
		context.scene.mesh_kit_settings.feedback_elements = str(len(points))
		context.scene.mesh_kit_settings.feedback_failures = str(failmax)
		context.scene.mesh_kit_settings.feedback_attempts = str(iteration)
		context.scene.mesh_kit_settings.feedback_time = str(round(time.time() - float(timer), 2))

		# Connect vertices
		if bpy.context.scene.mesh_kit_settings.polyline:
			bm.verts.ensure_lookup_table()
			for i in range(len(bm.verts)-1):
				bm.edges.new([bm.verts[i], bm.verts[i+1]])

		# Replace object with new mesh data
		bm.to_mesh(obj.data)
		bm.free()
		obj.data.update() # This ensures the viewport updates

		# Reset to original mode
		if object_mode is not None:
			bpy.ops.object.mode_set(mode = object_mode)

		return {'FINISHED'}



class MeshKit_Point_QR(bpy.types.Operator):
	bl_idname = "ops.meshkit_create_point_qr"
	bl_label = "Replace Mesh"
	bl_description = "Encode a string as a QR code, generating a point per dark module with edges between adjacent modules, deleting and replacing the currently selected mesh"
	bl_options = {'REGISTER', 'UNDO'}

	def execute(self, context):
		settings = bpy.context.scene.mesh_kit_settings
		text = settings.qr_string
		error = settings.qr_error
		invert = settings.qr_invert == 'BACKGROUND'
		polygons = settings.qr_output == 'POLYGONS'
		single = settings.qr_corners == 'POINT'
		radius = settings.scale_maximum
		space = radius * 2.0 # Module spacing (each module fills the space edge-to-edge)

		# QR encoding is provided by the bundled "segno" wheel (see blender_manifest.toml)
		try:
			import segno
		except ImportError:
			self.report({'ERROR'}, "QR Code generator unavailable: the 'segno' dependency failed to load. Try reinstalling the extension.")
			return {'CANCELLED'}

		if not text:
			self.report({'ERROR'}, "QR Code text is empty")
			return {'CANCELLED'}

		# Get the selected object
		obj = bpy.context.object

		# Stop processing if no valid mesh is found
		if obj is None or obj.type != 'MESH':
			print('Mesh Kit Point Array error: no mesh object selected')
			return {'CANCELLED'}

		# Encode the string
		# make_qr() forces a standard QR symbol (three finder patterns); make() could return a Micro QR with only one
		# boost_error=False keeps the exact error correction level the user selected (segno otherwise silently upgrades it)
		try:
			qr = segno.make_qr(text, error=error, boost_error=False)
		except Exception as exc:
			self.report({'ERROR'}, "QR Code encoding failed: " + str(exc))
			return {'CANCELLED'}

		# Read the module matrix (no quiet zone); matrix[row][col] == 1 for dark modules
		matrix = [list(row) for row in qr.matrix]
		size = len(matrix)

		# Identify the three finder patterns (7x7 blocks anchored to the top-left, top-right, and bottom-left corners)
		finder_origins = [(0, 0), (0, size - 7), (size - 7, 0)]

		def finder_region(r, c):
			# Returns 'inner' (central 3x3), 'outer' (surrounding ring), or None
			for fr, fc in finder_origins:
				if fr <= r <= fr + 6 and fc <= c <= fc + 6:
					lr, lc = r - fr, c - fc
					if 2 <= lr <= 4 and 2 <= lc <= 4:
						return 'inner'
					if lr in (0, 6) or lc in (0, 6):
						return 'outer'
					return 'outer' # Any other dark module inside the block (defensive)
			return None

		def in_finder(r, c):
			for fr, fc in finder_origins:
				if fr <= r <= fr + 6 and fc <= c <= fc + 6:
					return True
			return False

		# Build the set of grid point modules and their region classification
		# region: 0 = finder inner, 1 = finder outer, 2 = data, 3 = single finder marker
		# In background mode the light modules become the geometry instead of the dark ones (the negative space);
		# only the finder white-ring falls inside a finder block, so it is tagged region 1 (no inner light modules exist)
		target_value = 0 if invert else 1
		grid_points = {} # (row, col) -> region, for the connected module grid
		single_points = [] # [(row, col, region)] standalone finder markers (no edges)

		for r in range(size):
			for c in range(size):
				if matrix[r][c] != target_value:
					continue
				region = finder_region(r, c)
				if region is None:
					grid_points[(r, c)] = 2
				elif single:
					# Skip individual finder modules; a single marker is added separately below
					continue
				else:
					grid_points[(r, c)] = 0 if region == 'inner' else 1

		if single:
			for fr, fc in finder_origins:
				# Centre module of the 7x7 finder block
				single_points.append((fr + 3, fc + 3, 3))

		# Neighbour bitmask (8-directional "47-tile blob" set) computed over the connected grid point membership
		# Bit weights: up=1, right=2, down=4, left=8; corners only count when both adjacent edges are present
		def neighbour_state(r, c):
			up = (r - 1, c) in grid_points
			down = (r + 1, c) in grid_points
			left = (r, c - 1) in grid_points
			right = (r, c + 1) in grid_points
			state = 0
			if up:
				state |= 1
			if right:
				state |= 2
			if down:
				state |= 4
			if left:
				state |= 8
			if up and right and (r - 1, c + 1) in grid_points:
				state |= 16
			if down and right and (r + 1, c + 1) in grid_points:
				state |= 32
			if down and left and (r + 1, c - 1) in grid_points:
				state |= 64
			if up and left and (r - 1, c - 1) in grid_points:
				state |= 128
			return state

		# Switch out of editing mode if active
		if obj.mode != 'OBJECT':
			object_mode = obj.mode
			bpy.ops.object.mode_set(mode = 'OBJECT')
		else:
			object_mode = None

		# Create a new bmesh
		bm = bmesh.new()

		# Centre the code on the origin, with row 0 at +Y (reads correctly viewed down -Z)
		offset = (size - 1) * space * 0.5

		def place(r, c):
			return ((c * space) - offset, offset - (r * space), 0.0)

		# Sorted for deterministic ordering (top-left to bottom-right)
		ordered = sorted(grid_points.keys())
		total = max(len(ordered) + len(single_points) - 1, 1)

		if polygons:
			# Solid mode: one flat quad per module (scannable with no modifier; isolated modules are included)
			# region and state are written to the face domain
			freg = bm.faces.layers.int.new('region')
			fstate = bm.faces.layers.int.new('state')
			ff = bm.faces.layers.float.new('factor')
			half = space * 0.5
			corner_lookup = {}

			def corner(cr, cc):
				# Shared boundary vertex at the top-left of module (cr, cc), so adjacent quads weld together
				key = (cr, cc)
				cv = corner_lookup.get(key)
				if cv is None:
					cx, cy, _ = place(cr, cc)
					cv = bm.verts.new((cx - half, cy + half, 0.0))
					corner_lookup[key] = cv
				return cv

			def add_quad(r, c, region, state, factor):
				# Wound counter-clockwise as viewed down -Z for an upward-facing normal
				f = bm.faces.new((corner(r + 1, c), corner(r + 1, c + 1), corner(r, c + 1), corner(r, c)))
				f[freg] = region
				f[fstate] = state
				f[ff] = factor

			i = 0
			for (r, c) in ordered:
				add_quad(r, c, grid_points[(r, c)], neighbour_state(r, c), 0.0 if total == 0 else float(i) / float(total))
				i += 1
			# Single finder markers become one-module quads (single-point mode)
			for (r, c, region) in single_points:
				add_quad(r, c, region, 0, 0.0 if total == 0 else float(i) / float(total))
				i += 1

			# Ensure all faces point up (+Z)
			bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
		else:
			# Skeleton mode: one point per module, plus edges between adjacent modules for the Skin modifier
			pf = bm.verts.layers.float.new('factor')
			ps = bm.verts.layers.float.new('scale')
			preg = bm.verts.layers.int.new('region')
			pstate = bm.verts.layers.int.new('state')
			vert_lookup = {}
			i = 0

			# Create grid module vertices
			for (r, c) in ordered:
				x, y, z = place(r, c)
				v = bm.verts.new((x, y, z))
				v[pf] = 0.0 if total == 0 else float(i) / float(total)
				v[ps] = radius
				v[preg] = grid_points[(r, c)]
				v[pstate] = neighbour_state(r, c)
				vert_lookup[(r, c)] = v
				i += 1

			# Create standalone finder marker vertices (single-point mode)
			for (r, c, region) in single_points:
				x, y, z = place(r, c)
				v = bm.verts.new((x, y, z))
				v[pf] = 0.0 if total == 0 else float(i) / float(total)
				v[ps] = radius
				v[preg] = region
				v[pstate] = 0
				i += 1

			# Connect adjacent grid modules with edges (right and down neighbours, avoiding duplicates)
			# This wireframe is ready for the Skin modifier (set its radius to match the point radius)
			for (r, c), v in vert_lookup.items():
				right = vert_lookup.get((r, c + 1))
				if right is not None:
					bm.edges.new([v, right])
				down = vert_lookup.get((r + 1, c))
				if down is not None:
					bm.edges.new([v, down])

		# Replace object with new mesh data
		bm.to_mesh(obj.data)
		bm.free()
		obj.data.update() # This ensures the viewport updates

		# Store the QR settings to custom mesh properties
		mesh = obj.data
		mesh['MeshKit_QR_string'] = text
		mesh['MeshKit_QR_error'] = error
		mesh['MeshKit_QR_size'] = size

		# Reset to original mode
		if object_mode is not None:
			bpy.ops.object.mode_set(mode = object_mode)

		return {'FINISHED'}



###########################################################################
# UI rendering class

class MESHKIT_PT_point_array(bpy.types.Panel):
	bl_space_type = "VIEW_3D"
	bl_region_type = "UI"
	bl_category = "Launch"
	bl_order = 30
	bl_options = {'DEFAULT_CLOSED'}
	bl_label = "Point Array"
	bl_idname = "MESHKIT_PT_point_array"
	category_preference = "pointarray_category"

	@classmethod
	def poll(cls, context):
		return True
	
	def draw_header(self, context):
		try:
			layout = self.layout
		except Exception as exc:
			print(str(exc) + " | Error in Mesh Kit Point Array panel header")
	
	def draw(self, context):
		try:
			layout = self.layout
			layout.use_property_split = True
			layout.use_property_decorate = False # No animation
			
			layout.prop(context.scene.mesh_kit_settings, 'array_type')
			
			# Messaging variables
			target_name = ''
			ui_button = ''
			ui_message = ''
			
			# Cubic Grid UI
			if bpy.context.scene.mesh_kit_settings.array_type == "GRID":
				col=layout.column()
				col.prop(context.scene.mesh_kit_settings, 'grid_count')
				if bpy.context.scene.mesh_kit_settings.scale_random:
					row = layout.row()
					row.prop(context.scene.mesh_kit_settings, 'scale_minimum')
					row.prop(context.scene.mesh_kit_settings, 'scale_maximum')
				else:
					layout.prop(context.scene.mesh_kit_settings, 'scale_maximum')
				layout.prop(context.scene.mesh_kit_settings, 'scale_random')
				layout.prop(context.scene.mesh_kit_settings, 'rotation_random')
				layout.prop(context.scene.mesh_kit_settings, 'polyline')
				layout.prop(context.scene.mesh_kit_settings, 'grid_ground')
				
				if bpy.context.view_layer.objects.active is not None and bpy.context.view_layer.objects.active.type == "MESH":
					target_name = bpy.context.view_layer.objects.active.name
					ui_button = 'Replace "' + target_name + '"'
					ui_message = 'Generate ' + str(bpy.context.scene.mesh_kit_settings.grid_count[0] * bpy.context.scene.mesh_kit_settings.grid_count[1] * bpy.context.scene.mesh_kit_settings.grid_count[2]) + ' points'
				else:
					ui_button = ''
					ui_message = 'no mesh selected'

				# Display create button
				if ui_button:
					layout.operator(MeshKit_Point_Grid.bl_idname, text=ui_button)
			
			# Golden Angle UI
			elif bpy.context.scene.mesh_kit_settings.array_type == "GOLDEN":
				layout.prop(context.scene.mesh_kit_settings, 'golden_count')
				if bpy.context.scene.mesh_kit_settings.scale_random:
					row = layout.row()
					row.prop(context.scene.mesh_kit_settings, 'scale_minimum')
					row.prop(context.scene.mesh_kit_settings, 'scale_maximum')
				else:
					layout.prop(context.scene.mesh_kit_settings, 'scale_maximum')
				layout.prop(context.scene.mesh_kit_settings, 'scale_random')
				layout.prop(context.scene.mesh_kit_settings, 'rotation_random')
				layout.prop(context.scene.mesh_kit_settings, 'polyline')
				layout.prop(context.scene.mesh_kit_settings, 'golden_fill')
				
				if bpy.context.view_layer.objects.active is not None and bpy.context.view_layer.objects.active.type == "MESH":
					target_name = bpy.context.view_layer.objects.active.name
					ui_button = 'Replace "' + target_name + '"'
					ui_message = ''
				else:
					ui_button = ''
					ui_message = 'no mesh selected'
					
				# Display create button
				if ui_button:
					layout.operator(MeshKit_Point_Golden.bl_idname, text=ui_button)
			
			# Poisson Disc UI
			elif bpy.context.scene.mesh_kit_settings.array_type == "PACK":
				layout.prop(context.scene.mesh_kit_settings, 'area_shape')
				col=layout.column()
				col.prop(context.scene.mesh_kit_settings, 'area_size')
				
				if bpy.context.scene.mesh_kit_settings.area_shape == "HULL":
					layout.prop(context.scene.mesh_kit_settings, 'area_truncate')
				else:
					layout.prop(context.scene.mesh_kit_settings, 'area_alignment', expand=True)
				
				# Point settings
				if bpy.context.scene.mesh_kit_settings.scale_random:
					row = layout.row()
					row.prop(context.scene.mesh_kit_settings, 'scale_minimum')
					row.prop(context.scene.mesh_kit_settings, 'scale_maximum')
				else:
					layout.prop(context.scene.mesh_kit_settings, 'scale_maximum')
				layout.prop(context.scene.mesh_kit_settings, 'scale_random')
				layout.prop(context.scene.mesh_kit_settings, 'rotation_random')
				layout.prop(context.scene.mesh_kit_settings, 'polyline')
				
				# Limits
				layout.label(text='Iteration Limits')
				layout.prop(context.scene.mesh_kit_settings, 'max_elements')
				layout.prop(context.scene.mesh_kit_settings, 'max_failures')
				layout.prop(context.scene.mesh_kit_settings, 'max_attempts')
				
				if bpy.context.view_layer.objects.active is not None and bpy.context.view_layer.objects.active.type == "MESH":
					target_name = bpy.context.view_layer.objects.active.name
					ui_button = 'Replace "' + target_name + '"'
					if len(context.scene.mesh_kit_settings.feedback_time) > 0:
						ui_message = [
							'Points created: ' + str(context.scene.mesh_kit_settings.feedback_elements),
							'Consecutive fails: ' + str(context.scene.mesh_kit_settings.feedback_failures),
							'Total attempts: ' + str(context.scene.mesh_kit_settings.feedback_attempts),
							'Processing Time: ' + str(context.scene.mesh_kit_settings.feedback_time)
						]
					else:
						ui_message = ''
				else:
					ui_button = ''
					ui_message = 'no mesh selected'
				
				# Display create button
				if ui_button:
					layout.operator(MeshKit_Point_Pack.bl_idname, text=ui_button)



			# Rectangular Array UI
			elif bpy.context.scene.mesh_kit_settings.array_type == "REC":
				col=layout.column()
				col.prop(context.scene.mesh_kit_settings, 'array_count')
				layout.prop(context.scene.mesh_kit_settings, 'scale_maximum')
				layout.prop(context.scene.mesh_kit_settings, 'rotation_random')
				layout.prop(context.scene.mesh_kit_settings, 'polyline')
				layout.prop(context.scene.mesh_kit_settings, 'division_levels')
				layout.prop(context.scene.mesh_kit_settings, 'division_percentage')

				if bpy.context.view_layer.objects.active is not None and bpy.context.view_layer.objects.active.type == "MESH":
					target_name = bpy.context.view_layer.objects.active.name
					ui_button = 'Replace "' + target_name + '"'
					point_start = bpy.context.scene.mesh_kit_settings.array_count[0] * bpy.context.scene.mesh_kit_settings.array_count[1]
					ui_message = 'Generate ' + str(subdivide_count(point_start, 3)) + ' points'
				else:
					ui_button = ''
					ui_message = 'no mesh selected'

				# Display create button
				if ui_button:
					layout.operator(MeshKit_Point_Rectangle.bl_idname, text=ui_button)

			# Triangular Array UI
			elif bpy.context.scene.mesh_kit_settings.array_type == "TRI":
				layout.prop(context.scene.mesh_kit_settings, 'array_count', index=0, text="Count")
				layout.prop(context.scene.mesh_kit_settings, 'scale_maximum')
				layout.prop(context.scene.mesh_kit_settings, 'rotation_random')
				layout.prop(context.scene.mesh_kit_settings, 'polyline')
				layout.prop(context.scene.mesh_kit_settings, 'division_levels')
				layout.prop(context.scene.mesh_kit_settings, 'division_percentage')

				if bpy.context.view_layer.objects.active is not None and bpy.context.view_layer.objects.active.type == "MESH":
					target_name = bpy.context.view_layer.objects.active.name
					ui_button = 'Replace "' + target_name + '"'
					point_start = bpy.context.scene.mesh_kit_settings.array_count[0] ** 2
					ui_message = 'Generate ' + str(subdivide_count(point_start, 3)) + ' points'
				else:
					ui_button = ''
					ui_message = 'no mesh selected'

				# Display create button
				if ui_button:
					layout.operator(MeshKit_Point_Triangle.bl_idname, text=ui_button)

			# Tri-Hex Array UI
			elif bpy.context.scene.mesh_kit_settings.array_type == "TRIHEX":
				layout.prop(context.scene.mesh_kit_settings, 'array_count', index=0, text="Count")
				layout.prop(context.scene.mesh_kit_settings, 'scale_maximum')
				layout.prop(context.scene.mesh_kit_settings, 'rotation_random')
				layout.prop(context.scene.mesh_kit_settings, 'polyline')
				layout.prop(context.scene.mesh_kit_settings, 'division_levels')
				layout.prop(context.scene.mesh_kit_settings, 'division_percentage')

				if bpy.context.view_layer.objects.active is not None and bpy.context.view_layer.objects.active.type == "MESH":
					target_name = bpy.context.view_layer.objects.active.name
					ui_button = 'Replace "' + target_name + '"'
					point_start = 6 * (bpy.context.scene.mesh_kit_settings.array_count[0] ** 2)
					ui_message = 'Generate ' + str(subdivide_count(point_start, 3)) + ' points'
				else:
					ui_button = ''
					ui_message = 'no mesh selected'

				# Display create button
				if ui_button:
					layout.operator(MeshKit_Point_TriHex.bl_idname, text=ui_button)

			# Hexagonal Array UI
			elif bpy.context.scene.mesh_kit_settings.array_type == "HEX":
				layout.prop(context.scene.mesh_kit_settings, 'array_count', index=0, text="Count")
				layout.prop(context.scene.mesh_kit_settings, 'scale_maximum')
				layout.prop(context.scene.mesh_kit_settings, 'rotation_random')
				layout.prop(context.scene.mesh_kit_settings, 'polyline')
				layout.prop(context.scene.mesh_kit_settings, 'division_levels')
				layout.prop(context.scene.mesh_kit_settings, 'division_percentage')

				if bpy.context.view_layer.objects.active is not None and bpy.context.view_layer.objects.active.type == "MESH":
					target_name = bpy.context.view_layer.objects.active.name
					ui_button = 'Replace "' + target_name + '"'
					hex_count = bpy.context.scene.mesh_kit_settings.array_count[0]
					point_start = 3 * (hex_count ** 2) - 3 * hex_count + 1
					# Hexagons divide into 3 (not 4) elements per division, adding 2 per divided point
					ui_message = 'Generate ' + str(subdivide_count(point_start, 2, 3)) + ' points'
				else:
					ui_button = ''
					ui_message = 'no mesh selected'

				# Display create button
				if ui_button:
					layout.operator(MeshKit_Point_Hexagon.bl_idname, text=ui_button)

			# Random Walk UI
			elif bpy.context.scene.mesh_kit_settings.array_type == "WALK":
				layout.prop(context.scene.mesh_kit_settings, 'walk_dimensions', expand=True)
				layout.prop(context.scene.mesh_kit_settings, 'walk_directionality')
				if bpy.context.scene.mesh_kit_settings.walk_directionality > 0.0:
					col=layout.column()
					col.prop(context.scene.mesh_kit_settings, 'walk_vector')

				# Point settings
				if bpy.context.scene.mesh_kit_settings.scale_random:
					row = layout.row()
					row.prop(context.scene.mesh_kit_settings, 'scale_minimum')
					row.prop(context.scene.mesh_kit_settings, 'scale_maximum')
				else:
					layout.prop(context.scene.mesh_kit_settings, 'scale_maximum')
				layout.prop(context.scene.mesh_kit_settings, 'scale_random')
				layout.prop(context.scene.mesh_kit_settings, 'walk_decay')
				layout.prop(context.scene.mesh_kit_settings, 'walk_rotation')
				layout.prop(context.scene.mesh_kit_settings, 'polyline')

				# Limits
				layout.label(text='Iteration Limits')
				layout.prop(context.scene.mesh_kit_settings, 'max_elements')
				layout.prop(context.scene.mesh_kit_settings, 'max_failures')
				layout.prop(context.scene.mesh_kit_settings, 'max_attempts')

				if bpy.context.view_layer.objects.active is not None and bpy.context.view_layer.objects.active.type == "MESH":
					target_name = bpy.context.view_layer.objects.active.name
					ui_button = 'Replace "' + target_name + '"'
					if len(context.scene.mesh_kit_settings.feedback_time) > 0:
						ui_message = [
							'Points created: ' + str(context.scene.mesh_kit_settings.feedback_elements),
							'Consecutive fails: ' + str(context.scene.mesh_kit_settings.feedback_failures),
							'Total attempts: ' + str(context.scene.mesh_kit_settings.feedback_attempts),
							'Processing Time: ' + str(context.scene.mesh_kit_settings.feedback_time)
						]
					else:
						ui_message = ''
				else:
					ui_button = ''
					ui_message = 'no mesh selected'

				# Display create button
				if ui_button:
					layout.operator(MeshKit_Point_Walk.bl_idname, text=ui_button)

			# QR Code UI
			elif bpy.context.scene.mesh_kit_settings.array_type == "QR":
				layout.prop(context.scene.mesh_kit_settings, 'qr_string')
				layout.prop(context.scene.mesh_kit_settings, 'qr_error')
				layout.prop(context.scene.mesh_kit_settings, 'scale_maximum')
				col = layout.column(align=True)
				row1 = col.row(align=True)
				row1.prop(context.scene.mesh_kit_settings, 'qr_invert', expand=True)
				row2 = col.row(align=True)
				row2.prop(context.scene.mesh_kit_settings, 'qr_output', expand=True)
				row3 = col.row(align=True)
				row3.prop(context.scene.mesh_kit_settings, 'qr_corners', expand=True)

				if bpy.context.view_layer.objects.active is not None and bpy.context.view_layer.objects.active.type == "MESH":
					target_name = bpy.context.view_layer.objects.active.name
					ui_button = 'Replace "' + target_name + '"'
					estimate = estimate_qr(bpy.context.scene.mesh_kit_settings.qr_string, bpy.context.scene.mesh_kit_settings.qr_error)
					if estimate:
						ui_message = 'Version ' + str(estimate[0]) + ', ' + str(estimate[1]) + '×' + str(estimate[1]) + ' modules'
					else:
						ui_message = ''
				else:
					ui_button = ''
					ui_message = 'no mesh selected'

				# Display create button
				if ui_button:
					layout.operator(MeshKit_Point_QR.bl_idname, text=ui_button)

			# Display data message
			if ui_message:
				box = layout.box()
				if type(ui_message) == str:
					box.label(text=str(ui_message))
				else:
					boxcol=box.column()
					for ui_row in ui_message:
						boxcol.label(text=str(ui_row))
		
		except Exception as exc:
			print(str(exc) + " | Error in Mesh Kit Point Array panel")



###########################################################################
# Registration

classes = (
	MeshKit_Point_Grid,
	MeshKit_Point_Golden,
	MeshKit_Point_Pack,
	MeshKit_Point_Rectangle,
	MeshKit_Point_Triangle,
	MeshKit_Point_TriHex,
	MeshKit_Point_Hexagon,
	MeshKit_Point_Walk,
	MeshKit_Point_QR,
)

# Registered from the tab category set in the extension preferences
panels = [MESHKIT_PT_point_array]



def register():
	for cls in classes:
		bpy.utils.register_class(cls)
	# Register panels
	utility_panel.register_panels(panels)



def unregister():
	# Unregister panels
	utility_panel.unregister_panels(panels)
	for cls in reversed(classes):
		bpy.utils.unregister_class(cls)



if __name__ == "__main__":
	register()
