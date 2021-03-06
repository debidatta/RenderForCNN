#!/usr/bin/python3
# -*- coding: utf-8 -*-

import os
import sys
import shutil
import random
import tempfile
import datetime
from functools import partial
from multiprocessing.dummy import Pool
from subprocess import call
import numpy as np

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.dirname(BASE_DIR))
from global_variables import *

'''
@input: 
    shape_synset e.g. '03001627' (each category has a synset)
@output: 
    a list of (synset, md5, obj_filename, view_num) for each shape of that synset category
    where synset is the input synset, md5 is md5 of one shape in the synset category,
    obj_filename is the obj file of the shape, view_num is the number of images to render for that shape
'''
def load_one_category_shape_list(shape_synset):
    # return a list of (synset, md5, numofviews) tuples
    shape_md5_list = os.listdir(os.path.join(g_shapenet_root_folder,shape_synset))
    n_models = len(shape_md5_list)
    view_nums = np.bincount(np.random.choice(n_models, g_syn_images_num_per_category), minlength=n_models) 
    shape_list = []
    for i, view_num in enumerate(view_nums):
        if view_num != 0:
	    shape_list.append((shape_synset, shape_md5_list[i], os.path.join(g_shapenet_root_folder, shape_synset, shape_md5_list[i], 'model.obj'), view_num))
    return shape_list

'''
@input: 
    shape synset
@output:
    samples of viewpoints (plus distances) from pre-generated file, each element of view_params is
    a list of azimuth,elevation,tilt angles and distance
'''
def load_one_category_shape_views(synset):
    # return shape_synset_view_params
    if not os.path.exists(g_view_distribution_files[synset]):
        print('Failed to read view distribution files from %s for synset %s. Will use uniform random distribution for view parameters' % 
              (g_view_distribution_files[synset], synset))
	if g_model_view_params_proxy_use:
	    idx = g_shape_names.index(g_model_view_params_proxy_category)
	    proxy_synset = g_shape_synsets[idx]
	    view_params = open(g_view_distribution_files[proxy_synset]).readlines()
	    view_params = [[float(x) for x in line.strip().split(' ')] for line in view_params]
	else:
	    view_params = []
    else:
        view_params = open(g_view_distribution_files[synset]).readlines()
        view_params = [[float(x) for x in line.strip().split(' ')] for line in view_params] 
    return view_params

'''
@input:
    shape_list and view_params as output of load_one_category_shape_list/views
@output:
    save rendered images to g_syn_images_folder/<synset>/<md5>/xxx.png
''' 
def render_one_category_model_views(shape_list, view_params):
    tmp_dirname = tempfile.mkdtemp(dir=g_data_folder, prefix='tmp_view_')
    if not os.path.exists(tmp_dirname):
        os.mkdir(tmp_dirname)

    print('Generating rendering commands...')
    commands = []
    for shape_synset, shape_md5, shape_file, view_num in shape_list:
        # write tmp view file
        tmp = tempfile.NamedTemporaryFile(dir=tmp_dirname, delete=False)
        for i in range(view_num):
	    if len(view_params) != 0:
                paramId = random.randint(0, len(view_params)-1)
                tmp_string = '%f %f %f %f\n' % (view_params[paramId][0], view_params[paramId][1], view_params[paramId][2], max(0.01,view_params[paramId][3]))
            else:
	        azimuth = random.uniform(g_model_azimuth_degree_lowbound, g_model_azimuth_degree_highbound)
		elevation = random.uniform(g_model_elevation_degree_lowbound, g_model_elevation_degree_highbound)
		tilt = random.uniform(g_model_tilt_degree_lowbound, g_model_tilt_degree_highbound)
		distance = random.uniform(g_model_dist_lowbound, g_model_dist_highbound)
		tmp_string = '%f %f %f %f\n' % (azimuth, elevation, tilt, max(0.01,distance))
	    tmp.write(tmp_string)
        tmp.close()

        command = '%s %s --background --python %s -- %s %s %s %s %s > /dev/null 2>&1' % (g_blender_executable_path, g_blank_blend_file_path, os.path.join(BASE_DIR, 'render_model_views.py'), shape_file, shape_synset, shape_md5, tmp.name, os.path.join(g_syn_images_folder, shape_synset, shape_md5))
        commands.append(command)
    print('done (%d commands)!'%(len(commands)))
    print commands[0]

    print('Rendering, it takes long time...')
    report_step = 100
    if not os.path.exists(os.path.join(g_syn_images_folder, shape_synset)):
        os.mkdir(os.path.join(g_syn_images_folder, shape_synset))
    pool = Pool(g_syn_rendering_thread_num)
    for idx, return_code in enumerate(pool.imap(partial(call, shell=True), commands)):
        if idx % report_step == 0:
            print('[%s] Rendering command %d of %d' % (datetime.datetime.now().time(), idx, len(shape_list)))
        if return_code != 0:
            print('Rendering command %d of %d (\"%s\") failed' % (idx, len(shape_list), commands[idx]))
    shutil.rmtree(tmp_dirname) 

