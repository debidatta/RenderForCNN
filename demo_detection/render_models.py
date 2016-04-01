#!/usr/bin/python

import os.path as osp
import sys
import argparse
import os, tempfile, glob, shutil
import numpy as np

BASE_DIR = osp.dirname(__file__)
sys.path.append(osp.join(BASE_DIR,'../'))
from global_variables import *

parser = argparse.ArgumentParser(description='Render Model Images of a certain class and view')
parser.add_argument('model_file', help='CAD Model obj filename', default=osp.join(BASE_DIR,'sample_model/model.obj'))
parser.add_argument('keypoint_file', help='Chosen Keypoint list file')
parser.add_argument('output_folder', help='output folder')
parser.add_argument('-s', '--scale', help='Scale factor if model not in metres.', default=0.001)
parser.add_argument('-n', '--num_renders', help='Number of instances at each distance', default=1500, type=int)
args = parser.parse_args()

temp_dirname = tempfile.mkdtemp()
view_file = osp.join(temp_dirname, 'view.txt')
view_fout = open(view_file,'w')
blank_file = osp.join(g_blank_blend_file_path)
render_code = osp.join(g_render4cnn_root_folder, 'render_pipeline/render_model.py')

distances = [1, 1.25, 1.5, 1.75, 2, 2.4, 2.8, 3.2, 4, 5, 6, 8]
for d in distances:
    for i in xrange(args.num_renders):
        u = np.random.random()
        v = np.random.random()
        e = int(90.0*u)
        a = 360.0 * np.arccos(2.0*v - 1)/np.pi
        img_file = osp.join(args.output_folder, 'images', 'syn_a%03d_e%03d_t%03d_d%04d.png' % (a, e, 0, int(1000*d)))
        lbl_file = osp.join(args.output_folder, 'labels', 'syn_a%03d_e%03d_t%03d_d%04d.txt' % (a, e, 0, int(1000*d))) 
        tmp_string = '%f %f 0 %f %s %s\n' % (a, e, d, img_file, lbl_file)
        view_fout.write(tmp_string)
view_fout.close()
render_cmd = '%s %s --background --python %s -- %s %s %s %s %s %s' % (g_blender_executable_path, blank_file, render_code, args.model_file, args.keypoint_file, 'xxx', view_file, temp_dirname, args.scale)
os.system(render_cmd)
