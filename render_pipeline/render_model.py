#!/usr/bin/python3
# -*- coding: utf-8 -*-
'''
RENDER_MODEL_VIEWS.py
brief:
	render projections of a 3D model from viewpoints specified by an input parameter file
usage:
	blender blank.blend --background --python render_model_views.py -- <shape_obj_filename> <shape_category_synset> <shape_model_md5> <shape_view_param_file> <syn_img_output_folder>

inputs:
       <shape_obj_filename>: .obj file of the 3D shape model
       <shape_category_synset>: synset string like '03001627' (chairs)
       <shape_model_md5>: md5 (as an ID) of the 3D shape model
       <shape_view_params_file>: txt file - each line is '<azimith angle> <elevation angle> <in-plane rotation angle> <distance>'
       <syn_img_output_folder>: output folder path for rendered images of this model

author: hao su, charles r. qi, yangyan li
'''

import os
import bpy
import sys
import random
import numpy as np
import bpy
from bpy_extras.object_utils import world_to_camera_view
import bmesh
from mathutils import Vector

# Load rendering light parameters
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.dirname(BASE_DIR))
from global_variables import *
from render_pipeline.blender_utils import *

light_num_lowbound = g_syn_light_num_lowbound
light_num_highbound = g_syn_light_num_highbound
light_dist_lowbound = g_syn_light_dist_lowbound
light_dist_highbound = g_syn_light_dist_highbound

def view3d_find():
    # returns first 3d view, normally we get from context
    for area in bpy.context.window.screen.areas:
        if area.type == 'VIEW_3D':
            v3d = area.spaces[0]
            rv3d = v3d.region_3d
            for region in area.regions:
                if region.type == 'WINDOW':
                    return region, rv3d
    return None, None

def view3d_camera_border(scene):
    #obj = scene.camera
    #cam = obj.data
    cam = bpy.data.objects['Camera']
    bpy.context.scene.camera = cam
    obj = bpy.context.scene.camera
    cam = obj.data
    frame = cam.view_frame(scene)

    # move into object space
    frame = [obj.matrix_world * v for v in frame]

    # move into pixelspace
    from bpy_extras.view3d_utils import location_3d_to_region_2d
    region, rv3d = view3d_find()
    frame_px = [location_3d_to_region_2d(region, rv3d, v) for v in frame]
    print(frame_px)
    return frame_px

# Input parameters
#'%s %s --background --python %s -- %s %s %s %s %s %s' % (g_blender_executable_path, blank_file, render_code, args.model_file, 'xxx', 'xxx', view_file, temp_dirname, args.scale)
shape_file = sys.argv[-6]
shape_synset = sys.argv[-5]
shape_md5 = sys.argv[-4]
shape_view_params_file = sys.argv[-3]
syn_images_folder = sys.argv[-2]
scale = float(sys.argv[-1])

if not os.path.exists(syn_images_folder):
    os.mkdir(syn_images_folder)
#syn_images_folder = os.path.join(g_syn_images_folder, shape_synset, shape_md5) 
view_params = [[float(x) for x in line.strip().split(' ')] for line in open(shape_view_params_file).readlines()]

if not os.path.exists(syn_images_folder):
    os.makedirs(syn_images_folder)

if shape_file[-3:] == 'ply':
    bpy.ops.import_mesh.ply(filepath=shape_file)
    bpy.ops.transform.resize(value=(scale, scale, scale))
elif shape_file[-3:] == 'dae':
    bpy.ops.wm.collada_import(filepath=shape_file)
elif shape_file[-3:] == 'obj':
    bpy.ops.import_scene.obj(filepath=shape_file)

scene = bpy.context.scene
#obj = bpy.data.meshes[shape_file.split('/')[-1][:-4]]
#print(obj.vertices[0].co)
# needed to rescale 2d coordinates
render = scene.render
res_x = render.resolution_x
res_y = render.resolution_y


bpy.context.scene.render.alpha_mode = 'TRANSPARENT'
#bpy.context.scene.render.use_shadows = False
#bpy.context.scene.render.use_raytrace = False

bpy.data.objects['Lamp'].data.energy = 0

#m.subsurface_scattering.use = True

camObj = bpy.data.objects['Camera']
# camObj.data.lens_unit = 'FOV'
# camObj.data.angle = 0.2

# Remove ugly hack
mesh_name = [x.name for x in bpy.data.objects if x.name not in ['Camera','Lamp']][0]

# set lights
bpy.ops.object.select_all(action='TOGGLE')
if 'Lamp' in list(bpy.data.objects.keys()):
    bpy.data.objects['Lamp'].select = True # remove default light
bpy.ops.object.delete()

px_dict = {}
# YOUR CODE START HERE

for param in view_params:
    azimuth_deg = param[0]
    elevation_deg = param[1]
    theta_deg = -1 * param[2] # ** multiply by -1 to match pascal3d annotations **
    rho = param[3]

    # clear default lights
    bpy.ops.object.select_by_type(type='LAMP')
    bpy.ops.object.delete(use_global=False)

    # set environment lighting
    #bpy.context.space_data.context = 'WORLD'
    bpy.context.scene.world.light_settings.use_environment_light = True
    bpy.context.scene.world.light_settings.environment_energy = np.random.uniform(g_syn_light_environment_energy_lowbound, g_syn_light_environment_energy_highbound)
    bpy.context.scene.world.light_settings.environment_color = 'PLAIN'
    # set point lights
    for i in range(random.randint(light_num_lowbound,light_num_highbound)):
        light_azimuth_deg = np.random.uniform(g_syn_light_azimuth_degree_lowbound, g_syn_light_azimuth_degree_highbound)
        light_elevation_deg  = np.random.uniform(g_syn_light_elevation_degree_lowbound, g_syn_light_elevation_degree_highbound)
        light_dist = np.random.uniform(light_dist_lowbound, light_dist_highbound)
        lx, ly, lz = obj_centened_camera_pos(light_dist, light_azimuth_deg, light_elevation_deg)
        bpy.ops.object.lamp_add(type='POINT', view_align = False, location=(lx, ly, lz))
        bpy.data.objects['Point'].data.energy = np.random.normal(g_syn_light_energy_mean, g_syn_light_energy_std)
    
    cx, cy, cz = obj_centened_camera_pos(rho, azimuth_deg, elevation_deg)
    q1 = camPosToQuaternion(cx, cy, cz)
    q2 = camRotQuaternion(cx, cy, cz, theta_deg)
    q = quaternionProduct(q2, q1)
    camObj.location[0] = cx
    camObj.location[1] = cy 
    camObj.location[2] = cz
    camObj.rotation_mode = 'QUATERNION'
    camObj.rotation_quaternion[0] = q[0]
    camObj.rotation_quaternion[1] = q[1]
    camObj.rotation_quaternion[2] = q[2]
    camObj.rotation_quaternion[3] = q[3]
    
    # use generator expressions () or list comprehensions []
    for obj in [bpy.data.objects[mesh_name]]:
        bpy.data.objects['Camera']
        verts = [vert.co for vert in obj.data.vertices]
        coords_2d = [world_to_camera_view(scene, camObj, coord) for coord in verts]
        
        vertlist = [vert.co for vert in obj.data.vertices] 
        # neat eye location code with the help of paleajed
        bpy.context.scene.camera = bpy.data.objects['Camera']
        #bpy.ops.view3d.camera_to_view()
        
        #r, rv3d = view3d_find()#bpy.context.space_data.region_3d  
        #eye = Vector(rv3d.view_matrix[2][:3])
        eye_location = camObj.location 
        visible_vertices = set()
        for idx, polygon in enumerate(obj.data.polygons):
            vert_index = polygon.vertices[0]
            pnormal = obj.matrix_world * polygon.normal
            world_coordinate = obj.matrix_world * vertlist[vert_index]
        
            result_vector = eye_location-world_coordinate
            dot_value = pnormal.dot(result_vector.normalized())            

            if dot_value < 0.0:
                print("False")
                #polygon.select = False
            else:
                print("True")
                #polygon.select = True
                for vert in polygon.vertices:
                    visible_vertices.add(vert_index)   
        
        # 2d data printout:
        rnd = lambda i: round(i)
        coords_2d = [coords_2d[index] for index in list(visible_vertices)]
        print(len(coords_2d))
        for x, y, distance_to_lens in coords_2d:
            key_px = "{},{}".format(rnd(res_x*x), rnd(res_y*y))
            print("{},{}".format(rnd(res_x*x), rnd(res_y*y)))
            #if key_px in px_dict.keys():
            #    px_dict[key_px] = min(px_dict[key_px], distance_to_lens)
            #else:
            #    px_dict[key_px] = distance_to_lens
        #for x, y, distance_to_lens in coords_2d:
        #    key_px = "{},{}".format(rnd(res_x*x), rnd(res_y*y))
        #    if px_dict[key_px] == distance_to_lens:
        #        print("{},{}".format(rnd(res_x*x), rnd(res_y*y)))
        #    else:
        #        print("Point not visible")

    syn_image_file = './%s_%s_a%03d_e%03d_t%03d_d%03d.png' % (shape_synset, shape_md5, round(azimuth_deg), round(elevation_deg), round(theta_deg), round(rho))
    bpy.data.scenes['Scene'].render.filepath = os.path.join(syn_images_folder, syn_image_file)
    bpy.ops.render.render( write_still=True )

