import os
import sys
import argparse
import numpy as np
from tqdm import tqdm
import torch

from model import *
from dataloader import DatasetVal
from utils import *
from logger import Logger, ModelLogger, prepare_opt


device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

def get_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('-d', '--data', type=str, default='./data/', help='path to your dataset')
    parser.add_argument('-c', '--config', type=str, default='./config/unet.json', help='path to config JSON')
    parser.add_argument('-f', '--flag', type=str, help='id of the run')
    return prepare_opt(parser)


def restore_model(mname, logger):
    assert logger.path_existed, f"Path {logger.dir_save} not found"
    model_logger = ModelLogger(logger, state_only=True)
    model_logger.metric_name = 'iou'

    # ===== Model =====
    model = get_model(mname)
    model = model_logger.load_model('best', model=model).to(device)
    model.eval()
    return model


if __name__ == '__main__':
    args = get_args()
    BACH_SIZE = args.batch

    val_dataset = DatasetVal(args.data)
    val_dataloader = torch.utils.data.DataLoader(val_dataset, batch_size=BACH_SIZE, shuffle=False, num_workers=1)

    flag_run = "{}_{}".format(args.loss, args.flag)
    logger = Logger(prj_name=args.model, flag_run=flag_run)
    model = restore_model(args.model, logger)

    intersection_meter = AverageMeter()
    union_meter = AverageMeter()
    for batch_i, (x, y) in enumerate(tqdm(val_dataloader)):
        with torch.no_grad():
            pred_mask = model(x.to(device))
        pred_mask = torch.softmax(pred_mask, dim=1)
        y_pred = torch.argmax(pred_mask, dim=1)
        intersection, union, target = intersectionAndUnionGPU(y_pred, y.to(device), 12)
        intersection_meter.update(intersection)
        union_meter.update(union)

    iou_class = intersection_meter.sum / (union_meter.sum + 1e-10)
    np.save(logger.path_join('iou_mat.npy'), iou_class.cpu().numpy())

    mIoU = torch.mean(iou_class)
    print(f"mIoU: {mIoU}")
    msg = ', '.join(['{:.4f}'.format(t) for t in iou_class])
    print(msg)
