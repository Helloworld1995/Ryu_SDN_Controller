import iperf_peers
def readIpeers(path):
    peers=[]
    i=0
    with open(path,'r') as fw:
        result=fw.read().split(',')
    if path[-8:-4]=='loss':
        peers=read_loss(peers,result)
    else:
        for r in result:
            r=r.split('-')
            if i==0:
                temp=(r[0][1:],r[1][:-1])
            else:
                temp = (r[0][2:], r[1][:-1])
            peers.append(temp)
            i+=1
    return peers
def read_loss(peers,result):
     for r in result:
         peers.append(r[0:-1])
     return peers

