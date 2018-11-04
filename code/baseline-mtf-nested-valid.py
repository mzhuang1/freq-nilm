import sys
import numpy as np
import pandas as pd
from dataloader import APPLIANCE_ORDER, get_train_test
from tensor_custom_core import stf_4dim, stf_4dim_time
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error
import os

num_folds = 5


def nested_stf(dataset, cur_fold, r, lr, num_iter):

    train, test = get_train_test(dataset, num_folds=num_folds, fold_num=cur_fold)
    #train, valid = train_test_split(train, test_size=0.2, random_state=0)
    valid = train[int(0.8*len(train)):].copy()
    train = train[:int(0.8 * len(train))].copy()
    
    valid_gt = valid[:, 1:, :, :]
    test_gt = test[:, 1:, :, :]


    valid_copy = valid.copy()
    valid_copy[:, 1:, :, :] =np.NaN
    train_valid = np.concatenate([train, valid_copy])
    H, A, D, T = stf_4dim_time(tensor=train_valid, r=r, lr=lr, num_iter=num_iter)
    valid_pred = np.einsum("Hr, Ar, Dr, ATr -> HADT", H, A, D, T)[len(train):, 1:, :, :]
    valid_error = {APPLIANCE_ORDER[i+1]:mean_absolute_error(valid_pred[:, i,:,:].flatten(), 
                                                                       valid_gt[:, i, :, :].flatten()) for i in range(valid_pred.shape[1])}
    
    
    
    return valid_pred, valid_error, valid_gt

dataset, cur_fold, r, lr, num_iter= sys.argv[1:]
dataset = int(dataset)
cur_fold = int(cur_fold)
r = int(r)
lr = float(lr)
num_iter = int(num_iter)
directory = "./baseline/mtf/{}/valid/".format(dataset)
if not os.path.exists(directory):
    os.makedirs(directory)

valid_pred, valid_error, valid_gt = nested_stf(dataset, cur_fold, r, lr, num_iter)

np.save("./baseline/mtf/{}/valid/mtf-pred-{}-{}-{}-{}-{}.npy".format(dataset,dataset, cur_fold, r, lr, num_iter), valid_pred)
np.save("./baseline/mtf/{}/valid/mtf-error-{}-{}-{}-{}-{}.npy".format(dataset,dataset, cur_fold, r, lr, num_iter), valid_error)

