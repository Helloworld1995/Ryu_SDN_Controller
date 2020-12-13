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
import os

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

def get_throughput(throughput, traffic, app, input_file):
	
	full_bisection_bw = 100.0 * (args.k ** 3 / 4)   # (unit: Mbit/s)
	lines_list = read_file_1(input_file)
	first_second = int(lines_list[0][0])
	column_bytes_out_rate = 2   # bytes_out/s
	column_bytes_out = 6   # bytes_out
	switch=None
	if app == 'NonBlocking':
		switch = '1001'
	elif app in ['Hedera', 'ECMP', 'NMF', 'SRMF']:
		switch = '3[0-9][0-9][0-9]'
	else:
		pass
	sw = re.compile(switch)

	if not throughput.has_key(traffic):
		throughput[traffic] = {}

	if not throughput[traffic].has_key('realtime_bisection_bw'):
		throughput[traffic]['realtime_bisection_bw'] = {}
	if not throughput[traffic].has_key('realtime_throughput'):
		throughput[traffic]['realtime_throughput'] = {}
	if not throughput[traffic].has_key('accumulated_throughput'):
		throughput[traffic]['accumulated_throughput'] = {}
	if not throughput[traffic].has_key('normalized_total_throughput'):
		throughput[traffic]['normalized_total_throughput'] = {}

	if not throughput[traffic]['realtime_bisection_bw'].has_key(app):
		throughput[traffic]['realtime_bisection_bw'][app] = {}
	if not throughput[traffic]['realtime_throughput'].has_key(app):
		throughput[traffic]['realtime_throughput'][app] = {}
	if not throughput[traffic]['accumulated_throughput'].has_key(app):
		throughput[traffic]['accumulated_throughput'][app] = {}
	if not throughput[traffic]['normalized_total_throughput'].has_key(app):
		throughput[traffic]['normalized_total_throughput'][app] = 0

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
					try:
						if int(iface_name[-1]) > args.k / 2:   # Choose down-going interfaces only.

								if (int(row[0]) - first_second) <= args.duration:   # Take the good values only.
									throughput[traffic]['realtime_bisection_bw'][app][int(row[0]) - first_second] += float(row[column_bytes_out_rate]) * 8.0 / (10 ** 6)   # Mbit/s
									throughput[traffic]['realtime_throughput'][app][int(row[0]) - first_second] += float(row[column_bytes_out]) * 8.0 / (10 ** 6)   # Mbit
					except:
						continue
			elif switch == '1001':   # Choose all the interfaces. (For NonBlocking Topo only)
				if sw.match(iface_name):
					try:
						if (int(row[0]) - first_second) <= args.duration:
							throughput[traffic]['realtime_bisection_bw'][app][int(row[0]) - first_second] += float(row[column_bytes_out_rate]) * 8.0 / (10 ** 6)   # Mbit/s
							throughput[traffic]['realtime_throughput'][app][int(row[0]) - first_second] += float(row[column_bytes_out]) * 8.0 / (10 ** 6)   # Mbit
					except:
						continue
			else:
				pass

	for i in xrange(args.duration + 1):
		for j in xrange(i+1):
			throughput[traffic]['accumulated_throughput'][app][i] += throughput[traffic]['realtime_throughput'][app][j]   # Mbit

	throughput[traffic]['normalized_total_throughput'][app] = throughput[traffic]['accumulated_throughput'][app][args.duration] / (full_bisection_bw * args.duration)   # percentage

	return throughput

def get_value_list_1(value_dict, traffic, item, app):
	"""
		Get the values from the "throughput" data structure.
	"""
	value_list = []
	for i in xrange(args.duration + 1):
		value_list.append(value_dict[traffic][item][app][i])
	return value_list

def get_average_bisection_bw(value_dict, traffics, app):
	value_list = []
	complete_list = []
	accumulated_throughput = []
	for traffic in traffics:
		complete_list.append(value_dict[traffic]['accumulated_throughput'][app][args.duration] / float(args.duration))
		accumulated_throughput.append(value_dict[traffic]['accumulated_throughput'][app][args.duration])
	# print "accumulated_throughput:", accumulated_throughput
	for i in xrange(len(traffics)):
		value_list.append(calculate_average(complete_list[(i * 1): (i * 1 + 1)]))
	return value_list

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
	
	full_bisection_bw = 100.0 * (args.k ** 3 / 4)   # (unit: Mbit/s)
	utmost_throughput = full_bisection_bw * args.duration
	_traffics="random stag1_0.1_0.2 stag1_0.2_0.3 stag1_0.4_0.3 stag1_0.5_0.3 stag1_0.6_0.2 stag1_0.7_0.2 stag1_0.8_0.1"
	# _traffics="random stag6_0.1_0.2 stag6_0.2_0.3 stag6_0.3_0.3 stag6_0.4_0.3 stag6_0.5_0.3 stag6_0.6_0.2 stag6_0.7_0.2 stag6_0.8_0.1"
	# _traffics = "stag6_0.7_0.2"
	#_traffics="stag1_0.1_0.2 stag2_0.1_0.2 stag3_0.1_0.2 stag4_0.1_0.2 stag5_0.1_0.2 stag1_0.2_0.3 stag2_0.2_0.3 stag3_0.2_0.3 stag4_0.2_0.3 stag5_0.2_0.3 stag1_0.3_0.3 stag2_0.3_0.3 stag3_0.3_0.3 stag4_0.3_0.3 stag5_0.3_0.3 stag1_0.4_0.3 stag2_0.4_0.3 stag3_0.4_0.3 stag4_0.4_0.3 stag5_0.4_0.3"
	#_traffics = traffics="stag1_0.1_0.2 stag2_0.1_0.2 stag3_0.1_0.2 stag4_0.1_0.2 stag5_0.1_0.2 stag1_0.2_0.3 stag2_0.2_0.3 stag3_0.2_0.3 stag4_0.2_0.3 stag5_0.2_0.3 stag1_0.3_0.3 stag2_0.3_0.3 stag3_0.3_0.3 stag4_0.3_0.3 stag5_0.3_0.3 stag1_0.4_0.3 stag2_0.4_0.3 stag3_0.4_0.3 stag4_0.4_0.3 stag5_0.4_0.3"
	#_traffics = "stag1_0.5_0.3 stag2_0.5_0.3 stag3_0.5_0.3 stag4_0.5_0.3 stag5_0.5_0.3 stag6_0.5_0.3 stag7_0.5_0.3 stag8_0.5_0.3 stag9_0.5_0.3 stag10_0.5_0.3 stag11_0.5_0.3 stag12_0.5_0.3 stag13_0.5_0.3 stag14_0.5_0.3 stag15_0.5_0.3 stag16_0.5_0.3 stag17_0.5_0.3 stag18_0.5_0.3 stag19_0.5_0.3 stag20_0.5_0.3 stag1_0.6_0.2 stag2_0.6_0.2 stag3_0.6_0.2 stag4_0.6_0.2 stag5_0.6_0.2 stag6_0.6_0.2 stag7_0.6_0.2 stag8_0.6_0.2 stag9_0.6_0.2 stag10_0.6_0.2 stag11_0.6_0.2 stag12_0.6_0.2 stag13_0.6_0.2 stag14_0.6_0.2 stag15_0.6_0.2 stag16_0.6_0.2 stag17_0.6_0.2 stag18_0.6_0.2 stag19_0.6_0.2 stag20_0.6_0.2 stag1_0.7_0.2 stag2_0.7_0.2 stag3_0.7_0.2 stag4_0.7_0.2 stag5_0.7_0.2 stag6_0.7_0.2 stag7_0.7_0.2 stag8_0.7_0.2 stag9_0.7_0.2 stag10_0.7_0.2 stag11_0.7_0.2 stag12_0.7_0.2 stag13_0.7_0.2 stag14_0.7_0.2 stag15_0.7_0.2 stag16_0.7_0.2 stag17_0.7_0.2 stag18_0.7_0.2 stag19_0.7_0.2 stag20_0.7_0.2 stag1_0.8_0.1 stag2_0.8_0.1 stag3_0.8_0.1 stag4_0.8_0.1 stag5_0.8_0.1 stag6_0.8_0.1 stag7_0.8_0.1 stag8_0.8_0.1 stag9_0.8_0.1 stag10_0.8_0.1 stag11_0.8_0.1 stag12_0.8_0.1 stag13_0.8_0.1 stag14_0.8_0.1 stag15_0.8_0.1 stag16_0.8_0.1 stag17_0.8_0.1 stag18_0.8_0.1 stag19_0.8_0.1 stag20_0.8_0.1"
	traffics = _traffics.split(' ')

	#traffics_brief = ['random','stag_0.1_0.2', 'stag_0.2_0.3', 'stag_0.3_0.3', 'stag_0.4_0.3', 'stag_0.5_0.3', 'stag_0.6_0.2', 'stag_0.7_0.2', 'stag_0.8_0.1']
	#apps = ['EFattree', 'ECMP', 'PureSDN', 'Hedera']
	apps = ['ECMP', 'Hedera','NMF','SRMF']
	throughput = {}
	first_packet_delay = {}
	average_delay = {}

	for traffic in traffics:
		for app in apps:
			bwmng_file = args.out_dir + '/%s/%s/bwmng.txt' % (traffic, app)
			throughput = get_throughput(throughput, traffic, app, bwmng_file)

	# 1. Plot average throughput.
	fig = plt.figure()
	fig.set_size_inches(15, 5)
	num_groups = len(traffics)
	num_bar = len(apps)
	NMF_value_list = get_average_bisection_bw(throughput, traffics, 'NMF')
	SRMF_value_list = get_average_bisection_bw(throughput, traffics, 'SRMF')
	ECMP_value_list = get_average_bisection_bw(throughput, traffics, 'ECMP')
	Hedera_value_list = get_average_bisection_bw(throughput, traffics, 'Hedera')
	write2file(NMF_value_list,'NMF','average')
	write2file(SRMF_value_list,'SRMF','average')
	write2file(Hedera_value_list,'Hedera','average')
	write2file(ECMP_value_list,'ECMP','average')
	index = np.arange(num_groups) + 0.15
	bar_width = 0.2
	plt.bar(index + 0 * bar_width, NMF_value_list, bar_width, color='r', label='NMF')
	plt.bar(index + 1 * bar_width, SRMF_value_list, bar_width, color='g', label='SRMF')
	plt.bar(index + 2 * bar_width, Hedera_value_list, bar_width, color='y', label='Hedera')
	plt.bar(index + 3 * bar_width, ECMP_value_list, bar_width, color='b', label='ECMP')
	
	for x,y in zip(index,NMF_value_list):
		plt.text(x+0.09, y+0.05, '%.0f' % y, ha='center', va= 'bottom',fontsize=10)
	for x,y in zip(index + 1 * bar_width,SRMF_value_list):
		plt.text(x+0.09, y+0.05, '%.0f' % y, ha='center', va= 'bottom',fontsize=10)
	for x,y in zip(index + 2 * bar_width,Hedera_value_list):
		plt.text(x+0.09, y+0.05, '%.0f' % y, ha='center', va= 'bottom',fontsize=10)
	for x,y in zip(index + 3 * bar_width,ECMP_value_list):
		plt.text(x+0.09, y+0.05, '%.0f' % y, ha='center', va= 'bottom',fontsize=10)
	plt.xticks(index + num_bar / 2.0 * bar_width, traffics, fontsize='small')
	plt.ylabel(u'平均吞吐率\n(Mbps)', fontsize='xx-large', fontproperties=chinese_font)
	plt.ylim(0, full_bisection_bw)
	plt.yticks(np.linspace(0, full_bisection_bw, 11), fontsize='small')
	plt.legend(loc='upper right', ncol=len(apps), fontsize='small')
	plt.grid(axis='y')
	plt.tight_layout()
	plt.savefig(args.out_dir + '/1.average_throughput.png')

	# 2. Plot normalized total throughput.
	item = 'normalized_total_throughput'
	fig = plt.figure()
	fig.set_size_inches(15, 5)
	num_groups = len(traffics)
	num_bar = len(apps)
	NMF_value_list = get_value_list_2(throughput, traffics, item, 'NMF')
	SRMF_value_list = get_value_list_2(throughput, traffics, item, 'SRMF')
	Hedera_value_list = get_value_list_2(throughput, traffics, item, 'Hedera')
	ECMP_value_list = get_value_list_2(throughput, traffics, item, 'ECMP')
	print np.array(NMF_value_list)/full_bisection_bw
	index = np.arange(num_groups) + 0.15
	bar_width = 0.2
	plt.bar(index + 0 * bar_width, NMF_value_list, bar_width, color='r', label='NMF')
	plt.bar(index + 1 * bar_width, SRMF_value_list, bar_width, color='g', label='SRMF')
	plt.bar(index + 2 * bar_width, Hedera_value_list, bar_width, color='y', label='Hedera')
	plt.bar(index + 3 * bar_width,ECMP_value_list, bar_width, color='b', label='ECMP')
	for x,y in zip(index,NMF_value_list):
		plt.text(x+0.09, y+0.02, '%.2f' % y, ha='center', va= 'bottom',fontsize=10)
	for x,y in zip(index + 1 * bar_width,SRMF_value_list):
		plt.text(x+0.09, y+0.02, '%.2f' % y, ha='center', va= 'bottom',fontsize=10)
	for x,y in zip(index + 2 * bar_width,Hedera_value_list):
		plt.text(x+0.09, y+0.02, '%.2f' % y, ha='center', va= 'bottom',fontsize=10)
	for x,y in zip(index + 3 * bar_width,ECMP_value_list):
		plt.text(x+0.09, y+0.02, '%.2f' % y, ha='center', va= 'bottom',fontsize=10)

	plt.xticks(index + num_bar / 2.0 * bar_width, traffics, fontsize='small')
	plt.ylabel(u'标准化总吞吐量\n', fontsize='xx-large', fontproperties=chinese_font)
	plt.yticks(np.linspace(0, 1, 11), fontsize='large')
	plt.legend(loc='upper right', ncol=len(apps), fontsize='small')
	plt.grid(axis='y')
	plt.tight_layout()
	plt.savefig(args.out_dir + '/2.normalized_total_throughput.png')


if __name__ == '__main__':
	plot_results()
