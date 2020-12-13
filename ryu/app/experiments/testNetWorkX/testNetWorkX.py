import networkx as nx
import matplotlib.pyplot as plt

G=nx.DiGraph()
G.add_node(1)

G.add_node(3)
G.add_node(4)
G.add_node(5)

G.add_edge(1,3)
G[1][3]['bw']=1
G.add_edge(1,4)
G[1][4]['bw']=2
G.add_edge(4,5)
G[4][5]['bw']=2
G.add_edge(5,3)
G[5][3]['bw']=1
nx.draw(G,with_labels=True)

path=nx.shortest_path(G,1,3,weight='bw',method='dijkstra')

print(path)
plt.show()

