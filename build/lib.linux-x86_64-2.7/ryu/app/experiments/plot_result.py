# -*- coding: UTF-8 -*-
# Copyright (C) 2016 Huang MaChi at Chongqing University
# of Posts and Telecommunications, Chongqing, China.
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

import argparse
import re
from ryu.app.experiments.PureSDNPkt.setting import host_Capacity
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.font_manager import FontProperties
chinese_font = FontProperties(fname='/usr/share/matplotlib/mpl-data/fonts/ttf/simhei.ttf')


parser = argparse.ArgumentParser(description="Plot BFlows experiments' results")
parser.add_argument('--k', dest='k', type=int, default=4, choices=[4, 8], help="Switch fanout number")
parser.add_argument('--duration', dest='duration', type=int, default=60, help="Duration (sec) for each iperf traffic generation")
parser.add_argument('--dir', dest='out_dir', help="Directory to store outputs")
parser.add_argument('--fnum', dest='flows_num_per_host', type=float, default=1.0, help="Number of iperf flows per host")
args = parser.parse_args()


def read_file_1(file_name, delim=','):
    """
        Read the bwmng.txt file.
    """
    read_file = open(file_name, 'r')
    lines = read_file.xreadlines()
    lines_list = []
    for line in lines:
        line_list = line.strip().split(delim)
        lines_list.append(line_list)
    read_file.close()

    # Remove the last second's statistics, because they are mostly not intact.
    last_second = lines_list[-1][0]
    _lines_list = lines_list[:]
    for line in _lines_list:
        if line[0] == last_second:
            lines_list.remove(line)

    return lines_list

def read_file_2(file_name):
    """
        Read the first_packets.txt and successive_packets.txt file.
    """
    read_file = open(file_name, 'r')
    lines = read_file.xreadlines()
    lines_list = []
    for line in lines:
        if line.startswith('rtt') or line.endswith('ms\n'):
            lines_list.append(line)
    read_file.close()
    return lines_list

def calculate_average(value_list):
    average_value = sum(map(float, value_list)) / len(value_list)
    return average_value

def get_throughput(result,throughput, traffic, app, input_file):
    """
        csv output format:
        (Type rate)
        unix_timestamp;iface_name;bytes_out/s;bytes_in/s;bytes_total/s;bytes_in;bytes_out;packets_out/s;packets_in/s;packets_total/s;packets_in;packets_out;errors_out/s;errors_in/s;errors_in;errors_out\n
        (Type svg, sum, max)
        unix timestamp;iface_name;bytes_out;bytes_in;bytes_total;packets_out;packets_in;packets_total;errors_out;errors_in\n
        The bwm-ng mode used is 'rate'.

        throughput = {
                        'stag_0.5_0.3':
                        {
                            'realtime_bisection_bw': {'BFlows':{0:x, 1:x, ..}, 'ECMP':{0:x, 1:x, ..}, ...},
                            'realtime_throughput': {'BFlows':{0:x, 1:x, ..}, 'ECMP':{0:x, 1:x, ..}, ...},
                            'accumulated_throughput': {'BFlows':{0:x, 1:x, ..}, 'ECMP':{0:x, 1:x, ..}, ...},
                            'normalized_total_throughput': {'BFlows':x%, 'ECMP':x%, ...}
                        },
                        'stag_0.6_0.2':
                        {
                            'realtime_bisection_bw': {'BFlows':{0:x, 1:x, ..}, 'ECMP':{0:x, 1:x, ..}, ...},
                            'realtime_throughput': {'BFlows':{0:x, 1:x, ..}, 'ECMP':{0:x, 1:x, ..}, ...},
                            'accumulated_throughput': {'BFlows':{0:x, 1:x, ..}, 'ECMP':{0:x, 1:x, ..}, ...},
                            'normalized_total_throughput': {'BFlows':x%, 'ECMP':x%, ...}
                        },
                        ...
                    }
    """
    full_bisection_bw = 10.0 * (args.k ** 3 / 4)   # (unit: Mbit/s)
    lines_list = read_file_1(input_file)
    first_second = int(lines_list[0][0])
    column_bytes_out_rate = 2   # bytes_out/s
    column_bytes_out = 6   # bytes_out
    switch=None
    if app == 'NonBlocking':
        switch = '1001'
    elif app in ['BFlows', 'EFattree', 'ECMP', 'PureSDN', 'Hedera','Normalrouting','SRrouting','NMF','SRMF']:
        switch = '3[0-9][0-9][0-9]'
    else:
        pass
    switch = '3[0-9][0-9][0-9]'
    sw = re.compile(switch)
    if not throughput.has_key(traffic):
        throughput[traffic]={}
    if not throughput[traffic].has_key('realtime_bisection_bw'):
        throughput[traffic]['realtime_bisection_bw'] = {}
    if not throughput[traffic].has_key('realtime_throughput'):
        throughput[traffic]['realtime_throughput'] = {}
    if not throughput[traffic].has_key('accumulated_throughput'):
        throughput[traffic]['accumulated_throughput'] = {}
    if not throughput[traffic].has_key('normalized_total_throughput'):
        throughput[traffic]['normalized_total_throughput'] = {}
    if not result.has_key('accumulated_throughput'):
        result['accumulated_throughput']={}
    if not throughput[traffic]['realtime_bisection_bw'].has_key(app):
        throughput[traffic]['realtime_bisection_bw'][app] = {}
    if not throughput[traffic]['realtime_throughput'].has_key(app):
        throughput[traffic]['realtime_throughput'][app] = {}
    if not throughput[traffic]['accumulated_throughput'].has_key(app):
        throughput[traffic]['accumulated_throughput'][app] = {}
    if not throughput[traffic]['normalized_total_throughput'].has_key(app):
        throughput[traffic]['normalized_total_throughput'][app] = 0
    if not result['accumulated_throughput'].has_key(app):
        result['accumulated_throughput'][app]=0


    for i in xrange(args.duration + 1):
        if not throughput[traffic]['realtime_bisection_bw'][app].has_key(i):
            throughput[traffic]['realtime_bisection_bw'][app][i] = 0
        if not throughput[traffic]['realtime_throughput'][app].has_key(i):
            throughput[traffic]['realtime_throughput'][app][i] = 0
        if not throughput[traffic]['accumulated_throughput'][app].has_key(i):
            throughput[traffic]['accumulated_throughput'][app][i] = 0

    for row in lines_list:
        iface_name = row[1]
        if iface_name not in ['total', 'lo', 'eth0', 'enp0s3', 'enp0s8', 'docker0']:
            if switch == '3[0-9][0-9][0-9]':
                if sw.match(iface_name):
                    if int(iface_name[-1]) > args.k / 2:   # Choose down-going interfaces only.
                        if (int(row[0]) - first_second) <= args.duration:   # Take the good values only.
                            # throughput[traffic]['realtime_bisection_bw'][app][int(row[0]) - first_second] += float(row[column_bytes_out_rate]) * 8.0 / (1024*1024)   # Mbit/s
                            throughput[traffic]['realtime_throughput'][app][int(row[0]) - first_second] += float(row[column_bytes_out]) * 8.0 / (1024*1024)   # Mbit
            elif switch == '1001':   # Choose all the interfaces. (For NonBlocking Topo only)
                if sw.match(iface_name):
                    if (int(row[0]) - first_second) <= args.duration:
                        # throughput[traffic]['realtime_bisection_bw'][app][int(row[0]) - first_second] += float(row[column_bytes_out_rate]) * 8.0 / (1024*1024)   # Mbit/s
                        throughput[traffic]['realtime_throughput'][app][int(row[0]) - first_second] += float(row[column_bytes_out]) * 8.0 / (1024*1024)   # Mbit
            else:
                pass

    for i in xrange(args.duration + 1):
        for j in xrange(i+1):
            temp= throughput[traffic]['realtime_throughput'][app][j]
            throughput[traffic]['accumulated_throughput'][app][i] += temp  # Mbit
        if i==args.duration:
            result['accumulated_throughput'][app]+=throughput[traffic]['accumulated_throughput'][app][i]

    throughput[traffic]['normalized_total_throughput'][app] = throughput[traffic]['accumulated_throughput'][app][args.duration] / (full_bisection_bw * args.duration)   # percentage
    return throughput,result

def get_value_list_1(throughput, traffic, item, app):
    """
        Get the values from the "throughput" data structure.
    """
    value_list = []
    for i in xrange(args.duration + 1):
        value_list.append(throughput[traffic][item][app][i])
    return value_list

def get_average_bisection_bw(throughput, traffics, app):
    value_list = []
    complete_list = []
    step=len(traffics)
    for traffic in traffics:
        complete_list.append(throughput[traffic]['accumulated_throughput'][app][args.duration] / float(args.duration))
    # print complete_list
    # # print complete_list
    # for i in xrange(5):
    #     value_list.append(calculate_average(complete_list[(i * 10): (i * 10+ 10)]))
    return complete_list
def get_average_allround_bw(list,result):
    value=result.values()
    value_list=[]
    for i in list:
        value_list.append(result['accumulated_throughput'][i]/(args.duration*10))
    return value_list



def get_value_list_2(value_dict, traffics, item, app):
    """
        Get the values from the  data structure.
    """
    value_list = []
    for traffic in traffics:
        value_list.append(value_dict[traffic][item][app])
    return value_list
def plot_miceIndex_compare():
    round=[1,2,3,4,5,6,7,8,9,10]
    indexList=[0.6,0.7,0.8,0.9,1.0]
    default_path='/home/lee/ryu2/ryu/app/experiments/'

    for r in round:
        for index in indexList:
            bwmfile=default_path+'%s/%s/SRrouting/bwmng/'%(r,index)
            throughput={}
            get_throughput(throughput,r,index,bwmfile)



def run():
    result = {}
    throughput={}
    list1=[]
    list2=[]
    value_list={}
    path_segment=''
    path_segment2=''
    path='/home/lee/ryu2/ryu/app/experiments'
    check=input("which results you want to get?\n choice: 1 (miceIndex) , 2 (SR_vs_Normal) , 3(algorithm compare)")
    if str(check)=='1':
        list1=[1,2,3,4,5,6,7,8,9,10]
        list2=[0.6,0.7,0.8,0.9,1.0]

    if str(check)=='2':
        # list1=['10','20','30','40','50','60','70','80','90','100','110','120','130','140','150','160','170','180','190','200']
        list1 = ['10', '20', '30', '40', '50', '60', '70', '80','100']
        list2=['Normalrouting','SRrouting']
        path_segment='random/'
    if str(check)=='3':
        list1=['random','stag6_0.1_0.2','stag6_0.2_0.3','stag6_0.3_0.3','stag6_0.4_0.3','stag6_0.5_0.3','stag6_0.6_0.2','stag6_0.7_0.2','stag6_0.8_0.1']
        list2=['ECMP','Hedera','NMF','SRMF']

    for r in list1:
        for index in list2:
            if not value_list.has_key(index):
                value_list.setdefault(index,[])
            if(str(check)=='1'):
                file_path='%s/compare_miceIndex/%d/%.1f/SRrouting/bwmng/bwmng.txt'%(path,r,index)
            elif(str(check)=='2'):
                file_path='%s/results9/%s/random/%s/bwmng/bwmng.txt'%(path,r,index)
            elif(str(check)=='3'):
                file_path='%s/Results/4/%s/%s/bwmng/bwmng.txt'%(path,r,index)
            temp=get_throughput(result,throughput,r,index,file_path)
            throughput=temp[0]
            result=temp[1]
    if str(check)=='3':
        for k in list2:
            valuelist=get_average_bisection_bw(throughput,list1,k)
            value_list[k]=valuelist

    plot_results2(list1,list2,value_list)

def plot_results2(list,apps,value_list):
    full_bisection_bw = 250 * (args.k ** 3 / 4)  # (unit: Mbit/s)
    num_groups=len(list)
    count=1
    num_bar = len(apps)
    index = np.arange(num_groups) + 0.3
    bar_width = 0.15
    index = np.arange(num_groups) + 0.3
    colors=['g','b','r','k']
    # plt.bar(index, ECMP_value_list, bar_width, color='b', label='ECMP')
    for k in value_list:
        plt.bar(index + count * bar_width, value_list.get(k), bar_width, color=colors[count-1], label=k)
        count+=1
    # plt.bar(index + 2 * bar_width, compare_list2, bar_width, color='b', label='SRrouting')
    plt.xticks(index + num_bar * bar_width,list, fontsize='small')
    plt.ylabel(u'平均吞吐量\n(Mbps)', fontsize='xx-large', fontproperties=chinese_font)
    # plt.ylim(0, full_bisection_bw)
    # plt.yticks(np.linspace(0, full_bisection_bw, 11))
    plt.legend(loc='upper right', ncol=len(apps), fontsize='medium')
    plt.grid(axis='y')
    plt.tight_layout()
    plt.show()

def plot_results():
    """
        Plot the results:
        1. Plot realtime bisection bandwidth
        2. Plot average bisection bandwidth
        3. Plot accumulated throughput
        4. Plot normalized total throughput

        throughput = {
                        'stag_0.5_0.3':
                        {
                            'realtime_bisection_bw': {'BFlows':{0:x, 1:x, ..}, 'ECMP':{0:x, 1:x, ..}, ...},
                            'realtime_throughput': {'BFlows':{0:x, 1:x, ..}, 'ECMP':{0:x, 1:x, ..}, ...},
                            'accumulated_throughput': {'BFlows':{0:x, 1:x, ..}, 'ECMP':{0:x, 1:x, ..}, ...},
                            'normalized_total_throughput': {'BFlows':x%, 'ECMP':x%, ...}
                        },
                        'stag_0.6_0.2':
                        {
                            'realtime_bisection_bw': {'BFlows':{0:x, 1:x, ..}, 'ECMP':{0:x, 1:x, ..}, ...},
                            'realtime_throughput': {'BFlows':{0:x, 1:x, ..}, 'ECMP':{0:x, 1:x, ..}, ...},
                            'accumulated_throughput': {'BFlows':{0:x, 1:x, ..}, 'ECMP':{0:x, 1:x, ..}, ...},
                            'normalized_total_throughput': {'BFlows':x%, 'ECMP':x%, ...}
                        },
                        ...
                    }
    """
    full_bisection_bw = 250* (args.k ** 3 / 4)   # (unit: Mbit/s)
    utmost_throughput = full_bisection_bw * args.duration
    _traffics = "random1 random2 random3 random4 random5 random6 random7 random8 stag1_0.1_0.2 stag2_0.1_0.20.1_0.2 stag4_0.1_0.2 stag5_0.1_0.2 stag6_0.1_0.2 stag7_0.1_0.2 stag8_0.1_0.2 stag1_0.2_0.3 stag2_0.2_0.3 stag3_0.2_0.3 stag4_0.2_0.3 stag5_0.2_0.3 stag6_0.2_0.3 stag7_0.2_0.3 stag8_0.2_0.3 stag1_0.3_0.3 stag2_0.3_0.3 stag3_0.3_0.3 stag4_0.3_0.3 stag5_0.3_0.3 stag6_0.3_0.3 stag7_0.3_0.3 stag8_0.3_0.3 stag1_0.4_0.3 stag2_0.4_0.3 stag3_0.4_0.3 stag4_0.4_0.3 stag5_0.4_0.3 stag6_0.4_0.3 stag7_0.4_0.3 stag8_0.4_0.3 stag1_0.5_0.3 stag2_0.5_0.3 stag3_0.5_0.3 stag4_0.5_0.3 stag5_0.5_0.3 stag6_0.5_0.3 stag7_0.5_0.3 stag8_0.5_0.3 stag1_0.6_0.2 stag2_0.6_0.2 stag3_0.6_0.2 stag4_0.6_0.2 stag5_0.6_0.2 stag6_0.6_0.2 stag7_0.6_0.2 stag8_0.6_0.2 stag1_0.7_0.2 stag2_0.7_0.2 stag3_0.7_0.2 stag4_0.7_0.2 stag5_0.7_0.2 stag6_0.7_0.2 stag7_0.7_0.2 stag8_0.7_0.2 stag1_0.8_0.1 stag2_0.8_0.1 stag3_0.8_0.1 stag4_0.8_0.1 stag5_0.8_0.1 stag6_0.8_0.1 stag7_0.8_0.1 stag8_0.8_0.1"
    traffics = _traffics.split(' ')
    flow_num=[100,90,80,70,60,50,40,30,20,10,1]
    # traffics_brief = ['random', 'stag_0.1_0.2', 'stag_0.2_0.3', 'stag_0.3_0.3', 'stag_0.4_0.3', 'stag_0.5_0.3', 'stag_0.6_0.2', 'stag_0.7_0.2', 'stag_0.8_0.1']
    traffics_brief=['10','20','30','40','50','60','70','80','90','100','110','120']
    # traffics_brief=['20','40','60','80','100','120','140','160','180','200']
    # apps = ['ECMP', 'PureSDN', 'NonBlocking']
    apps=['Normalrouting','SRrouting']
    throughput = {}
    traffics='random'
    for n in traffics_brief:
        for app in apps:
            bwmng_file ='/home/lee/ryu2/ryu/app/experiments/results5/%s/%s/%s/bwmng/bwmng.txt' % (n,traffics,app)
            throughput = get_throughput(throughput, n ,app, bwmng_file)
    print throughput
    # 1. Plot average throughput.
    fig = plt.figure()
    fig.set_size_inches(12, 6)
    num_groups = len(traffics_brief)
    num_bar = len(apps)
    # ECMP_value_list = get_average_bisection_bw(throughput, traffics, 'ECMP')
    # PureSDN_value_list = get_average_bisection_bw(throughput, traffics, 'PureSDN')
    # NonBlocking_value_list = get_average_bisection_bw(throughput, traffics, 'NonBlocking')
    Normalrouting_value_list=get_average_bisection_bw(throughput, traffics_brief, 'Normalrouting')
    SRrouting_value_list=get_average_bisection_bw(throughput, traffics_brief, 'SRrouting')
    index = np.arange(num_groups) + 0.3
    bar_width = 0.3
    # plt.bar(index, ECMP_value_list, bar_width, color='b', label='ECMP')
    plt.bar(index + 1 * bar_width, Normalrouting_value_list, bar_width, color='g', label='Normalrouting')
    plt.bar(index + 2 * bar_width,SRrouting_value_list, bar_width, color='b', label='SRrouting')
    plt.xticks(index + num_bar  * bar_width, traffics_brief, fontsize='small')
    plt.ylabel(u'平均吞吐量\n(Mbps)', fontsize='xx-large', fontproperties=chinese_font)
    # plt.ylim(0, full_bisection_bw)
    # plt.yticks(np.linspace(0, full_bisection_bw, 11))
    plt.legend(loc='upper right', ncol=len(apps), fontsize='medium')
    plt.grid(axis='y')
    plt.tight_layout()
    plt.show()
    # plt.savefig(args.out_dir + '/%s-average_throughput.png' % args.flows_num_per_host)


if __name__ == '__main__':
    # plot_results()
    run()

