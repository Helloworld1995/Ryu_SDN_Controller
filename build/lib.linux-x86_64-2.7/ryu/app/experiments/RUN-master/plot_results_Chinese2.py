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
chinese_font = FontProperties(
    fname='/usr/share/matplotlib/mpl-data/fonts/ttf/simhei.ttf')


parser = argparse.ArgumentParser(
    description="Plot BFlows experiments' results")
parser.add_argument('--k', dest='k', type=int, default=4,
                    choices=[4, 8], help="Switch fanout number")
parser.add_argument('--duration', dest='duration', type=int, default=60,
                    help="Duration (sec) for each iperf traffic generation")
parser.add_argument('--dir', dest='out_dir', help="Directory to store outputs")
parser.add_argument('--fnum', dest='flows_num_per_host',
                    type=int, default=1, help="Number of iperf flows per host")
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
    #     average_value = sum(map(float, value_list)) / len(value_list)
    average_value = sum(map(float, value_list)) / 1
    return average_value


def get_value_list_2(value_dict, traffics, item, app):
    """
            Get the values from the  data structure.
    """
    value_list = []
    complete_list = []
    for traffic in traffics:
        complete_list.append(value_dict[traffic][item][app])
    for i in xrange(4):
        value_list.append(calculate_average(
            complete_list[(i * 1): (i * 1 + 1)]))
    return value_list


def get_utilization(utilization, traffic, app, input_file):
    """
            Get link utilization and link bandwidth utilization.
    """
    lines_list = read_file_1(input_file)
    first_second = int(lines_list[0][0])
    column_packets_out = 11   # packets_out
    column_packets_in = 10   # packets_in
    column_bytes_out = 6   # bytes_out
    column_bytes_in = 5   # bytes_in

    if not utilization.has_key(traffic):
        utilization[traffic] = {}
    if not utilization[traffic].has_key(app):
        utilization[traffic][app] = {}

    for row in lines_list:
        iface_name = row[1]
        if iface_name.startswith('1'):
            # Take the good values only.
            if (int(row[0]) - first_second) <= args.duration:
                if not utilization[traffic][app].has_key(iface_name):
                    utilization[traffic][app][iface_name] = {
                        'LU_out': 0, 'LU_in': 0, 'LBU_out': 0, 'LBU_in': 0}
                if row[6] not in ['0', '0.00', '1960', '3920', '3990', '5880', '60', '120']:
                    utilization[traffic][app][iface_name]['LU_out'] = 1
                if row[5] not in ['0', '0.00', '1960', '3920', '3990', '5880', '60', '120']:
                    utilization[traffic][app][iface_name]['LU_in'] = 1
                utilization[traffic][app][iface_name]['LBU_out'] += int(row[6])
                utilization[traffic][app][iface_name]['LBU_in'] += int(row[5])
        elif iface_name.startswith('2'):
            # Choose down-going interfaces only.
            if int(iface_name[-1]) > args.k / 2:
                # Take the good values only.
                if (int(row[0]) - first_second) <= args.duration:
                    if not utilization[traffic][app].has_key(iface_name):
                        utilization[traffic][app][iface_name] = {
                            'LU_out': 0, 'LU_in': 0, 'LBU_out': 0, 'LBU_in': 0}
                    if row[6] not in ['0', '0.00', '1960', '3920', '3990', '5880', '60', '120']:
                        utilization[traffic][app][iface_name]['LU_out'] = 1
                    if row[5] not in ['0', '0.00', '1960', '3920', '3990', '5880', '60', '120']:
                        utilization[traffic][app][iface_name]['LU_in'] = 1
                    utilization[traffic][app][iface_name]['LBU_out'] += int(
                        row[6])
                    utilization[traffic][app][iface_name]['LBU_in'] += int(
                        row[5])
        else:
            pass

    return utilization


def get_link_utilization_ratio(utilization, traffics, app):
    value_list = []
    num_list = []
    complete_list = []
    average_list = []
    for traffic in traffics:
        num = 0
        for interface in utilization[traffic][app].keys():
            if utilization[traffic][app][interface]['LU_out'] == 1:
                num += 1
            if utilization[traffic][app][interface]['LU_in'] == 1:
                num += 1
        num_list.append(num)
        complete_list.append(
            float(num) / (len(utilization[traffic][app].keys()) * 2))
    for i in xrange(len(traffics)):
        value_list.append(calculate_average(
            complete_list[(i * 1): (i * 1 + 1)]))
    for i in xrange(len(traffics)):
        average_list.append(calculate_average(num_list[(i * 1): (i * 1 + 1)]))
    return value_list


def get_value_list_3(utilization, some_traffics, app):
    """
            Get link bandwidth utilization ratio.
    """
    value_list = []
    link_bandwidth_utilization = {}
    utilization_list = []
    for i in np.linspace(0, 1, 101):
        link_bandwidth_utilization[i] = 0

    for traffic in some_traffics:
        for interface in utilization[traffic][app].keys():
            ratio_out = float(utilization[traffic][app][interface]
                              ['LBU_out'] * 8) / (100.0 * (10 ** 6) * args.duration)
            ratio_in = float(utilization[traffic][app][interface]
                             ['LBU_in'] * 8) / (100.0 * (10 ** 6) * args.duration)
            utilization_list.append(ratio_out)
            utilization_list.append(ratio_in)

    for ratio in utilization_list:
        for seq in link_bandwidth_utilization.keys():
            if ratio <= seq:
                link_bandwidth_utilization[seq] += 1

    for seq in link_bandwidth_utilization.keys():
        link_bandwidth_utilization[seq] = float(
            link_bandwidth_utilization[seq]) / len(utilization_list)

    for seq in sorted(link_bandwidth_utilization.keys()):
        value_list.append(link_bandwidth_utilization[seq])

    return value_list


def plot_results():
    #_traffics="random1 stag1_0.1_0.2 stag1_0.2_0.3 stag1_0.3_0.3 stag1_0.4_0.3 stag1_0.5_0.3 stag1_0.6_0.2 stag1_0.7_0.2 stag1_0.8_0.1"
    _traffics = "random stag1_0.1_0.2 stag1_0.2_0.3 stag1_0.4_0.3 stag1_0.5_0.3 stag1_0.6_0.2 stag1_0.7_0.2 stag1_0.8_0.1"
    #_traffics = traffics="stag1_0.1_0.2 stag2_0.1_0.2 stag3_0.1_0.2 stag4_0.1_0.2 stag5_0.1_0.2 stag1_0.2_0.3 stag2_0.2_0.3 stag3_0.2_0.3 stag4_0.2_0.3 stag5_0.2_0.3 stag1_0.3_0.3 stag2_0.3_0.3 stag3_0.3_0.3 stag4_0.3_0.3 stag5_0.3_0.3 stag1_0.4_0.3 stag2_0.4_0.3 stag3_0.4_0.3 stag4_0.4_0.3 stag5_0.4_0.3"
    traffics = _traffics.split(' ')
    # traffics = ["stag1_0.5_0.3"]
    #traffics_brief = ['random', 'stag_0.2_0.3', 'stag_0.4_0.3', 'stag_0.6_0.2']
    # traffics_brief = ["stag1_0.5_0.3"]
    #traffics_brief = ['random','stag_0.1_0.2', 'stag_0.2_0.3', 'stag_0.3_0.3', 'stag_0.4_0.3', 'stag_0.5_0.3', 'stag_0.6_0.2', 'stag_0.7_0.2', 'stag_0.8_0.1']
    apps = ['NMF', 'SRMF', 'Hedera', 'ECMP']
    utilization = {}

    for traffic in traffics:
        for app in apps:
            bwmng_file = args.out_dir + '/%s/%s/bwmng.txt' % (traffic, app)
            utilization = get_utilization(
                utilization, traffic, app, bwmng_file)

    #  Plot link utilization ratio.
    fig = plt.figure()
    fig.set_size_inches(15, 5)
    num_groups = len(traffics)
    num_bar = len(apps)
    ECMP_value_list = get_link_utilization_ratio(utilization, traffics, 'NMF')
    EFattree_value_list = get_link_utilization_ratio(
        utilization, traffics, 'SRMF')
    PureSDN_value_list = get_link_utilization_ratio(
        utilization, traffics, 'Hedera')
    Hedera_value_list = get_link_utilization_ratio(
        utilization, traffics, 'ECMP')
    index = np.arange(num_groups) + 0.15
    bar_width = 0.2
    plt.bar(index + 0 * bar_width, EFattree_value_list,
            bar_width, color='r', label='NMF')
    plt.bar(index + 1 * bar_width, ECMP_value_list,
            bar_width, color='b', label='SRMF')
    plt.bar(index + 2 * bar_width, Hedera_value_list,
            bar_width, color='y', label='Hedera')
    plt.bar(index + 3 * bar_width, PureSDN_value_list,
            bar_width, color='g', label='ECMP')
    for x, y in zip(index, EFattree_value_list):
        plt.text(x + 0.03, y + 0.01, '%.2f' %
                 y, ha='center', va='bottom', fontsize=10)
    for x, y in zip(index + 3 * bar_width, ECMP_value_list):
        plt.text(x + 0.03, y + 0.01, '%.2f' %
                 y, ha='center', va='bottom', fontsize=10)
    for x, y in zip(index + 2 * bar_width, Hedera_value_list):
        plt.text(x + 0.03, y + 0.01, '%.2f' %
                 y, ha='center', va='bottom', fontsize=10)
    for x, y in zip(index + 1 * bar_width, PureSDN_value_list):
        plt.text(x + 0.03, y + 0.01, '%.2f' %
                 y, ha='center', va='bottom', fontsize=10)

    plt.xticks(index + num_bar / 2.0 * bar_width,
               traffics, fontsize='small')
    plt.ylabel(u'链路利用率\n', fontsize='xx-large', fontproperties=chinese_font)

    plt.ylim(0, 1)
    plt.yticks(np.linspace(0, 1, 11))
    plt.legend(loc='upper right', ncol=len(apps), fontsize='small')
    plt.grid(axis='y')
    plt.tight_layout()

    plt.savefig(args.out_dir + '/8.link_utilization_ratio.png')

    # 4. Plot link bandwidth utilization ratio.
    fig = plt.figure()
    fig.set_size_inches(18, 12)
    num_subplot = len(traffics)
    num_raw = 3
    num_column = 3
    NO_subplot = 1
    x = np.linspace(0, 1, 101)
    for i in xrange(len(traffics)):
        plt.subplot(num_raw, num_column, NO_subplot)
        y1 = get_value_list_3(
            utilization, traffics[(i * 1): (i * 1 + 1)], 'NMF')
        y2 = get_value_list_3(
            utilization, traffics[(i * 1): (i * 1 + 1)], 'SRMF')
        y3 = get_value_list_3(
            utilization, traffics[(i * 1): (i * 1 + 1)], 'Hedera')
        y4 = get_value_list_3(
            utilization, traffics[(i * 1): (i * 1 + 1)], 'ECMP')

        plt.plot(x, y1, 'r-', linewidth=2, label="NMF")
        plt.plot(x, y2, 'b-', linewidth=2, label="SRMF")
        plt.plot(x, y3, 'y-', linewidth=2, label="Hedera")
        plt.plot(x, y4, 'g-', linewidth=2, label="ECMP")

        plt.title('%s' % traffics[i], fontsize='xx-large')
        plt.xlabel(u'链路带宽利用率', fontsize='xx-large',
                   fontproperties=chinese_font)
        plt.xlim(0, 1)
        plt.xticks(np.linspace(0, 1, 11))
        plt.ylabel(u'链路带宽利用率\n累积分布函数', fontsize='xx-large',
                   fontproperties=chinese_font)
        plt.ylim(0, 1)
        plt.yticks(np.linspace(0, 1, 11))
        plt.legend(loc='lower right', fontsize='large')
        plt.grid(True)
        NO_subplot += 1
    plt.tight_layout()
    plt.savefig(args.out_dir + '/9.link_bandwidth_utilization_ratio.png')


if __name__ == '__main__':
    plot_results()
