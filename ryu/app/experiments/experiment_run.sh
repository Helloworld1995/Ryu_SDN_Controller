#!/bin/bash
# Copyright (C) 2016 Huang MaChi at Chongqing University
# of Posts and Telecommunications, China.

k=$1
#cpu=$2
flow_num=$2   # number of iperf flows per host.
#duration=$4
out_dir=$3

# Exit on any failure.
set -e

# Check for uninitialized variables.
set -o nounset

ctrlc() {
	killall python
	killall -9 ryu-manager
	mn -c
	exit
}

trap ctrlc INT

# Traffic patterns.
# "stag_0.5_0.3" means 50% under the same Edge switch,
# 30% between different Edge switches in the same Pod,
# and 20% between different Pods.
# "random" means choosing the iperf server randomly.
# Change it if needed.
#traffics="random1 random2 random3 random4 random5 random6 random7 random8 stag1_0.1_0.2 stag2_0.1_0.2 stag3_0.1_0.2 stag4_0.1_0.2 stag5_0.1_0.2 stag6_0.1_0.2 stag7_0.1_0.2 stag8_0.1_0.2 stag1_0.2_0.3 stag2_0.2_0.3 stag3_0.2_0.3 stag4_0.2_0.3 stag5_0.2_0.3 stag6_0.2_0.3 stag7_0.2_0.3 stag8_0.2_0.3 stag1_0.3_0.3 stag2_0.3_0.3 stag3_0.3_0.3 stag4_0.3_0.3 stag5_0.3_0.3 stag6_0.3_0.3 stag7_0.3_0.3 stag8_0.3_0.3 stag1_0.4_0.3 stag2_0.4_0.3 stag3_0.4_0.3 stag4_0.4_0.3 stag5_0.4_0.3 stag6_0.4_0.3 stag7_0.4_0.3 stag8_0.4_0.3 stag1_0.5_0.3 stag2_0.5_0.3 stag3_0.5_0.3 stag4_0.5_0.3 stag5_0.5_0.3 stag6_0.5_0.3 stag7_0.5_0.3 stag8_0.5_0.3 stag1_0.6_0.2 stag2_0.6_0.2 stag3_0.6_0.2 stag4_0.6_0.2 stag5_0.6_0.2 stag6_0.6_0.2 stag7_0.6_0.2 stag8_0.6_0.2 stag1_0.7_0.2 stag2_0.7_0.2 stag3_0.7_0.2 stag4_0.7_0.2 stag5_0.7_0.2 stag6_0.7_0.2 stag7_0.7_0.2 stag8_0.7_0.2 stag1_0.8_0.1 stag2_0.8_0.1 stag3_0.8_0.1 stag4_0.8_0.1 stag5_0.8_0.1 stag6_0.8_0.1 stag7_0.8_0.1 stag8_0.8_0.1"
traffics="random"
# Run experiments.
for traffic in $traffics
do

#	# ECMP
#	dir=$out_dir/$flow_num/$traffic/ECMP
#	mkdir -p $dir
#	mn -c
#	sudo python ./ECMP/fattree.py --k $k --duration $duration --dir $dir --cpu $cpu
#
# #PureSDN
#	dir=$out_dir/$flow_num/$traffic/PureSDN
#	mkdir -p $dir
#	mn -c
#	sudo python ./PureSDN/SegmentECMPfattree4.py --k $k --duration $duration --dir $dir --cpu $cpu
#
##Hedera
#	dir=$out_dir/$flow_num/$traffic/Hedera
#	mkdir -p $dir
#	mn -c
#	sudo python ./Hedera/fattree4.py --k $k --duration $duration --dir $dir --cpu $cpu

#myNormal
  dir=$out_dir/$flow_num/$traffic/Normalrouting/bwmng
	mkdir -p $dir
	dir=$out_dir/$flow_num/$traffic/Normalrouting/pingTest
	mkdir -p $dir
	dir=$out_dir/$flow_num/$traffic/Normalrouting
	sudo mn -c
	sudo python ./PureSDNPkt/NormalFattree.py --k $k --dir $dir --fnum $flow_num

  sleep 1
#mySR
  dir=$out_dir/$flow_num/$traffic/SRrouting/bwmng
	mkdir -p $dir
	dir=$out_dir/$flow_num/$traffic/SRrouting/pingTest
	mkdir -p $dir
	dir=$out_dir/$flow_num/$traffic/SRrouting
	sudo mn -c
	sudo python ./PureSDNPkt/SegmentFattree.py --k $k --dir $dir --fnum $flow_num
	# NonBlocking
#	dir=$out_dir/$flowsPerHost/$traffic/NonBlocking
#	mkdir -p $dir
#	mn -c
#	sudo python ./NonBlocking/NonBlocking.py --k $k --duration $duration --dir $dir --cpu $cpu

done

# Plot results.
#sudo python ./plot_results_Chinese.py --k $k --duration $duration --dir $out_dir --fnum $flowsPerHost
