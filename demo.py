#coding=utf-8
from __future__ import division

from models import *
from utils.utils import *
from utils.datasets import *

import os
import sys
import time
import datetime
import argparse
import cv2 as cv

from PIL import Image

import torch
from torch.utils.data import DataLoader
from torchvision import datasets
from torch.autograd import Variable

import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.ticker import NullLocator
from torch.utils.tensorboard import SummaryWriter
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--image_path", type=str, default="data/samples/dog.jpg", help="path to image")
    parser.add_argument("--model_def", type=str, default="config/yolov3.cfg", help="path to model definition file")
    parser.add_argument("--weights_path", type=str, default="weights/yolov3.weights", help="path to weights file")
    parser.add_argument("--class_path", type=str, default="data/coco.names", help="path to class label file")
    parser.add_argument("--conf_thres", type=float, default=0.8, help="object confidence threshold")
    parser.add_argument("--nms_thres", type=float, default=0.4, help="iou thresshold for non-maximum suppression")
    parser.add_argument("--batch_size", type=int, default=4, help="size of the batches")
    parser.add_argument("--n_cpu", type=int, default=0, help="number of cpu threads to use during batch generation")
    parser.add_argument("--img_size", type=int, default=416, help="size of each image dimension")
    parser.add_argument("--checkpoint_model", type=str, help="path to checkpoint model")
    opt = parser.parse_args()
    print(opt)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    os.makedirs("output", exist_ok=True)

    log_writer = SummaryWriter(log_dir='logs',comment='yolov3')

    # Set up model
    model = Darknet(opt.model_def, img_size=opt.img_size).to(device)

    if opt.weights_path.endswith(".weights"):
        # Load darknet weights
        model.load_darknet_weights(opt.weights_path)
    else:
        # Load checkpoint weights
        model.load_state_dict(torch.load(opt.weights_path))

    model.eval()  # Set in evaluation mode

    dataloader = DataLoader(
        ImagePath(opt.image_path, img_size=opt.img_size),
        batch_size=opt.batch_size,
        shuffle=False,
        num_workers=opt.n_cpu,
    )

    classes = load_classes(opt.class_path)  # Extracts class labels from file

    Tensor = torch.cuda.FloatTensor if torch.cuda.is_available() else torch.FloatTensor

    imgs = []  # Stores image paths
    img_detections = []  # Stores detections for each image index

    print("\nPerforming object detection:")
    prev_time = time.time()
    for batch_i, (img_paths, input_img) in enumerate(dataloader):
        # Configure input
        input_img = Variable(input_img.type(Tensor))

        
        # with torch.no_grad():
        #     log_writer.add_graph(model, input_img)

        # Get detections
        with torch.no_grad():
            detections = model(input_img)
            log_writer.add_graph(model, input_img)         #模型日志
            detections = non_max_suppression(detections, opt.conf_thres, opt.nms_thres)
            #log_writer.add_graph(model, input_img)         #模型日志

        # Log progress
        current_time = time.time()
        inference_time = datetime.timedelta(seconds=current_time - prev_time)
        prev_time = current_time
        print("\t+ Batch %d, Inference Time: %s" % (batch_i, inference_time))

        # Save image and detections
        imgs.extend(img_paths)   #将 img_paths全部添加在imgs后面
        img_detections.extend(detections)

    image_path1 = imgs[0]
    img_detection1 = img_detections[0]
    
    im = cv.imread(image_path1)
    if img_detection1 is not None:
        print (detections)
        # Rescale boxes to original image
        img_detection1 = rescale_boxes(img_detection1, opt.img_size, im.shape[:2])
        unique_labels = img_detection1[:, -1].cpu().unique()
        n_cls_preds = len(unique_labels)
        for x1, y1, x2, y2, conf, cls_conf, cls_pred in img_detection1:
            print("\t+ Label: %s, Conf: %.5f" % (classes[int(cls_pred)], cls_conf.item()))
            cv.rectangle(im,(int(x1),int(y1)),(int(x2),int(y2)),(0,255,0),3)
        
    cv.imshow('detect',im)
    cv.waitKey(0)
    cv.destroyAllWindows()    

    
    
