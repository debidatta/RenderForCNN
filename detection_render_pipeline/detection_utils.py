import glob
import cv2
import matplotlib.pyplot as plt

def get_bbox(im_file, visualize=False):
    """Gets bounding box of a single object in a image against a black background"""
    im = cv2.imread(im_file)
    non_black_pixels = im.any(axis=-1).nonzero() 
    bbox = [min(non_black_pixels[1][:]), min(non_black_pixels[0][:]),
            max(non_black_pixels[1][:]), max(non_black_pixels[0][:])]
    if visualize:
        vis_bbox(im, bbox)
        plt.show()
    return bbox

def get_bboxes(path_rendered_images, output_file, ext='.jpg'):
    with open(output_file, 'w') as f:
        for im_file in glob.glob(path_rendered_images+'/*/*'+ext):
            f.write('%s '%im_file)
            bbox =  get_bbox(im_file)
            f.write('%s %s %s %s\n'%(tuple(bbox)))

def vis_bbox(im, bbox):
    """Draw detected bounding boxes. Adapted from Ross Girshick's Fast R-CNN"""
    im = im[:, :, (2, 1, 0)]
    fig, ax = plt.subplots(figsize=(12, 12))
    ax.imshow(im, aspect='equal')
    ax.add_patch(
            plt.Rectangle((bbox[0], bbox[1]),
                          bbox[2] - bbox[0],
                          bbox[3] - bbox[1], fill=False,
                          edgecolor='red', linewidth=3.5)
            )

    plt.axis('off')
    plt.tight_layout()
    plt.draw()

