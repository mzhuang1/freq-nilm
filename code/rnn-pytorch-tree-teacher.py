from common import APPLIANCES_ORDER
import sys
appliance, num_hidden, num_iterations, num_layers = sys.argv[1:]
num_hidden = int(num_hidden)
num_layers = int(num_layers)
num_iterations = int(num_iterations)


import numpy as np

import pandas as pd
tensor = np.load('../1H-input.npy')


def create_subset_dataset(tensor, start=160, num_days=112):
    t_subset = tensor[:, :, start:start + num_days, :]
    all_indices = np.array(list(range(320)))
    for i in range(1, 7):
        valid_homes = pd.DataFrame(t_subset[:, i, :].reshape(320, num_days * 24)).dropna().index
        all_indices = np.intersect1d(all_indices, valid_homes)
    print(len(all_indices))
    t_subset = t_subset[all_indices, :, :, :].reshape(len(all_indices), 7, num_days * 24)

    # Create artificial aggregate
    t_subset[:, 0, :] = 0.0
    for i in range(1, 7):
        t_subset[:, 0, :] = t_subset[:, 0, :] + t_subset[:, i, :]
    # t_subset is of shape (#home, appliance, days*hours)
    return t_subset, all_indices

t_all, valid_homes = create_subset_dataset(tensor)

num_days = 112
train_agg = t_all[:30, 0, :].reshape(30*num_days, 24)

train_hvac = t_all[:30, 1, :].reshape(30*num_days, 24)
train_fridge = t_all[:30, 2, :].reshape(30*num_days, 24)
train_mw = t_all[:30, 3, :].reshape(30*num_days, 24)
train_dw = t_all[:30, 4, :].reshape(30*num_days, 24)
train_wm = t_all[:30, 5, :].reshape(30*num_days, 24)
train_oven = t_all[:30, 6, :].reshape(30*num_days, 24)








train_agg_new = train_hvac + train_fridge





test_hvac = t_all[30:52, 1, :].reshape(22*num_days, 24)
test_fridge = t_all[30:52, 2, :].reshape(22*num_days, 24)
test_mw = t_all[30:52, 3, :].reshape(22*num_days, 24)
test_dw = t_all[30:52, 4, :].reshape(22*num_days, 24)
test_wm = t_all[30:52, 5, :].reshape(22*num_days, 24)
test_oven = t_all[30:52, 6, :].reshape(22*num_days, 24)









test_agg = t_all[30:, 0, :].reshape(22*num_days, 24)
test_agg_new = test_hvac + test_fridge

import torch
import torch.nn as nn
from torch.autograd import Variable

torch.manual_seed(0)
np.random.seed(0)

input_dim = 1
hidden_size = 200
num_layers = 1


class CustomRNN(nn.Module):
    def __init__(self, input_size, hidden_size, output_size):
        super(CustomRNN, self).__init__()
        self.rnn = nn.GRU(input_size=input_size, hidden_size=hidden_size, num_layers=num_layers, batch_first=True)
        self.linear = nn.Linear(hidden_size, output_size, )

    def forward(self, x):
        pred, hidden = self.rnn(x, None)
        pred = self.linear(pred).view(pred.data.shape[0], -1, 1)
        pred = torch.clamp(pred, min=0.)
        pred = torch.min(pred, x)

        return pred

ORDER = ['hvac','fridge','oven','dw','mw','wm'][:3]

class AppliancesRNN(nn.Module):
    def __init__(self, input_size, hidden_size, output_size, num_appliance):
        super(AppliancesRNN, self).__init__()
        self.num_appliance = num_appliance
        self.preds = {}
        self.order = ORDER
        for appliance in range(self.num_appliance):
            setattr(self, "Appliance_" + str(appliance), CustomRNN(input_size, hidden_size, output_size))

    def forward(self, agg, hvac, fridge, oven, p):
        agg_current = agg
        flag = False
        if np.random.random() > p:
            flag = True
            print("Subtracting prediction")
        else:
            print("Subtracting true")
        for appliance in range(self.num_appliance):
            self.preds[appliance] = getattr(self, "Appliance_" + str(appliance))(agg_current)
            if flag:
                agg_current = agg_current - self.preds[appliance]

            else:
                agg_current = agg_current - eval(self.order[appliance])

        return torch.cat([self.preds[a] for a in range(self.num_appliance)])


a = AppliancesRNN(input_dim, hidden_size, 1, len(ORDER))
print(a)
# Storing predictions per iterations to visualise later
predictions = []

optimizer = torch.optim.Adam(a.parameters(), lr=2)
loss_func = nn.L1Loss()

out_train = {}
for appliance in ORDER:
    out_train[appliance] = Variable(torch.Tensor(eval("train_"+appliance).reshape((train_agg.shape[0], -1, 1))))

for t in range(num_iterations):

    inp = Variable(torch.Tensor(train_agg.reshape((train_agg.shape[0], -1, 1))), requires_grad=True)


    out = torch.cat([out_train[appliance] for appliance in ORDER])

    pred = a(inp, out_train['hvac'], out_train['fridge'],
             out_train['oven'], 0.8)

    optimizer.zero_grad()
    predictions.append(pred.data.numpy())
    loss = loss_func(pred, out)
    if t % 10 == 0:
        print(t, loss.data[0])
    loss.backward()
    optimizer.step()

test_inp = Variable(torch.Tensor(test_agg.reshape((test_agg.shape[0], -1, 1))), requires_grad=True)
test_pred = a(test_inp, None, None, None,  -2).data.numpy().reshape(-1, 24)

from sklearn.metrics import mean_absolute_error



