import networkx as nx
import random as rand
import matplotlib.pyplot as plt

def test():
    G=nx.Graph()
    G.add_edge(1,2,weight=3)
    G.add_edge(2,3,weight=8)
    G.add_edge(1,4,weight=4)
    G.add_edge(1,5,weight=1)
    G.add_edge(2,5,weight=5)
    G.add_edge(5, 2, weight=5)
    G.add_edge(4,5,weight=9)
    G.add_edge(5,3,weight=1)
    G.add_edge(5,6,weight=8)
    G.add_edge(3,6,weight=2)

    path1=nx.shortest_path(G,1,6,weight="weight")
    print path1
    G.remove_edge(5, 3)
    p1=nx.shortest_path(G,1,5,weight="weight")
    p2=nx.shortest_path(G,5,3,weight="weight")

    path=p1+p2
    nx.draw(G,data=True)
    plt.show()
    print path
test()