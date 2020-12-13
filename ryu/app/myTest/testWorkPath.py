import os
import ryu.app.experiments.iperf_peers_fsize as peers
print os.getcwd()

for p in peers.iperf_peers:
    print p

