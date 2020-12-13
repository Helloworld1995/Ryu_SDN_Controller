import numpy as np
from scipy import spatial
import matplotlib.pyplot as plt
from sko.GA import GA_TSP
import pandas as pd
import time
import random






# for i in range(1,flow_nums+1):
#     k=k+1
#     switch.append(1000 + k)
#     if(i%4==0):
#         k=0


switch = [1001, 1002, 1003, 1004]
flow_nums = 20
flow = list(range(1, flow_nums + 1))
flows = {}
k = 0
for i in flow:
    flows[i] = {}
def cal_total_weight(routine):
    '''The objective function. input routine, return total distance.
    cal_total_distance(np.arange(num_points))
    '''

    count=Ga_Test().count
    flows_ = flows
    flow_list = routine
    for i in range(flow_nums):
        flows_[i+1][i+1]=flow_list[i]%4+1001
    for k in flows_:
        for j in flows_[k]:
            count=count+j*(flows_[k][j]%1000)
    return count
class Ga_Test():
    def __init__(self):
        self.count = 0
    def kaka(self):

        ga_tsp = GA_TSP(func=cal_total_weight, n_dim=flow_nums ,size_pop=flow_nums, max_iter=500, prob_mut=0.01)
        best_goods, best_value=ga_tsp.run()
        print(best_goods,best_value)
        fit_history = pd.DataFrame(ga_tsp.all_history_Y)
        fig, ax = plt.subplots(2, 1)
        ax[0].plot(fit_history.index, fit_history.values, '.', color='red')
        plt_min=fit_history.min(axis=1)
        ax[1].plot(plt_min.index,plt_min,Label='min')
        ax[1].plot(plt_min.index, plt_min.cummin())
        # fit_history.max(axis=1).cummin().plot(kind='line')
        plt.show()
Ga_Test().kaka()
# def start():
#     kakak()

def point(ga_tsp):
    fit_history = pd.DataFrame(ga_tsp.generation_best_Y)
    fig, ax = plt.subplots(2, 1)
    ax[0].plot(fit_history.index, fit_history.values, '.', color='red')
    plt_min=fit_history.min(axis=1)
    ax[1].plot(plt_min.index,plt_min,Label='min')
    ax[1].plot(plt_min.index, plt_min.cummin())
    # fit_history.max(axis=1).cummin().plot(kind='line')
    plt.show()
