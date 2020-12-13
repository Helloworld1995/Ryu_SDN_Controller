

import matplotlib.pyplot as plt
# import pandas as pd
import numpy as np
from sko.GA import GA_TSP
import time
import setting
from ryu.base.app_manager import lookup_service_brick
import SRrouting as shortest_forwarding
import network_awareness as awareness

def _GA_Fit(routine):
    j=-1
    sf = lookup_service_brick('shortest_forwarding')
    awareness = lookup_service_brick('awareness')
    Max_value=setting.MAX_CAPACITY*10240
    graph =awareness.graph.copy()
    traffics=sf.traffics
    flow_code = routine
    minBand = Max_value
    for k in flow_code:
        j = j + 1
        f=traffics[j]
        speed = f['speed']
        swPair=f['swPair']
        core=1001 + k % 4
        paths=sf.paths[swPair]
        if paths==None:
            paths=sf._ip2sw(swPair)
        for path in paths:
            if path[int((len(path) - 1) / 2)] == core:
                for i in xrange(0, len(path) - 1):
                    graph[path[i]][path[i + 1]]['bandwidth']=graph[path[i]][path[i + 1]]['bandwidth']*1024 - speed*8# consider the flow_demand
                    # spare=graph[path[i]][path[i + 1]].get('bandwidth')-(speed*8)/1024
                    if minBand>graph[path[i]][path[i + 1]]['bandwidth']:
                        minBand=graph[path[i]][path[i + 1]]['bandwidth']
    # show_topo(graph, awareness)

    # flow_band_list=[]
    # for link in graph.edges():
    #     node1 = link[0]
    #     node2 = link[1]
    #     flow_band_list.append(graph[node1][node2].get('bandwidth'))
    # sd=np.std(flow_band_list,ddof=1)
    # # min_bw=min(flow_band_list)
    # return sd / 1024.000
    # minBand = Max_value
    # for link in graph.edges():
    #      node1=link[0]
    #      node2=link[1]
    #      bw=graph[node1][node2].get('bandwidth')
    #      minBand = min(minBand, int(bw))
     #print("the minimal num is ----------->%d"%fit)
    # show_topo(graph,awareness)
    return Max_value/minBand
   # return Max_value if minBand==0 else (Max_value/minBand)

    # return setting.MAX_CAPACITY-min_bw



def _GA_start(flows_len):

    if(flows_len%2!=0):
        flows_len=flows_len-1
    len=flows_len
    ga_tsp = GA_TSP(func=_GA_Fit, n_dim=len, size_pop=len, max_iter=200,prob_mut=0.06)
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