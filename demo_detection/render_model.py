#!/usr/bin/python

import os.path as osp
import sys
import argparse
import os, tempfile, glob, shutil
import traceback

BASE_DIR = osp.dirname(__file__)
sys.path.append(osp.join(BASE_DIR,'../'))
from global_variables import *


parser = argparse.ArgumentParser(description='Render Model Images of a certain class and view')
parser.add_argument('model_file', help='CAD Model obj filename', default=osp.join(BASE_DIR,'/media/dey/debidatd/desk3d/ferrari/mesh_ferrari.obj'))#'sample_model/model.obj'))
parser.add_argument('keypoint_file', help='Chosen Keypoint list file')
parser.add_argument('-a', '--azimuth', default='45')
parser.add_argument('-e', '--elevation', default='20')
parser.add_argument('-t', '--tilt', default='0')
parser.add_argument('-d', '--distance', default='2.0')
parser.add_argument('-o', '--output_img', help='Output img filename.', default=osp.join(BASE_DIR, 'demo_img.png'))
parser.add_argument('-l', '--output_label', help='Output label filename.', default=osp.join(BASE_DIR, 'demo_label.txt'))
parser.add_argument('-s', '--scale', help='Scale factor if model not in metres.', default=0.001)
args = parser.parse_args()

blank_file = osp.join(g_blank_blend_file_path)
render_code = osp.join(g_render4cnn_root_folder, 'render_pipeline/render_model.py')

# MK TEMP DIR
temp_dirname = tempfile.mkdtemp()
view_file = osp.join(temp_dirname, 'view.txt')
view_fout = open(view_file,'w')
view_fout.write(' '.join([args.azimuth, args.elevation, args.tilt, args.distance, args.output_img, args.output_label]))
view_fout.close()

try:
    render_cmd = '%s %s --background --python %s -- %s %s %s %s %s %s' % (g_blender_executable_path, blank_file, render_code, args.model_file, args.keypoint_file, 'xxx', view_file, temp_dirname, args.scale)
    print render_cmd
    os.system(render_cmd)
    #imgs = glob.glob(temp_dirname+'/*.png')
    #labels = glob.glob(temp_dirname+'/*.label')
    #shutil.move(imgs[0], args.output_img)
    #shutil.move(labels[0], args.output_label)
except Exception, err:
    print('render failed. render_cmd: %s' % (render_cmd))
    print(traceback.format_exc())
# CLEAN UP
shutil.rmtree(temp_dirname)
