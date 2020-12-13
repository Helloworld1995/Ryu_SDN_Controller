

import matplotlib.pyplot as plt
# import pandas as pd
import numpy as np
from sko.GA import GA_TSP
import time
# import network_monitor
# import network_awareness
import setting
from ryu.base.app_manager import lookup_service_brick


def _GA_Fit(routine):
    j=-1
    fit=0
    gpGaProcessor()
    Max_value=setting.MAX_CAPACITY*100000
    monitor=gp.monitor
    awareness=gp.awareness
    graph =awareness.graph.copy()
    traffics=gp.monitor.traffics
    flow_code = routine
    for k in flow_code:
        j = j + 1
        f=traffics[j]
        src = f['src']
        dst = f['dst']
        speed = f['speed']
        demand=f['demand']
        core=1001 + k % 4
        paths=monitor._ip2sw(src,dst)
        for path in paths:
            if path[int((len(path) - 1) / 2)] == core:
                # print(path)
                for i in xrange(0, len(path) - 1):
                    spare=graph[path[i]][path[i + 1]].get('bandwidth') - setting.MAX_CAPACITY*demand * 8/10
                    graph[path[i]][path[i + 1]]['bandwidth']=max(spare,0.0)

    minBand = Max_value
    for link in graph.edges():
        node1=link[0]
        node2=link[1]
        if(node1,node2) in awareness.link_to_port.keys():
            bw = graph[node1][node2].get('bandwidth')
            minBand = min(minBand, bw)
    show_topo(graph,awareness)
    return Max_value*10 if minBand==0.0 else Max_value/minBand



class GaProcessor():
    monitor=None
    awareness=None
    def __init__(self):
        self.monitor = lookup_service_brick('monitor')
        self.awareness = lookup_service_brick('awareness')
    def _GA_start(self,flows_len):

        if(flows_len%2!=0):
            flows_len=flows_len-1
        len=flows_len
        ga_tsp = GA_TSP(func=_GA_Fit, n_dim=len, size_pop=len, max_iter=100,prob_mut=0.05)
        best_goods, best_value = ga_tsp.run()
        print(best_goods, best_value)
        point2(ga_tsp)
        return best_goods

# def point(ga_tsp):
#
#     fit_history = pd.DataFrame(ga_tsp.Y_history)
#     fig, ax = plt.subplots(2, 1)
#     ax[0].plot(fit_history.index, fit_history.values, '.', color='red')
#     fit_history.min(axis=1).cummin().plot(kind='line')
#     plt.show()
def point2(ga_tsp):
    Y_history = ga_tsp.generation_best_Y
    #print(ga_tsp.all_history_Y)
    index=list(range(0,len(Y_history)))
    values=list(Y_history)
    fig = plt.figure()
    ax = fig.add_subplot(1, 1, 1)
    ax.plot(index, values)
    # plt.show()
    plt.pause(3)
    # plt.close()
def show_topo(graph,awareness):
    print "\n---------------------Link Port---------------------"
    print '%6s' % ('switch'),
    for node in sorted([node for node in graph.nodes()], key=lambda node: node):
        print '%6d' % node,
    print
    for node1 in sorted([node for node in graph.nodes()], key=lambda node: node):
        print '%6d' % node1,
        for node2 in sorted([node for node in graph.nodes()], key=lambda node: node):
            if (node1, node2) in awareness.link_to_port.keys():
                print '%6s' % str(awareness.link_to_port[(node1, node2)]),
                print('%6s' % str(graph[node1][node2]['bandwidth']))
            else:
                print '%6s' % '/',
        print
    print