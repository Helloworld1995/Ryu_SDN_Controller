import time
from threading import Thread
from mininet.net import Mininet
from mininet.node import Controller, RemoteController
from mininet.cli import CLI
from mininet.log import setLogLevel
from mininet.link import Link, Intf, TCLink
from mininet.topo import Topo
import argparse
import logging
import os
import sys
import signal
# from ryu.app.experiments.readfile import readIpeers
from subprocess import Popen
from multiprocessing import Process
parentdir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, parentdir)
import random

parser = argparse.ArgumentParser(description="Parameters importation")
parser.add_argument('--k', dest='k', type=int, default=4, choices=[4, 8], help="Switch fanout number")
parser.add_argument('--duration', dest='duration', type=int, default=60, help="Duration (sec) for each iperf traffic generation")
parser.add_argument('--dir', dest='output_dir', help="Directory to store outputs")
parser.add_argument('--cpu', dest='cpu', type=float, default=1.0, help='Total CPU to allocate to hosts')
parser.add_argument('--fnum', dest='flow_num', type=int, default=10, help='number of traffic')
parser.add_argument('--miceIndex', dest='miceIndex', type=float, default=0.7, help='miceIndex')
args = parser.parse_args()
import ryu.app.experiments.iperf_peers_fsize as peers


def traffic_generation(net,flows_peers,ping_peers):
    """
        Generate traffics and test the performance of the network.
    """
    # 1.Start iperf. (Elephant flows)
    # Start the servers.

    serversList = set([peer[1] for peer in flows_peers])
    for server in serversList:
        server = net.get(server)
        server.cmd("iperf -s > /dev/null &")  # Its statistics is useless, just throw away.
    time.sleep(3)
    # Start the clients.
    for src, dest in flows_peers:
        time.sleep(1)
        server = net.get(dest)
        client = net.get(src)
        client.cmd("iperf -c %s -t %d -M 1250 > /dev/null &" % (server.IP(), 3000))
    pingTest(net,ping_peers)
    time.sleep(5)
    monitor = Process(target=monitor_devs_ng, args=('%s/bwmng.txt' % args.output_dir, 1.0))
    monitor.start()
    time.sleep(args.duration + 5)
    monitor.terminate()
def time_comsume(net,flows_peers):
    """
        Generate traffics and test the performance of the network.
    """
    # 1.Start iperf. (Elephant flows)
    # Start the servers.
    serversList = set([peer[1] for peer in flows_peers])
    for server in serversList:
        server = net.get(server)
        server.cmd("iperf -s > /dev/null &")  # Its statistics is useless, just throw away.

    time.sleep(3)
    # Start the clients.
    for src, dest , fsize in flows_peers:
        time.sleep(1)
        server = net.get(dest)
        client = net.get(src)
        client.cmd("iperf -c %s -t %d -n %s -M 1250 > /dev/null &" % (server.IP(), 3000,fsize))

    # time.sleep(5)
    # time.sleep(args.duration + 5)

def monitor_devs_ng(fname="./txrate.txt", interval_sec=0.1):
    """
        Use bwm-ng tool to collect interface transmit rate statistics.
        bwm-ng Mode: rate;
        interval time: 1s.
    """
    cmd = "sleep 1; bwm-ng -t %s -o csv -u bits -T rate -C ',' > %s" % (interval_sec * 1000, fname)
    Popen(cmd, shell=True).wait()
def first_icmp_delay(net,flows_peers):
    count=0
    random.shuffle(flows_peers)
    for src,dst,demand in flows_peers:
        if count==1:
            break
        server=net.get(dst)
        client=net.get(src)
        # client.cmd('ping %s -c %d > %s/pingTest/ping_%s_%s_%d.txt &'%(server.IP(),60,args.output_dir,src,dst,count))
        client.cmd('ping -c 2 -i 1 -n -q %s>> %s &' % (server.IP(), './pingtest/first_packet_ecmp1.txt'))
        count+=1
def pingTest(net,flows_peers):
    random.shuffle(flows_peers)
    for src,dst in flows_peers:
        server=net.get(dst)
        client=net.get(src)
        # client.cmd('ping %s -c %d > %s/pingTest/ping_%s_%s_%d.txt &'%(server.IP(),60,args.output_dir,src,dst,count))
        client.cmd('ping -c %d -i 0.1 -n -q %s>> %s/%s &' % (args.duration*10,server.IP(), args.output_dir,'successive_packets.txt'))





def test(flows_peers):
    """
        Generate traffics and test the performance of the network.
    """
    # 1.Start iperf. (Elephant flows)
    # Start the servers.
    serversList = set([peer[1] for peer in flows_peers])
    print serversList

    # Start the clients.
    for src, dest , fsize in flows_peers:
        print src+dest+fsize
    # pingTest(net,ping_peers)


# test(peers.iperf_peers)