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
from mathutils import Vector, Matrix
from mathutils.geometry import intersect_ray_tri
import math
from collections import OrderedDict

# Load rendering light parameters
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.dirname(BASE_DIR))
from global_variables import *
from render_pipeline.blender_utils import *

light_num_lowbound = g_syn_light_num_lowbound
light_num_highbound = g_syn_light_num_highbound
light_dist_lowbound = g_syn_light_dist_lowbound
light_dist_highbound = g_syn_light_dist_highbound

render_scale = bpy.context.scene.render.resolution_percentage / 100
render_size = (
            int(bpy.context.scene.render.resolution_x * render_scale),
            int(bpy.context.scene.render.resolution_y * render_scale),
            )

def project_by_object_utils(cam, point):
    scene = bpy.context.scene
    co_2d = world_to_camera_view(scene, cam, point)
    return Vector((co_2d.x * render_size[0], render_size[1] - co_2d.y * render_size[1]))

# Input parameters
#'%s %s --background --python %s -- %s %s %s %s %s %s' % (g_blender_executable_path, blank_file, render_code, args.model_file, 'xxx', 'xxx', view_file, temp_dirname, args.scale)
shape_file = sys.argv[-6]
keypoint_file = sys.argv[-5]
#shape_synset = sys.argv[-5]
shape_md5 = sys.argv[-4]
shape_view_params_file = sys.argv[-3]
syn_images_folder = sys.argv[-2]
scale = float(sys.argv[-1])

if not os.path.exists(syn_images_folder):
    os.mkdir(syn_images_folder)
#syn_images_folder = os.path.join(g_syn_images_folder, shape_synset, shape_md5) 
view_params = [[float(x) if i < 4 else x for i,x in enumerate(line.strip().split(' '))] for line in open(shape_view_params_file).readlines()]

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

bpy.context.scene.render.alpha_mode = 'TRANSPARENT'
#bpy.context.scene.render.use_shadows = False
#bpy.context.scene.render.use_raytrace = False

bpy.data.objects['Lamp'].data.energy = 0

#m.subsurface_scattering.use = True

camObj = bpy.data.objects['Camera']
# camObj.data.lens_unit = 'FOV'
# camObj.data.angle = 0.2

# Recipe to merge meshes as CAD models may have more than one mesh 
objs = []
for ob in bpy.context.scene.objects:
    ob.select = False
    if ob.type == 'MESH':
        objs.append(ob)
objs = sorted(objs, key=lambda ob: ob.name)
for ob in objs:
    ob.select = True
    bpy.context.scene.objects.active = ob
    
bpy.ops.object.join()

# Find mesh name
mesh_name = [x.name for x in bpy.data.objects if x.name not in ['Camera','Lamp']][0]

# Push all vertices in a dict
vert_visibility_dict = {}
obj = bpy.data.objects[mesh_name]
verts = [obj.matrix_world*vert.co for vert in obj.data.vertices]
for vert in verts:
    vert_str = "{:.40f},{:.40f},{:.40f}".format(vert[0],vert[1], vert[2]) 
    vert_visibility_dict[vert_str] = (False, None)
vert_visibility_dict = OrderedDict(sorted(vert_visibility_dict.items(), key=lambda x: x[0]))
# set lights
bpy.ops.object.select_all(action='TOGGLE')
if 'Lamp' in list(bpy.data.objects.keys()):
    bpy.data.objects['Lamp'].select = True # remove default light
bpy.ops.object.delete()

# YOUR CODE START HERE
with open(keypoint_file) as f:
    kp_list =  [int(x.strip()) for x in f.readlines()]

for param in view_params:
    azimuth_deg = param[0]
    elevation_deg = param[1]
    theta_deg = -1 * param[2] # ** multiply by -1 to match pascal3d annotations **
    rho = param[3]
    img_file = param[4]
    lbl_file = param[5]
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
    bpy.context.scene.update()
    vert_list_from_dict = list(vert_visibility_dict.keys())
    # use generator expressions () or list comprehensions []
    for obj in [bpy.data.objects[mesh_name]]:
        coords_2d = [project_by_object_utils(camObj, coord) for coord in verts]
        eye_location = camObj.location 
        # Find visible points in current camera
        vert_indices = []
        for polygon in obj.data.polygons:
            vert_index = [p for p in polygon.vertices]
            vert_indices.append(vert_index)
        random.shuffle(vert_indices)
        for i, vert in enumerate(verts):
            vert_str = "{:.40f},{:.40f},{:.40f}".format(vert[0],vert[1], vert[2])
            if vert_list_from_dict.index(vert_str) not in kp_list:
                continue
            vis = True
            for vert_index in vert_indices:
                if i in vert_index:
                    continue
                v1 = Vector(verts[vert_index[0]])
                v2 = Vector(verts[vert_index[1]])
                v3 = Vector(verts[vert_index[2]])
                ray = Vector(eye_location-vert)
                orig = Vector(vert)
                
                int_pt = intersect_ray_tri(v1, v2, v3, ray, orig)
                if int_pt != None:
                    vis = False
                    break
            
            if vis:    
                vert_visibility_dict[vert_str] = (True, coords_2d[i])
            else:
                vert_visibility_dict[vert_str] = (False, coords_2d[i])
        
        # 2d data printout:
        rnd = lambda i: round(i)
        #syn_label_file = 'syn_a%03d_e%03d_t%03d_d%03d.txt' % (round(azimuth_deg), round(elevation_deg), round(theta_deg), round(rho))
        render_scale = bpy.context.scene.render.resolution_percentage / 100
        render_size = (
            int(bpy.context.scene.render.resolution_x * render_scale),
            int(bpy.context.scene.render.resolution_y * render_scale),
            )
        with open(lbl_file, 'w') as f:
             for i, vert in enumerate(vert_visibility_dict.items()):
                if vert[1][1] == None:
                    key_px = "{} {} {}".format(i, -1, -1)
                else:
                    x, y = vert[1][1]
        #        key_px = "{} {} {}".format(i, rnd(x), rnd(y))
                    if vert[1][0] and (0 <= x < render_size[0]) and (0 <= y < render_size[1]):
                        key_px = "{} {} {}".format(i, rnd(x), rnd(y))
                    else:
                        key_px = "{} {} {}".format(i, -1, -1)
                f.write("%s\n"%key_px)
    #syn_image_file = 'syn_a%03d_e%03d_t%03d_d%03d.png' % (round(azimuth_deg), round(elevation_deg), round(theta_deg), round(rho))
    bpy.data.scenes['Scene'].render.filepath = os.path.join(img_file)
    bpy.ops.render.render( write_still=True )

