import random
import argparse
import os
import time
parser = argparse.ArgumentParser(description="BFlows experiments")
parser.add_argument('--k', dest='k', type=int, default=4, choices=[4, 8], help="Switch fanout number")
parser.add_argument('--traffic', dest='traffic', default="stag_0.2_0.3", help="Traffic pattern to simulate")
parser.add_argument('--fnum', dest='fnum', type=int, default=25, help="Number of iperf flows ")
args = parser.parse_args()

#random create fnum flows

def createPeers():
    iperf_peers=[]
    num=args.fnum
    for i in range(0,num):
        first=random.randint(1,16)
        second=random.randint(1,16)
        while(first==second):
            first = random.randint(1, 16)
            second = random.randint(1, 16)
        prefix='h0'
        first_str=None
        second_str=None
        if first<=9:
            first_str='0'+str(first)
        elif first>=10:
            first_str=str(first)
        if second <= 9:
            second_str = '0' + str(second)
        elif second>=10:
            second_str = str(second)
        peer=prefix+first_str+'-'+prefix+second_str
        iperf_peers.append(peer)
    write2file(iperf_peers)
def write2file(flows_peers):
    file_save = open('iperf_peers.txt', 'w+')
    file_save.write(str(flows_peers)[1:-1])
    file_save.close()

if __name__ == '__main__':
    createPeers()