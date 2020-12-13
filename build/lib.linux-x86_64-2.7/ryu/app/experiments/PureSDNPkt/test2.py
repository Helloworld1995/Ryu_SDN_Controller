
import matplotlib.pyplot as plt
from sko.GA import GA_TSP
import pandas as pd

switch=[1001,1002,1003,1004]
flow_nums=50
flow=list(range(1,flow_nums+1))
flows={}
k=0
for i in flow:
    flows[i]={}

# for i in range(1,flow_nums+1):
#     k=k+1
#     switch.append(1000 + k)
#     if(i%4==0):
#         k=0

def cal_total_weight(routine):
    '''The objective function. input routine, return total distance.
    cal_total_distance(np.arange(num_points))
    '''
    count=0
    flows_ = flows
    flow_list = routine
    for i in range(flow_nums):
        flows_[i+1][i+1]=flow_list[i]%4+1001
    for k in flows_:
        for j in flows_[k]:
            count=count+j*(flows_[k][j]%1000)
    return count

def kakak():
    ga_tsp = GA_TSP(func=cal_total_weight, n_dim=flow_nums, size_pop=50, max_iter=200, prob_mut=0.06)
    best_goods, best_value=ga_tsp.run()
    print(best_goods,best_value)
    point2(ga_tsp)

def start():
    kakak()

def point(ga_tsp):
    Y_history = pd.DataFrame(ga_tsp.all_history_Y)
    fig, ax = plt.subplots(2, 1)
    ax[0].plot(Y_history.index, Y_history.values, '.', color='red')
    Y_history.min(axis=1).cummin().plot(kind='line')
    plt.show()

def point2(ga_tsp):
    Y_history = ga_tsp.generation_best_Y
    print(Y_history)
    index=list(range(0,len(Y_history)))
    values=list(Y_history)
    fig = plt.figure()
    ax = fig.add_subplot(1, 1, 1)
    ax.plot(index, values)
    plt.show()
start()
