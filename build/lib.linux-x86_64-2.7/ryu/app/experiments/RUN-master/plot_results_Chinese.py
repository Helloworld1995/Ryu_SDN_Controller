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
import os
import re
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.font_manager import FontProperties
chinese_font = FontProperties(fname='/usr/share/matplotlib/mpl-data/fonts/ttf/simhei.ttf')


parser = argparse.ArgumentParser(description="Plot EFattree experiments' results")
parser.add_argument('--k', dest='k', type=int, default=4, choices=[4, 8], help="Switch fanout number")
parser.add_argument('--duration', dest='duration', type=int, default=60, help="Duration (sec) for each iperf traffic generation")
parser.add_argument('--dir', dest='out_dir', help="Directory to store outputs")
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


def get_value_list_2(value_dict, traffics, item, app):
    """
        Get the values from the "throughput", "first_packet_delay" and "average_delay" data structure.
    """
    value_list = []
    complete_list = []
    for traffic in traffics:
        complete_list.append(value_dict[traffic][item][app])
    for i in xrange(len(traffics)):
        value_list.append(calculate_average(complete_list[(i * 1): (i * 1 + 1)]))
    return value_list

def get_value_list_3(value_dict, traffics, items, app):
    """
        Get the values from the "first_packet_delay" and "average_delay" data structure.
    """
    value_list = []
    send_list = []
    receive_list = []
    for traffic in traffics:
        send_list.append(value_dict[traffic][items[0]][app])
        receive_list.append(value_dict[traffic][items[1]][app])
    for i in xrange(len(traffics)):
        value_list.append((sum(send_list[(i * 1): (i * 1 + 1)]) - sum(receive_list[(i * 1): (i * 1 + 1)])) / float(sum(send_list[(i * 1): (i * 1 + 1)])))

    return value_list

def get_delay(delay, traffic, keys, app, input_file):

    if not delay.has_key(traffic):
        delay[traffic] = {}

    for i in range(len(keys)):
        if not delay[traffic].has_key(keys[i]):
            delay[traffic][keys[i]] = {}

    for i in range(len(keys)):
        if not delay[traffic][keys[i]].has_key(app):
            delay[traffic][keys[i]][app] = 0

    lines_list = read_file_2(input_file)
    average_delay_list = []
    if len(keys) == 3:
        for line in lines_list:
            if line.startswith('rtt'):
                average_delay_list.append(float(line.split('/')[4]))
            else:
                delay[traffic]['first_packet_total_send'][app] += int(line.split(' ')[0])
                delay[traffic]['first_packet_total_receive'][app] += int(line.split(' ')[3])
        # print "traffic:", traffic
        # print "app:", app
        delay[traffic][keys[0]][app] = calculate_average(average_delay_list)
    elif len(keys) == 4:
        mean_deviation_list = []
        for line in lines_list:
            if line.startswith('rtt'):
                average_delay_list.append(float(line.split('/')[4]))
                mean_deviation_list.append(float((line.split('/')[6]).split(' ')[0]))
            else:
                delay[traffic]['total_send'][app] += int(line.split(' ')[0])
                delay[traffic]['total_receive'][app] += int(line.split(' ')[3])
        delay[traffic][keys[0]][app] = calculate_average(average_delay_list)
        delay[traffic][keys[1]][app] = calculate_average(mean_deviation_list)

    return delay
def write2file(dict,app,result):
    fileDir = '/home/lee/ryu2/ryu/app/experiments/RESULTS/%s'%app
    if not os.path.exists(fileDir):
        os.makedirs(fileDir)
    filename = fileDir + "/%s.txt"%result
    file_save = open(filename, 'a+')
    file_save.write(str(dict)[1:-1])
    file_save.write("\r\n")
    file_save.close()
def plot_results():


    #_traffics="random1 stag1_0.1_0.2 stag1_0.2_0.3 stag1_0.3_0.3 stag1_0.4_0.3 stag1_0.5_0.3 stag1_0.6_0.2 stag1_0.7_0.2 stag1_0.8_0.1"
    _traffics = "random stag1_0.1_0.2 stag1_0.2_0.3 stag1_0.4_0.3 stag1_0.5_0.3 stag1_0.6_0.2 stag1_0.7_0.2 stag1_0.8_0.1"
    # _traffics = "stag6_0.7_0.2"
    #_traffics="stag1_0.1_0.2 stag2_0.1_0.2 stag3_0.1_0.2 stag4_0.1_0.2 stag5_0.1_0.2 stag1_0.2_0.3 stag2_0.2_0.3 stag3_0.2_0.3 stag4_0.2_0.3 stag5_0.2_0.3 stag1_0.3_0.3 stag2_0.3_0.3 stag3_0.3_0.3 stag4_0.3_0.3 stag5_0.3_0.3 stag1_0.4_0.3 stag2_0.4_0.3 stag3_0.4_0.3 stag4_0.4_0.3 stag5_0.4_0.3"
    #_traffics = "stag1_0.5_0.3 stag2_0.5_0.3 stag3_0.5_0.3 stag4_0.5_0.3 stag5_0.5_0.3 stag6_0.5_0.3 stag7_0.5_0.3 stag8_0.5_0.3 stag9_0.5_0.3 stag10_0.5_0.3 stag11_0.5_0.3 stag12_0.5_0.3 stag13_0.5_0.3 stag14_0.5_0.3 stag15_0.5_0.3 stag16_0.5_0.3 stag17_0.5_0.3 stag18_0.5_0.3 stag19_0.5_0.3 stag20_0.5_0.3 stag1_0.6_0.2 stag2_0.6_0.2 stag3_0.6_0.2 stag4_0.6_0.2 stag5_0.6_0.2 stag6_0.6_0.2 stag7_0.6_0.2 stag8_0.6_0.2 stag9_0.6_0.2 stag10_0.6_0.2 stag11_0.6_0.2 stag12_0.6_0.2 stag13_0.6_0.2 stag14_0.6_0.2 stag15_0.6_0.2 stag16_0.6_0.2 stag17_0.6_0.2 stag18_0.6_0.2 stag19_0.6_0.2 stag20_0.6_0.2 stag1_0.7_0.2 stag2_0.7_0.2 stag3_0.7_0.2 stag4_0.7_0.2 stag5_0.7_0.2 stag6_0.7_0.2 stag7_0.7_0.2 stag8_0.7_0.2 stag9_0.7_0.2 stag10_0.7_0.2 stag11_0.7_0.2 stag12_0.7_0.2 stag13_0.7_0.2 stag14_0.7_0.2 stag15_0.7_0.2 stag16_0.7_0.2 stag17_0.7_0.2 stag18_0.7_0.2 stag19_0.7_0.2 stag20_0.7_0.2 stag1_0.8_0.1 stag2_0.8_0.1 stag3_0.8_0.1 stag4_0.8_0.1 stag5_0.8_0.1 stag6_0.8_0.1 stag7_0.8_0.1 stag8_0.8_0.1 stag9_0.8_0.1 stag10_0.8_0.1 stag11_0.8_0.1 stag12_0.8_0.1 stag13_0.8_0.1 stag14_0.8_0.1 stag15_0.8_0.1 stag16_0.8_0.1 stag17_0.8_0.1 stag18_0.8_0.1 stag19_0.8_0.1 stag20_0.8_0.1"
    traffics = _traffics.split(' ')
    #traffics_brief = ['random','stag_0.1_0.2', 'stag_0.2_0.3', 'stag_0.3_0.3', 'stag_0.4_0.3', 'stag_0.5_0.3', 'stag_0.6_0.2', 'stag_0.7_0.2', 'stag_0.8_0.1']
    # traffics_brief = ['random','stag_0.2_0.3','stag_0.4_0.3', 'stag_0.6_0.2', 'stag_0.8_0.1']
    apps = ['ECMP', 'Hedera','NMF','SRMF']
    throughput = {}
    first_packet_delay = {}
    average_delay = {}

    for traffic in traffics:
        for app in apps:
            bwmng_file = args.out_dir + '/%s/%s/bwmng.txt' % (traffic, app)

            keys2 = ['average_round_trip_delay', 'mean_deviation_of_round_trip_delay', 'total_send', 'total_receive']
            first_packet_file = args.out_dir + '/%s/%s/first_packets.txt' % (traffic, app)

            successive_packets_file = args.out_dir + '/%s/%s/successive_packets.txt' % (traffic, app)
            average_delay = get_delay(average_delay, traffic, keys2, app, successive_packets_file)


    # 5. Plot average packet round-trip delay of delay-sensitive traffic.
    item = 'average_round_trip_delay'
    fig = plt.figure()
    fig.set_size_inches(15, 5)
    num_groups = len(traffics)
    num_bar = len(apps)
    EFattree_value_list = get_value_list_2(average_delay, traffics, item, 'NMF')
    PureSDN_value_list = get_value_list_2(average_delay, traffics, item, 'SRMF')
    Hedera_value_list = get_value_list_2(average_delay, traffics, item, 'Hedera')
    ECMP_value_list = get_value_list_2(average_delay, traffics, item, 'ECMP')
    write2file(EFattree_value_list,'NMF','delay')
    write2file(PureSDN_value_list, 'SRMF', 'delay')
    write2file(Hedera_value_list, 'Hedera', 'delay')
    write2file(ECMP_value_list, 'ECMP', 'delay')
    index = np.arange(num_groups) + 0.15
    bar_width = 0.2
    plt.bar(index, EFattree_value_list, bar_width, color='r', label='NMF')
    plt.bar(index + 1 * bar_width, PureSDN_value_list, bar_width, color='g', label='SRMF')
    plt.bar(index + 2 * bar_width, Hedera_value_list, bar_width, color='y', label='Hedera')
    plt.bar(index + 3 * bar_width, ECMP_value_list, bar_width, color='b', label='ECMP')

    for x,y in zip(index,EFattree_value_list):
        plt.text(x+0.1, y+0.05, '%.2f' % y, ha='center', va= 'bottom',fontsize=10)
    for x,y in zip(index + 1 * bar_width,PureSDN_value_list):
        plt.text(x+0.1, y+0.05, '%.2f' % y, ha='center', va= 'bottom',fontsize=10)
    for x,y in zip(index + 2 * bar_width,Hedera_value_list):
        plt.text(x+0.1, y+0.05, '%.2f' % y, ha='center', va= 'bottom',fontsize=10)
    for x,y in zip(index + 3 * bar_width,ECMP_value_list):
        plt.text(x+0.1, y+0.05, '%.2f' % y, ha='center', va= 'bottom',fontsize=10)
    plt.xticks(index + num_bar / 2.0 * bar_width,traffics, fontsize='small')
    plt.ylabel(u'小流平均往返时延\n(ms)', fontsize='xx-large', fontproperties=chinese_font)
    plt.yticks(fontsize='large')
    plt.legend(loc='upper right', ncol=len(apps), fontsize='small')
    plt.grid(axis='y')
    plt.tight_layout()
    plt.savefig(args.out_dir + '/5.average_round_trip_delay.png')


    

    
    # 6. Plot packet loss rate of delay-sensitive traffic.
    items = ['total_send', 'total_receive']
    fig = plt.figure()
    fig.set_size_inches(15, 5)
    num_groups = len(traffics)
    num_bar = len(apps)
    EFattree_value_list = get_value_list_3(average_delay, traffics, items, 'NMF')
    PureSDN_value_list = get_value_list_3(average_delay, traffics, items, 'SRMF')
    Hedera_value_list = get_value_list_3(average_delay, traffics, items, 'Hedera')
    ECMP_value_list = get_value_list_3(average_delay, traffics, items, 'ECMP')
    # write2file(EFattree_value_list, 'NMF', 'loss')
    # write2file(PureSDN_value_list, 'SRMF', 'loss')
    # write2file(Hedera_value_list, 'Hedera', 'loss')
    # write2file(ECMP_value_list, 'ECMP', 'loss')
    bar_width = 0.2
    plt.bar(index, EFattree_value_list, bar_width, color='r', label='Rfrag')
    plt.bar(index + 1 * bar_width, PureSDN_value_list, bar_width, color='g', label='NMF')
    plt.bar(index + 2 * bar_width, Hedera_value_list, bar_width, color='y', label='SRMF')
    plt.bar(index + 3 * bar_width, ECMP_value_list, bar_width, color='b', label='ECMP')

    for x,y in zip(index,EFattree_value_list):
        plt.text(x+0.1, y, '%.4f' % y, ha='center', va= 'bottom',fontsize=10)
    for x,y in zip(index + 1 * bar_width,PureSDN_value_list):
        plt.text(x+0.1, y, '%.4f' % y, ha='center', va= 'bottom',fontsize=10)
    for x,y in zip(index + 2 * bar_width,Hedera_value_list):
        plt.text(x+0.1, y, '%.4f' % y, ha='center', va= 'bottom',fontsize=10)
    for x,y in zip(index + 3 * bar_width,ECMP_value_list):
        plt.text(x+0.1, y, '%.4f' % y, ha='center', va= 'bottom',fontsize=10)


    plt.xticks(index + num_bar / 2.0 * bar_width, traffics, fontsize='small')
    plt.ylabel(u'小流丢包率\n', fontsize='xx-large', fontproperties=chinese_font)
    plt.yticks(fontsize='large')
    plt.legend(loc='upper right', ncol=len(apps), fontsize='small')
    plt.grid(axis='y')
    plt.tight_layout()
    plt.savefig(args.out_dir + '/6.packet_loss_rate.png')
    # 7. Plot mean deviation of round-trip delay of delay-sensitive traffic.
    item = 'mean_deviation_of_round_trip_delay'
    fig = plt.figure()
    fig.set_size_inches(15, 5)
    num_groups = len(traffics)
    num_bar = len(apps)
    EFattree_value_list = get_value_list_2(average_delay, traffics, item, 'NMF')
    PureSDN_value_list = get_value_list_2(average_delay, traffics, item, 'SRMF')
    Hedera_value_list = get_value_list_2(average_delay, traffics, item, 'Hedera')
    ECMP_value_list = get_value_list_2(average_delay, traffics, item, 'ECMP')
    # write2file(EFattree_value_list, 'NMF', 'mdelay')
    # write2file(PureSDN_value_list, 'SRMF', 'mdelay')
    # write2file(Hedera_value_list, 'Hedera', 'mdelay')
    # write2file(ECMP_value_list, 'ECMP', 'mdelay')
    index = np.arange(num_groups) + 0.15
    bar_width = 0.2
    plt.bar(index, EFattree_value_list, bar_width, color='r', label='NMF')
    plt.bar(index + 1 * bar_width, PureSDN_value_list, bar_width, color='g', label='SRMF')
    plt.bar(index + 2 * bar_width, Hedera_value_list, bar_width, color='y', label='Hedera')
    plt.bar(index + 3 * bar_width, ECMP_value_list, bar_width, color='b', label='ECMP')
    for x,y in zip(index,EFattree_value_list):
        plt.text(x+0.1, y+0.05, '%.2f' % y, ha='center', va= 'bottom',fontsize=10)
    for x,y in zip(index + 1 * bar_width,PureSDN_value_list):
        plt.text(x+0.1, y+0.05, '%.2f' % y, ha='center', va= 'bottom',fontsize=10)
    for x,y in zip(index + 2 * bar_width,Hedera_value_list):
        plt.text(x+0.1, y+0.05, '%.2f' % y, ha='center', va= 'bottom',fontsize=10)
    for x,y in zip(index + 3 * bar_width,ECMP_value_list):
        plt.text(x+0.1, y+0.05, '%.2f' % y, ha='center', va= 'bottom',fontsize=10)
    plt.xticks(index + num_bar / 2.0 * bar_width, traffics, fontsize='small')
    plt.ylabel(u'小流往返时延平均偏差\n(ms)', fontsize='xx-large', fontproperties=chinese_font)
    plt.yticks(fontsize='large')
    plt.legend(loc='upper right', ncol=len(apps), fontsize='small')
    plt.grid(axis='y')
    plt.tight_layout()
    plt.savefig(args.out_dir + '/7.mean_deviation_of_round_trip_delay.png')


if __name__ == '__main__':
    plot_results()
