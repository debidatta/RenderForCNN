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

# Load rendering light parameters
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.dirname(BASE_DIR))
from global_variables import *
from render_pipeline.blender_utils import *

light_num_lowbound = g_syn_light_num_lowbound
light_num_highbound = g_syn_light_num_highbound
light_dist_lowbound = g_syn_light_dist_lowbound
light_dist_highbound = g_syn_light_dist_highbound

# Input parameters
shape_file = sys.argv[-5]
shape_synset = sys.argv[-4]
shape_md5 = sys.argv[-3]
shape_view_params_file = sys.argv[-2]
syn_images_folder = sys.argv[-1]
if not os.path.exists(syn_images_folder):
    os.mkdir(syn_images_folder)
#syn_images_folder = os.path.join(g_syn_images_folder, shape_synset, shape_md5) 
view_params = [[float(x) for x in line.strip().split(' ')] for line in open(shape_view_params_file).readlines()]

if not os.path.exists(syn_images_folder):
    os.makedirs(syn_images_folder)

if shape_file[-3:] == 'obj':
    bpy.ops.import_scene.obj(filepath=shape_file) 
elif shape_file[-3:] == 'ply':
    bpy.ops.import_mesh.ply(filepath=shape_file)
    bpy.ops.transform.resize(value=(0.001, 0.001, 0.001))

bpy.context.scene.render.alpha_mode = 'TRANSPARENT'
#bpy.context.scene.render.use_shadows = False
#bpy.context.scene.render.use_raytrace = False

bpy.data.objects['Lamp'].data.energy = 0

#m.subsurface_scattering.use = True

camObj = bpy.data.objects['Camera']
# camObj.data.lens_unit = 'FOV'
# camObj.data.angle = 0.2

# set lights
bpy.ops.object.select_all(action='TOGGLE')
if 'Lamp' in list(bpy.data.objects.keys()):
    bpy.data.objects['Lamp'].select = True # remove default light
bpy.ops.object.delete()

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
    syn_image_file = './%s_%s_a%03d_e%03d_t%03d_d%03d.png' % (shape_synset, shape_md5, round(azimuth_deg), round(elevation_deg), round(theta_deg), round(rho))
    bpy.data.scenes['Scene'].render.filepath = os.path.join(syn_images_folder, syn_image_file)
    bpy.ops.render.render( write_still=True )

