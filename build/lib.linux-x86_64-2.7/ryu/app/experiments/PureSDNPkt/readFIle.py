def readIpeers():
    peers=[]
    i=0
    result=''
    with open('/home/lee/ryu2/ryu/app/experiments/iperf_peers.txt','r') as fw:
        result=fw.read().split(',')
    print result
    for r in result:
        r=r.split('-')
        if i==0:
            temp=(r[0][1:],r[1][:-1])
        else:
            temp = (r[0][2:], r[1][:-1])
        peers.append(temp)
        i+=1
    return peers