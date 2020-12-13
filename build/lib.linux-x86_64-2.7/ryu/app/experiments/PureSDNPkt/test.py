def readIpeers():
    iperf_peers=[]
    with open('/home/lee/ryu2/ryu/app/experiments/iperf_peers.txt','r') as fw:
        result=fw.read()
        iperf_peers=list(result)
    return iperf_peers
print readIpeers()
