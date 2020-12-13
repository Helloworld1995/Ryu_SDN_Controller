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
    # for i in xrange(10):
    #     value_list.append(calculate_average(complete_list[(i * 10): (i * 10 + 10)]))
    return complete_list

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

def plot_results():
    plot_dict = {}
    plot_dict.setdefault('delay', {})
    plot_dict.setdefault('loss', {})
    plot_dict.setdefault('mdelay',{})
    colorlist = ['r', 'g', 'b', 'y', 'pink', 'k', 'orange', 'brown', 'purple', 'darkslategray']
    count = 0

    #_traffics="random1 stag1_0.1_0.2 stag1_0.2_0.3 stag1_0.3_0.3 stag1_0.4_0.3 stag1_0.5_0.3 stag1_0.6_0.2 stag1_0.7_0.2 stag1_0.8_0.1"
    _traffics = "SRMF"
    # _traffics = "stag6_0.7_0.2"
    #_traffics="stag1_0.1_0.2 stag2_0.1_0.2 stag3_0.1_0.2 stag4_0.1_0.2 stag5_0.1_0.2 stag1_0.2_0.3 stag2_0.2_0.3 stag3_0.2_0.3 stag4_0.2_0.3 stag5_0.2_0.3 stag1_0.3_0.3 stag2_0.3_0.3 stag3_0.3_0.3 stag4_0.3_0.3 stag5_0.3_0.3 stag1_0.4_0.3 stag2_0.4_0.3 stag3_0.4_0.3 stag4_0.4_0.3 stag5_0.4_0.3"
    #_traffics = "stag1_0.5_0.3 stag2_0.5_0.3 stag3_0.5_0.3 stag4_0.5_0.3 stag5_0.5_0.3 stag6_0.5_0.3 stag7_0.5_0.3 stag8_0.5_0.3 stag9_0.5_0.3 stag10_0.5_0.3 stag11_0.5_0.3 stag12_0.5_0.3 stag13_0.5_0.3 stag14_0.5_0.3 stag15_0.5_0.3 stag16_0.5_0.3 stag17_0.5_0.3 stag18_0.5_0.3 stag19_0.5_0.3 stag20_0.5_0.3 stag1_0.6_0.2 stag2_0.6_0.2 stag3_0.6_0.2 stag4_0.6_0.2 stag5_0.6_0.2 stag6_0.6_0.2 stag7_0.6_0.2 stag8_0.6_0.2 stag9_0.6_0.2 stag10_0.6_0.2 stag11_0.6_0.2 stag12_0.6_0.2 stag13_0.6_0.2 stag14_0.6_0.2 stag15_0.6_0.2 stag16_0.6_0.2 stag17_0.6_0.2 stag18_0.6_0.2 stag19_0.6_0.2 stag20_0.6_0.2 stag1_0.7_0.2 stag2_0.7_0.2 stag3_0.7_0.2 stag4_0.7_0.2 stag5_0.7_0.2 stag6_0.7_0.2 stag7_0.7_0.2 stag8_0.7_0.2 stag9_0.7_0.2 stag10_0.7_0.2 stag11_0.7_0.2 stag12_0.7_0.2 stag13_0.7_0.2 stag14_0.7_0.2 stag15_0.7_0.2 stag16_0.7_0.2 stag17_0.7_0.2 stag18_0.7_0.2 stag19_0.7_0.2 stag20_0.7_0.2 stag1_0.8_0.1 stag2_0.8_0.1 stag3_0.8_0.1 stag4_0.8_0.1 stag5_0.8_0.1 stag6_0.8_0.1 stag7_0.8_0.1 stag8_0.8_0.1 stag9_0.8_0.1 stag10_0.8_0.1 stag11_0.8_0.1 stag12_0.8_0.1 stag13_0.8_0.1 stag14_0.8_0.1 stag15_0.8_0.1 stag16_0.8_0.1 stag17_0.8_0.1 stag18_0.8_0.1 stag19_0.8_0.1 stag20_0.8_0.1"
    traffics = _traffics.split(' ')
    #traffics_brief = ['random','stag_0.1_0.2', 'stag_0.2_0.3', 'stag_0.3_0.3', 'stag_0.4_0.3', 'stag_0.5_0.3', 'stag_0.6_0.2', 'stag_0.7_0.2', 'stag_0.8_0.1']
    # traffics_brief = ['random','stag_0.2_0.3','stag_0.4_0.3', 'stag_0.6_0.2', 'stag_0.8_0.1']
    round = ['1', '2', '3', '4', '5', '6', '7', '8', '9', '10']
    apps=['0.1','0.2','0.3','0.4','0.5','0.6','0.7','0.8','0.9']
    throughput = {}
    first_packet_delay = {}
    average_delay = {}

    for traffic in traffics:
        for r in round:
            for app in apps:
                bwmng_file = args.out_dir + '/%s/%s/%s/bwmng.txt' % (r,app,traffic)
                keys2 = ['average_round_trip_delay', 'mean_deviation_of_round_trip_delay', 'total_send', 'total_receive']
                first_packet_file = args.out_dir + '/%s/%s/first_packets.txt' % (traffic, app)
                successive_packets_file = args.out_dir + '/%s/%s/%s/successive_packets.txt' % (r,app,traffic)
                average_delay = get_delay(average_delay, traffic, keys2, app, successive_packets_file)
    # 5. Plot average packet round-trip delay of delay-sensitive traffic.
    item = ['average_round_trip_delay','mean_deviation_of_round_trip_delay']
    items = ['total_send', 'total_receive']

    # plot average delay
    fig = plt.figure()
    fig.set_size_inches(15, 5)
    num_groups = len(traffics)
    num_bar = len(apps)
    index = np.arange(num_groups) + 0.15
    bar_width = 0.2
    for app in apps:
        temp_list1=get_value_list_2(average_delay,traffics,item[0],app)
        plot_dict['delay'][app]=temp_list1
        temp_list2 = get_value_list_2(average_delay, traffics, item[1], app)
        plot_dict['mdelay'][app]=temp_list2
        temp_list3=get_value_list_3(average_delay, traffics, items, app)
        plot_dict['loss'][app] = temp_list3
    for p in plot_dict['delay']:
        plt.bar(index + count * bar_width, plot_dict['delay'].get(p), bar_width, color=colorlist[count], label=p)
        count += 1
    count = 0
    index = np.arange(num_groups) + 0.15
    bar_width = 0.2
    plt.xticks(index + num_bar / 2.0 * bar_width, traffics, fontsize='small')
    for p in plot_dict['delay']:
        for x,y in zip(index+count*bar_width,plot_dict['delay'].get(p)):
            plt.text(x + 0.1, y + 0.05, '%.2f' % y, ha='center', va='bottom', fontsize=10)
        count+=1
    count=0
    plt.ylabel(u'小流平均往返时延\n(ms)', fontsize='xx-large', fontproperties=chinese_font)
    plt.yticks(fontsize='large')
    plt.legend(loc='upper right', ncol=len(apps), fontsize='small')
    plt.grid(axis='y')
    plt.tight_layout()
    plt.savefig(args.out_dir + '/5.average_round_trip_delay.png')


    #plot mean_deviation_of_round_trip_delay
    fig = plt.figure()
    fig.set_size_inches(15, 5)
    index = np.arange(num_groups) + 0.15
    for p in plot_dict['mdelay']:
        plt.bar(index + count * bar_width, plot_dict['mdelay'].get(p), bar_width, color=colorlist[count], label=p)
        count += 1
    count = 0
    for p in plot_dict['mdelay']:
        for x,y in zip(index+count*bar_width,plot_dict['mdelay'].get(p)):
            plt.text(x + 0.1, y + 0.05, '%.2f' % y, ha='center', va='bottom', fontsize=10)
        count+=1
    count=0
    plt.xticks(index + num_bar / 2.0 * bar_width,traffics, fontsize='small')
    plt.ylabel(u'小流往返时延平均偏差\n(ms)', fontsize='xx-large', fontproperties=chinese_font)
    plt.yticks(fontsize='large')
    plt.legend(loc='upper right', ncol=len(apps), fontsize='small')
    plt.grid(axis='y')
    plt.tight_layout()
    plt.savefig(args.out_dir + '/7.mean_deviation_of_round_trip_delay.png')


    #plot average loss
    fig = plt.figure()
    fig.set_size_inches(15, 5)
    index = np.arange(num_groups) + 0.15
    bar_width = 0.2
    for p in plot_dict['loss']:
        plt.bar(index + count * bar_width, plot_dict['loss'].get(p), bar_width, color=colorlist[count], label=p)
        count += 1
    count = 0
    for p in plot_dict['loss']:
        for x,y in zip(index+count*bar_width,plot_dict['loss'].get(p)):
            plt.text(x + 0.1, y, '%.4f' % y, ha='center', va='bottom', fontsize=10)
        count+=1
    plt.xticks(index + num_bar / 2.0 * bar_width, traffics, fontsize='small')
    plt.ylabel(u'小流丢包率\n', fontsize='xx-large', fontproperties=chinese_font)
    plt.yticks(fontsize='large')
    plt.legend(loc='upper right', ncol=len(apps), fontsize='small')
    plt.grid(axis='y')
    plt.tight_layout()
    plt.savefig(args.out_dir + '/6.packet_loss_rate.png')

    #

if __name__ == '__main__':
    plot_results()
