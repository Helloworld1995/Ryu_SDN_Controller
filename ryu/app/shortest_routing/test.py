import numpy as np
from scipy import spatial
import matplotlib.pyplot as plt
from sko.GA import GA_TSP
import pandas as pd
import time
import random
class hehe():
    def __init__(self):
        self.switch=[1001,1002,1003,1004]
        self.flow_nums=100
        self.flow=list(range(1,self.flow_nums+1))
        self.flows={}
        self.k=0
        self.init()

    # for i in range(1,flow_nums+1):
    #     k=k+1
    #     switch.append(1000 + k)
    #     if(i%4==0):
    #         k=0
    def init(self):
        for i in self.flow:
            self.flows[i]={}


    def cal_total_weight(self,routine):
        '''The objective function. input routine, return total distance.
        cal_total_distance(np.arange(num_points))
        '''
        print(routine[0])
        count=0
        flows_ = self.flows
        flow_list = routine
        for i in range(self.flow_nums):
            flows_[i+1][i+1]=flow_list[i]%4+1001

        for k in flows_:
            for j in flows_[k]:
             count=count+j*(flows_[k][j]%1000)
        return count
    def GA_go(self):
        ga_tsp = GA_TSP(func=self.cal_total_weight, points=self.flow, pop=50, max_iter=100, Pm=0.01)
        best_goods, best_value=ga_tsp.fit()
        print(best_goods,best_value)
        Y_history = pd.DataFrame(ga_tsp.FitV_history)
        fig,ax = plt.subplots(2, 1)
        ax[0].plot(Y_history.index, Y_history.values, '.', color='red')
        Y_history.min(axis=1).cummin().plot(kind='line')
        plt.show()
hehe().GA_go()