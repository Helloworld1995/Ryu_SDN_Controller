import networkx as nx
import random as rand
import matplotlib.pyplot as plt
def read():
    f = open('/home/lee/test/test_data.txt', 'a+')
    vertext=set()
    edge={}
    while True:
        line = f.readline().strip()
        if line:
            a1,a2,a3 = line.split(',')
            a1=int(a1)
            a2=int(a2)
            vertext.add(a1)
            vertext.add(a2)
            if a1 not in edge.keys():
                edge[a1]=[]
            edge[a1].append(a2)

        else:
            break
    return edge,vertext
def buildGraph():
    edge,vertext=read()
    G=nx.DiGraph()
    for node in vertext:
        G.add_node(node)
    for node1 in edge.keys():
        for node2 in edge[node1]:
            G.add_edge(node1,node2)
    nx.draw(G)
    paths=nx.shortest_simple_paths
    str(paths)
    print paths
    plt.show()
buildGraph()







