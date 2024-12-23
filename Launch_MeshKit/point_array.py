import bpy
import bmesh
from random import uniform
from mathutils import Vector
import math
import time
# Data import support
from pathlib import Path
import numpy as np
import re
# Volume Field import support
import struct

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



class MeshKit_Import_Position_Data(bpy.types.Operator):
	bl_idname = "ops.meshkit_import_position_data"
	bl_label = "Import Position Data"
	bl_description = "Create a point cloud or poly line using the selected options and source data"
	bl_options = {'REGISTER', 'UNDO'}
	
	def execute(self, context):
		# Load data
		data_name = 'MeshKit_Import_Position_Data'
		# Internal data-block
		if bpy.context.scene.mesh_kit_settings.data_source == 'INT':
			# Load internal CSV data
			source = int(bpy.context.scene.mesh_kit_settings.data_text)
			data_name = bpy.data.texts[source].name
			source = bpy.data.texts[source].as_string()
			# Attempting to cleanse the input data by removing all lines that contain unusable data such as headers, nan/inf, and empty columns or rows
			source = re.sub(r'^.*([a-z]).*\n|^(\,.*||.*\,)\n|\"', '', source, flags=re.MULTILINE).rstrip()
			# Create multidimensional array from string data
			data = np.array([np.fromstring(i, dtype=float, sep=',') for i in source.split('\n')])
		# External data file
		else:
			# Load external CSV/NPY data
			source = bpy.path.abspath(bpy.context.scene.mesh_kit_settings.data_file)
			data_suffix = Path(source).suffix
			data_name = Path(source).name
			# Alternatively use ".stem" for just the file name without extension
			if data_suffix == ".csv":
				data = np.loadtxt(source, delimiter=',', skiprows=1, dtype='str')
				# The process of importing questionable CSV data is far more nightmarish than it has any right to be, so here's a stupid "numbers only" filter
				for row in data:
					for i, string in enumerate(row):
						string = re.sub(r'[^\d\.\-]', '', string)
						try:
							row[i] = float(string)
						except:
							row[i] = np.nan
			elif data_suffix == ".npy":
				data = np.load(source)
		
		# Process data
		# Return an error if the array contains less than two rows or one column
		if len(data) < 2 or len(data[1]) < 1:
			return {'CANCELLED'}
		
		# Remove all rows that have non-numeric data
		data = data[np.isfinite(data.astype("float")).all(axis=1)]
		
		# Load point settings
		scale_random = bpy.context.scene.mesh_kit_settings.scale_random
		scale_max = bpy.context.scene.mesh_kit_settings.scale_maximum # maximum radius of the generated point
		scale_min = bpy.context.scene.mesh_kit_settings.scale_minimum # minimum radius of the generated point
		rotation_rand = bpy.context.scene.mesh_kit_settings.rotation_random
		
		# Get or create object
		if bpy.context.scene.mesh_kit_settings.data_target == 'NAME':
			# https://blender.stackexchange.com/questions/184109/python-check-if-object-exists-in-blender-2-8
			obj = bpy.context.scene.objects.get(data_name)
			if not obj:
				# https://blender.stackexchange.com/questions/61879/create-mesh-then-add-vertices-to-it-in-python
				# Create a new mesh, a new object that uses that mesh, and then link that object in the scene
				mesh = bpy.data.meshes.new(data_name)
				obj = bpy.data.objects.new(mesh.name, mesh)
				bpy.context.collection.objects.link(obj)
				bpy.context.view_layer.objects.active = obj
				# Deselect all other items, and select the newly created mesh object
				bpy.ops.object.select_all(action='DESELECT')
				obj.select_set(True); 
		else:
			# Get the currently active object
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
		ps = bm.verts.layers.float.new('scale')
		pr = bm.verts.layers.float_vector.new('rotation')
		
		# Cycle through rows
		count = len(data)
		for i, row in enumerate(data):
			pointX = float(row[0]) if len(row) > 0 else 0.0
			pointY = float(row[1]) if len(row) > 1 else 0.0
			pointZ = float(row[2]) if len(row) > 2 else 0.0
			v = bm.verts.new((float(pointX), float(pointY), float(pointZ)))
			v[pf] = 0.0 if i == 0.0 else i / count
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



class MeshKit_Import_Volume_Field(bpy.types.Operator):
	bl_idname = "ops.meshkit_import_volume_field"
	bl_label = "Import Volume Field"
	bl_description = "Create a volume field from a Unity 3D .vf file"
	bl_options = {'REGISTER', 'UNDO'}
	
	def execute(self, context):
		# Load external Volume Field binary data
		source = bpy.path.abspath(bpy.context.scene.mesh_kit_settings.field_file)
		data_suffix = Path(source).suffix
		data_name = Path(source).name
		# Alternatively use ".stem" for just the file name without extension
		
		# Cancel if the input file is an invalid format
		if data_suffix != ".vf":
			print('VF Point Array error: input file is an invalid format')
			return {'CANCELLED'}
		
		# Define the format strings for parsing
		fourcc_format = '4s'
		volume_grid_format = 'HHH'
		float_data_format = 'f'
		vector_data_format = 'fff'
		
		# Define persistent variables
		is_float_data = False
		grid_x = 0
		grid_y = 0
		grid_z = 0
		
		# Open the binary file for reading
		with open(source, 'rb') as file:
			# Read the FourCC
			fourcc = struct.unpack(fourcc_format, file.read(4))[0].decode('utf-8')
			
			# Check if it's float or vector data
			is_float_data = fourcc[3] == 'F'
			
			# Read the volume size
			grid_x, grid_y, grid_z = struct.unpack(volume_grid_format, file.read(6))
			
			# Calculate the stride based on the data type
			stride = 1 if is_float_data else 3
			
			# Read the data (XYZ order doesn't matter here, it's just reading the series of values)
			data = []
			for _x in range(grid_x):
				for _y in range(grid_y):
					for _z in range(grid_z):
						if is_float_data:
							value = struct.unpack(float_data_format, file.read(4))[0]
						else:
							value = struct.unpack(vector_data_format, file.read(12))
						data.append(value)
		
		# Load point settings
		scale_random = bpy.context.scene.mesh_kit_settings.scale_random
		scale_max = bpy.context.scene.mesh_kit_settings.scale_maximum # maximum radius of the generated point
		scale_min = bpy.context.scene.mesh_kit_settings.scale_minimum # minimum radius of the generated point
		rotation_rand = bpy.context.scene.mesh_kit_settings.rotation_random
		space = scale_max * 2.0
		offset_x = (grid_x - 1) * space * -0.5 if bpy.context.scene.mesh_kit_settings.field_center else 0.0
		offset_y = (grid_z - 1) * space * -0.5 if bpy.context.scene.mesh_kit_settings.field_center else 0.0
		offset_z = (grid_y - 1) * space * -0.5 if bpy.context.scene.mesh_kit_settings.field_center else 0.0
		
		# Get or create object
		if bpy.context.scene.mesh_kit_settings.field_target == 'NAME':
			# https://blender.stackexchange.com/questions/184109/python-check-if-object-exists-in-blender-2-8
			obj = bpy.context.scene.objects.get(data_name)
			if not obj:
				# https://blender.stackexchange.com/questions/61879/create-mesh-then-add-vertices-to-it-in-python
				# Create a new mesh, a new object that uses that mesh, and then link that object in the scene
				mesh = bpy.data.meshes.new(data_name)
				obj = bpy.data.objects.new(mesh.name, mesh)
				bpy.context.collection.objects.link(obj)
				bpy.context.view_layer.objects.active = obj
				# Deselect all other items, and select the newly created mesh object
				bpy.ops.object.select_all(action='DESELECT')
				obj.select_set(True); 
		else:
			# Get the currently active object
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
		ps = bm.verts.layers.float.new('scale')
		pr = bm.verts.layers.float_vector.new('rotation')
		pv = bm.verts.layers.float_vector.new('field_vector')
		pf = bm.verts.layers.float.new('field_float')
		
		# Create geometry and assign field values
		count = len(data) - 1
		i = 0
		vec = Vector([0.0, 0.0, 0.0]) # Used for float data
		for _y in range(grid_z): # First step in swizzled channel order
			for _z in range(grid_y): # First step in swizzled channel order
				for _x in range(grid_x):
					v = bm.verts.new((_x * space + offset_x, _y * space + offset_y, _z * space + offset_z))
					v[pf] = 0.0 if i == 0 else i / count
					v[ps] = scale_max if not scale_random else uniform(scale_min, scale_max)
					if is_float_data:
						v[pv] = vec
						v[pf] = data[i]
						v[pr] = vec if not rotation_rand else Vector([uniform(-math.pi, math.pi), uniform(-math.pi, math.pi), uniform(-math.pi, math.pi)])
					else:
						vec = Vector(tuple(data[i])).xzy # Second step in swizzled channel order
						v[pv] = vec
						v[pf] = vec.length
						v[pr] = vec.to_track_quat('Z','Y').to_euler()
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



###########################################################################
# Data cleanup for NumPy CSV import

def data_converter(var):
	return float(re.sub(r'[^\d\-\.]', "", var))



###########################################################################
# UI rendering class

class MESHKIT_PT_point_array(bpy.types.Panel):
	bl_space_type = "VIEW_3D"
	bl_region_type = "UI"
	bl_category = "Launch"
	bl_order = 4
	bl_options = {'DEFAULT_CLOSED'}
	bl_label = "Point Array"
	bl_idname = "MESHKIT_PT_point_array"
	
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
			
			# Position Data Import UI
			elif bpy.context.scene.mesh_kit_settings.array_type == "DATA":
				layout.prop(context.scene.mesh_kit_settings, 'data_source', expand=True)
				
				# Initialise data source boolean
				file_selected = False
				
				# Internal CSV text datablock import
				if bpy.context.scene.mesh_kit_settings.data_source == 'INT':
					if len(bpy.data.texts) > 0:
						layout.prop(context.scene.mesh_kit_settings, 'data_text')
						file_selected = True if bpy.context.scene.mesh_kit_settings.data_text else False
						if file_selected:
							target_name = bpy.data.texts[int(bpy.context.scene.mesh_kit_settings.data_text)].name
					else:
						ui_message = 'no text blocks available'
				
				# External CSV/NPY file import
				else:
					layout.prop(context.scene.mesh_kit_settings, 'data_file')
					file_selected = True if len(bpy.context.scene.mesh_kit_settings.data_file) > 4 else False
					if file_selected:
						target_name = Path(bpy.context.scene.mesh_kit_settings.data_file).name
					else:
						ui_message = 'no data file chosen'
				
				# General settings
				if file_selected:
					# General settings
					if bpy.context.scene.mesh_kit_settings.scale_random:
						row = layout.row()
						row.prop(context.scene.mesh_kit_settings, 'scale_minimum')
						row.prop(context.scene.mesh_kit_settings, 'scale_maximum')
					else:
						layout.prop(context.scene.mesh_kit_settings, 'scale_maximum')
					layout.prop(context.scene.mesh_kit_settings, 'scale_random')
					layout.prop(context.scene.mesh_kit_settings, 'rotation_random')
					layout.prop(context.scene.mesh_kit_settings, 'polyline')
					
					# Target object
					layout.prop(context.scene.mesh_kit_settings, 'data_target', expand=True)
					if bpy.context.scene.mesh_kit_settings.data_target == 'NAME':
						if bpy.context.scene.objects.get(target_name):
							ui_button = 'Replace "' + target_name + '"'
							ui_message = ''
						else:
							ui_button = 'Create "' + target_name + '"'
							ui_message = ''
					else:
						if bpy.context.view_layer.objects.active is not None and bpy.context.view_layer.objects.active.type == "MESH":
							target_name = bpy.context.view_layer.objects.active.name
							ui_button = 'Replace "' + target_name + '"'
							ui_message = ''
						else:
							ui_button = ''
							ui_message = 'no mesh selected'
					
					# Display import button
					if ui_button:
						layout.operator(MeshKit_Import_Position_Data.bl_idname, text=ui_button)
			
			# Volume Field UI
			elif bpy.context.scene.mesh_kit_settings.array_type == "FIELD":
				# Initialise data source boolean
				file_selected = False
				
				# Display file input UI
				layout.prop(context.scene.mesh_kit_settings, 'field_file')
				file_selected = True if len(bpy.context.scene.mesh_kit_settings.field_file) > 4 else False
				if file_selected:
					target_name = Path(bpy.context.scene.mesh_kit_settings.field_file).name
				else:
					ui_message = 'no volume field chosen'
						
				# General settings
				if file_selected:
					# General settings
					if bpy.context.scene.mesh_kit_settings.scale_random:
						row = layout.row()
						row.prop(context.scene.mesh_kit_settings, 'scale_minimum')
						row.prop(context.scene.mesh_kit_settings, 'scale_maximum')
					else:
						layout.prop(context.scene.mesh_kit_settings, 'scale_maximum')
					layout.prop(context.scene.mesh_kit_settings, 'scale_random')
					layout.prop(context.scene.mesh_kit_settings, 'rotation_random')
					layout.prop(context.scene.mesh_kit_settings, 'polyline')
					layout.prop(context.scene.mesh_kit_settings, 'field_center')
					
					# Target object
					layout.prop(context.scene.mesh_kit_settings, 'field_target', expand=True)
					if bpy.context.scene.mesh_kit_settings.field_target == 'NAME':
						if bpy.context.scene.objects.get(target_name):
							ui_button = 'Replace "' + target_name + '"'
							ui_message = ''
						else:
							ui_button = 'Create "' + target_name + '"'
							ui_message = ''
					else:
						if bpy.context.view_layer.objects.active is not None and bpy.context.view_layer.objects.active.type == "MESH":
							target_name = bpy.context.view_layer.objects.active.name
							ui_button = 'Replace "' + target_name + '"'
							ui_message = ''
						else:
							ui_button = ''
							ui_message = 'no mesh selected'
					
					# Display import button
					if ui_button:
						layout.operator(MeshKit_Import_Volume_Field.bl_idname, text=ui_button)
			
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
