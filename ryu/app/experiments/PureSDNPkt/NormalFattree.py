# Copyright (C) 2016 Huang MaChi at Chongqing University
# of Posts and Telecommunications, China.
# Copyright (C) 2016 Li Cheng at Beijing University of Posts
# and Telecommunications. www.muzixing.com
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.
import traffic_generation as t
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
from ryu.app.experiments.readfile import readIpeers
from subprocess import Popen
from multiprocessing import Process
parentdir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, parentdir)
import ryu.app.experiments.iperf_peers_fsize as peers1
import random



parser = argparse.ArgumentParser(description="Parameters importation")
parser.add_argument('--k', dest='k', type=int, default=4, choices=[4, 8], help="Switch fanout number")
parser.add_argument('--duration', dest='duration', type=int, default=60, help="Duration (sec) for each iperf traffic generation")
parser.add_argument('--dir', dest='output_dir', help="Directory to store outputs")
parser.add_argument('--cpu', dest='cpu', type=float, default=1.0, help='Total CPU to allocate to hosts')
parser.add_argument('--fnum', dest='flow_num', type=int, default=10, help='number of traffic')
parser.add_argument('--miceIndex', dest='miceIndex', type=float, default=0.7, help='miceIndex')
args = parser.parse_args()


class Fattree(Topo):
    """
        Class of Fattree Topology.
    """
    CoreSwitchList = []
    AggSwitchList = []
    EdgeSwitchList = []
    HostList = []

    def __init__(self, k, density):
        self.pod = k
        self.density = density
        self.iCoreLayerSwitch = (k/2)**2
        self.iAggLayerSwitch = k*k/2
        self.iEdgeLayerSwitch = k*k/2
        self.iHost = self.iEdgeLayerSwitch * density

        # Init Topo
        Topo.__init__(self)

    def createNodes(self):
        self.createCoreLayerSwitch(self.iCoreLayerSwitch)
        self.createAggLayerSwitch(self.iAggLayerSwitch)
        self.createEdgeLayerSwitch(self.iEdgeLayerSwitch)
        self.createHost(self.iHost)

    # Create Switch and Host
    def _addSwitch(self, number, level, switch_list):
        """
            Create switches.
        """
        for i in xrange(1, number+1):
            PREFIX = str(level) + "00"
            if i >= 10:
                PREFIX = str(level) + "0"
            switch_list.append(self.addSwitch(PREFIX + str(i)))

    def createCoreLayerSwitch(self, NUMBER):
        self._addSwitch(NUMBER, 1, self.CoreSwitchList)

    def createAggLayerSwitch(self, NUMBER):
        self._addSwitch(NUMBER, 2, self.AggSwitchList)

    def createEdgeLayerSwitch(self, NUMBER):
        self._addSwitch(NUMBER, 3, self.EdgeSwitchList)

    def createHost(self, NUMBER):
        """
            Create hosts.
        """
        for i in xrange(1, NUMBER+1):
            if i >= 100:
                PREFIX = "h"
            elif i >= 10:
                PREFIX = "h0"
            else:
                PREFIX = "h00"
            self.HostList.append(self.addHost(PREFIX + str(i), cpu=1.0/NUMBER))

    def createLinks(self, bw_c2a=1000, bw_a2e=500, bw_e2h=250):
        """
            Add network links.
        """
        # Core to Agg

        end = self.pod/2
        for x in xrange(0, self.iAggLayerSwitch, end):
            for i in xrange(0, end):
                for j in xrange(0, end):
                    self.addLink(
                        self.CoreSwitchList[i*end+j],
                        self.AggSwitchList[x+i],
                        bw=bw_c2a, max_queue_size=1000)   # use_htb=False

        # Agg to Edge
        for x in xrange(0, self.iAggLayerSwitch, end):
            for i in xrange(0, end):
                for j in xrange(0, end):
                    self.addLink(
                        self.AggSwitchList[x+i], self.EdgeSwitchList[x+j],
                        bw=bw_a2e, max_queue_size=1000)   # use_htb=False

        # Edge to Host
        for x in xrange(0, self.iEdgeLayerSwitch):
            for i in xrange(0, self.density):
                self.addLink(
                    self.EdgeSwitchList[x],
                    self.HostList[self.density * x + i],
                    bw=bw_e2h, max_queue_size=1000)   # use_htb=False

    def set_ovs_protocol_13(self,):
        """
            Set the OpenFlow version for switches.
        """
        self._set_ovs_protocol_13(self.CoreSwitchList)
        self._set_ovs_protocol_13(self.AggSwitchList)
        self._set_ovs_protocol_13(self.EdgeSwitchList)

    def _set_ovs_protocol_13(self, sw_list):
        for sw in sw_list:
            cmd = "sudo ovs-vsctl set bridge %s protocols=OpenFlow13" % sw
            os.system(cmd)


def set_host_ip(net, topo):
    hostlist = []
    for k in xrange(len(topo.HostList)):
        hostlist.append(net.get(topo.HostList[k]))
    i = 1
    j = 1
    for host in hostlist:
        host.setIP("10.%d.0.%d" % (i, j))
        j += 1
        if j == topo.density+1:
            j = 1
            i += 1

def create_subnetList(topo, num):
    """
        Create the subnet list of the certain Pod.
    """
    subnetList = []
    remainder = num % (topo.pod/2)
    if topo.pod == 4:
        if remainder == 0:
            subnetList = [num-1, num]
        elif remainder == 1:
            subnetList = [num, num+1]
        else:
            pass
    elif topo.pod == 8:
        if remainder == 0:
            subnetList = [num-3, num-2, num-1, num]
        elif remainder == 1:
            subnetList = [num, num+1, num+2, num+3]
        elif remainder == 2:
            subnetList = [num-1, num, num+1, num+2]
        elif remainder == 3:
            subnetList = [num-2, num-1, num, num+1]
        else:
            pass
    else:
        pass
    return subnetList

def install_proactive(net, topo):
    """
        Install proactive flow entries for switches.
    """
    # Edge Switch
    for sw in topo.EdgeSwitchList:
        num = int(sw[-2:])

        # Downstream.
        for i in xrange(1, topo.density + 1):
            cmd = "ovs-ofctl add-flow %s -O OpenFlow13 \
            				'table=0,idle_timeout=0,hard_timeout=0,priority=40,arp, \
            				nw_dst=10.%d.0.%d,actions=output:%d'" % (sw, num, i, topo.pod / 2 + i)
            os.system(cmd)
            cmd = "ovs-ofctl add-flow %s -O OpenFlow13 \
                            'table=0,idle_timeout=0,hard_timeout=0,priority=10,ip, \
                            nw_dst=10.%d.0.%d,actions=output:%d'" % (sw, num, i, topo.pod / 2 + i)
            os.system(cmd)
        # Upstream
        if topo.pod == 4:
            cmd = "ovs-ofctl add-group %s -O OpenFlow13 \
                'group_id=1,type=select,bucket=output:1,bucket=output:2'" % sw
        elif topo.pod == 8:
            cmd = "ovs-ofctl add-group %s -O OpenFlow13 \
                'group_id=1,type=select,bucket=output:1,bucket=output:2,\
                bucket=output:3,bucket=output:4'" % sw
        else:
            pass
        os.system(cmd)
        cmd = "ovs-ofctl add-flow %s -O OpenFlow13 \
        		'table=0,priority=10,arp,actions=group:1'" % sw
        os.system(cmd)
        cmd = "ovs-ofctl add-flow %s -O OpenFlow13 \
                'table=0,priority=10,ip,nw_proto=1,actions=group:1'" % sw
        os.system(cmd)

    # Aggregate Switch
    for sw in topo.AggSwitchList:
        num = int(sw[-2:])
        subnetList = create_subnetList(topo, num)
        k = 1
        for i in subnetList:
            cmd = "ovs-ofctl add-flow %s -O OpenFlow13 \
            				'table=0,idle_timeout=0,hard_timeout=0,priority=40,arp, \
            				nw_dst=10.%d.0.0/16, actions=output:%d'" % (sw, i, topo.pod / 2 + k)
            os.system(cmd)
            # cmd = "ovs-ofctl add-flow %s -O OpenFlow13 \
            #         'table=0,idle_timeout=0,hard_timeout=0,priority=10,mpls, \
            #         mpls_label=%d, actions=pop_mpls:0x0800,output:%d'" % (sw, topo.pod / 2 + k, topo.pod / 2 + k)
            # os.system(cmd)
            # cmd = "ovs-ofctl add-flow %s -O OpenFlow13 \
            #         'table=0,idle_timeout=0,hard_timeout=0,priority=10,mpls, \
            #         mpls_label=%d,actions=pop_mpls:0x8847,output:%d'" % (sw, k, k)
            # os.system(cmd)
            cmd = "ovs-ofctl add-flow %s -O OpenFlow13 \
                            'table=0,idle_timeout=0,hard_timeout=0,priority=40,ip,nw_proto=1 \
                            nw_dst=10.%d.0.0/16, actions=output:%d'" % (sw, i, topo.pod / 2 + k)
            os.system(cmd)
            k += 1
        # Upstream
        if topo.pod == 4:
            cmd = "ovs-ofctl add-group %s -O OpenFlow13 \
                'group_id=1,type=select,bucket=output:1,bucket=output:2'" % sw
        elif topo.pod == 8:
            cmd = "ovs-ofctl add-group %s -O OpenFlow13 \
                'group_id=1,type=select,bucket=output:1,bucket=output:2,\
                bucket=output:3,bucket=output:4'" % sw
        else:
            pass
        os.system(cmd)
        cmd = "ovs-ofctl add-flow %s -O OpenFlow13 \
        		'table=0,priority=10,arp,actions=group:1'" % sw
        os.system(cmd)
        cmd = "ovs-ofctl add-flow %s -O OpenFlow13 \
                'table=0,priority=10,ip,nw_proto=1 actions=group:1'" % sw
        os.system(cmd)

    # Core Switch
    for sw in topo.CoreSwitchList:
        j = 1
        k = 1
        for i in xrange(1, len(topo.EdgeSwitchList)+1):
            # cmd = "ovs-ofctl add-flow %s -O OpenFlow13 \
            #        'table=0,idle_timeout=0,hard_timeout=0,priority=10,mpls, \
            #        mpls_label=%d,actions=pop_mpls:0x8847,output:%d'" % (sw, j, j)
            # os.system(cmd)
            cmd = "ovs-ofctl add-flow %s -O OpenFlow13 \
            				'table=0,idle_timeout=0,hard_timeout=0,priority=10,arp, \
            				nw_dst=10.%d.0.0/16, actions=output:%d'" % (sw, i, j)
            os.system(cmd)
            cmd = "ovs-ofctl add-flow %s -O OpenFlow13 \
                            'table=0,idle_timeout=0,hard_timeout=0,priority=10,ip,nw_proto=1 \
                            nw_dst=10.%d.0.0/16, actions=output:%d'" % (sw, i, j)
            os.system(cmd)
            k += 1
            if k == topo.pod/2 + 1:
                j += 1
                k = 1
def iperfTest(net, topo):
    """
        Start iperf test.
    """
    h001, h015, h016 = net.get(
        topo.HostList[0], topo.HostList[14], topo.HostList[15])
    # iperf Server
    h001.popen('iperf -s -u -i 1 > iperf_server_differentPod_result', shell=True)
    # iperf Server
    h015.popen('iperf -s -u -i 1 > iperf_server_samePod_result', shell=True)
    # iperf Client
    h016.cmdPrint('iperf -c ' + h001.IP() + ' -u -t 10 -i 1 -b 10m')
    h016.cmdPrint('iperf -c ' + h015.IP() + ' -u -t 10 -i 1 -b 10m')

def monitor_devs_ng(fname="./txrate.txt", interval_sec=0.1):
    """
        Use bwm-ng tool to collect interface transmit rate statistics.
        bwm-ng Mode: rate;
        interval time: 1s.
    """
    cmd = "sleep 1; bwm-ng -t %s -o csv -u bits -T rate -C ',' > %s" %  (interval_sec * 1000, fname)
    Popen(cmd, shell=True).wait()
def traffic_generation1(net,flows_peers,ping_peers):
    """
        Generate traffics and test the performance of the network.
    """
    # 1.Start iperf. (Elephant flows)
    # Start the servers.

    serversList = set([peer[1] for peer in flows_peers])
    for server in serversList:
        # filename = server[1:]
        server = net.get(server)
        # server.cmd("iperf -s > %s/%s &" % (args.output_dir, 'server'+filename+'.txt'))
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
        # client.cmd("iperf -c %s -t %d -M 1250 > /dev/null &" % (server.IP(), 2500) ) # Its statistics is useless, just throw away. 1990 just means a great
    # client.cmd("iperf -c %s -t %d -M 1250 > /dev/null &" % (server.IP(), random.randint(10,60)))
    # time.sleep(1)
    # monitor = Process(target = monitor_devs_ng, args = ('%s/bwmng.txt' % args.output_dir, 1.0))
    # Wait for the traffic to become stable.
    # 3. The experiment is going on.
    time.sleep(args.duration + 5)
    monitor.terminate()
def traffic_generation(net,flows_peers,monitor1,monitor):
    """
        Generate traffics and test the performance of the network.
    """
    # 1.Start iperf. (Elephant flows)
    # Start the servers.
    serversList = set([peer[1] for peer in flows_peers])

    for server in serversList:
        # filename = server[1:]
        server = net.get(server)
        # server.cmd("iperf -s > /%s/%s &" % (args.output_dir, 'server'+str(count)+'.txt'))
        server.cmd("iperf -s >> /dev/null &")  # Its statistics is useless, just throw away.

    time.sleep(3)
    # Start the clients.
    monitor = Process(target=monitor_devs_ng, args=('%s/bwmng.txt' % args.output_dir, 1.0))
    monitor1.start()
    count=0
    for src, dest in flows_peers:
        count+=1
        time.sleep(1)
        server = net.get(dest)
        client = net.get(src)
        Thread(target=iperfC,args=(client,server.IP(),3000)).start()
        # client.cmd("iperf -c %s -t %d -M 1250 > /dev/null &" % (server.IP(), 60))  # Its statistics is useless, just throw away. 1990 just means a great
    # client.cmd("iperf -c %s -t %d -M 1250 > /dev/null &" % (server.IP(), random.randint(10,60)))
    # time.sleep(1)
    # monitor = Process(target = monitor_devs_ng, args = ('%s/bwmng.txt' % args.output_dir, 1.0))
    # Wait for the traffic to become stable.
    # 3. The experiment is going on.
    time.sleep(60)
    monitor.start()
    time.sleep(args.duration + 5)
    monitor.terminate()
    monitor1.terminate()
def iperfC(client,ip,time):
    client.cmd("iperf -c %s -t %d -M 1250 > /dev/null &" % (ip, time))
def pingTest(net,flows_peers):
    for src,dst in flows_peers:
        server=net.get(dst)
        client=net.get(src)
        # client.cmd('ping %s -c %d > %s/pingTest/ping_%s_%s_%d.txt &'%(server.IP(),60,args.output_dir,src,dst,count))
        client.cmd('ping -c %d -i 0.1 -n -q %s>> %s/%s &' % (args.duration*10,server.IP(), args.output_dir,'successive_packets.txt'))

def removeOldFiles():
    cmd="sudo rm -f NormalroutingResult/*"
    os.system(cmd)
    cmd="sudo rm -f SRroutingResult/*"
    os.system(cmd)
    cmd="sudo rm -f resultSolve/count_text.txt"
    os.system(cmd)
def createTopo(pod, density, ip="192.168.16.138", port=6653, bw_c2a=100, bw_a2e=100, bw_e2h=100):
    """
        Create network topology and run the Mininet.
    """
    topo = Fattree(pod, density)
    topo.createNodes()
    topo.createLinks(bw_c2a=bw_c2a, bw_a2e=bw_a2e, bw_e2h=bw_e2h)
    # Start Mininet.
    CONTROLLER_IP = ip
    CONTROLLER_PORT = port
    net = Mininet(topo=topo, link=TCLink, controller=None, autoSetMacs=True)
    net.addController(
        'controller', controller=RemoteController,
        ip=CONTROLLER_IP, port=CONTROLLER_PORT)
    net.start()
    # Set OVS's protocol as OF13.
    topo.set_ovs_protocol_13()
    # Set hosts IP addresses.
    set_host_ip(net, topo)
    # Install proactive flow entries
    install_proactive(net, topo)
    # 2. Start the controller.
    k_paths = args.k ** 2 / 4
    fanout = args.k
    # Controller_Ryu = Popen("ryu-manager --observe-links Normalrouting.py --k_paths=%d --weight=hop --fanout=%d --dir=%s --miceIndex=%f" %(k_paths, fanout,args.output_dir[2:],args.miceIndex), shell=True, preexec_fn=os.setsid)
    Controller_Ryu = Popen("ryu-manager --observe-links Rerouting.py --k_paths=%d --weight=hop --fanout=%d" % (k_paths, fanout),shell=True, preexec_fn=os.setsid)
    time.sleep(45)
    # t.traffic_generation(net, iperf_peers, ping_peers)
    # t.first_icmp_delay(net,peers1.iperf_peers)
    CLI(net)
    closeable(net,Controller_Ryu)
def closeable(net,Controller_Ryu):
    os.system('killall ping')
    os.system('killall iperf')
    # CLI(net)
    os.killpg(Controller_Ryu.pid, signal.SIGKILL)
    net.stop()
if __name__ == '__main__':
    setLogLevel('info')
    if os.getuid() != 0:
        logging.debug("You are NOT root")
    elif os.getuid() == 0:
         # removeOldFiles()
        # logging.debug("remove old result files")
        # time.sleep(3)
        createTopo(4, 2)
        # createTopo(8, 4)
