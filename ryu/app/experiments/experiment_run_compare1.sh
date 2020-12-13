#!/bin/bash
# Copyright (C) 2016 Huang MaChi at Chongqing University
# of Posts and Telecommunications, China.
printf $1
printf $2
printf $3
printf $4

k=$1
traffic=$2
flow_num=$3
#duration=$4
path=$4

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

# Run experiments.
  out_dir1=$path/$flow_num/$traffic
  mkdir -p $out_dir1
#  printf $out_dir
#	# ECMP
	dir1=$out_dir1/ECMP
	dir=$dir1/pingTest
	mkdir -p $dir
	dir=$dir1/bwmng
	mkdir -p $dir
	dir=$out_dir1/ECMP
	mkdir -p $dir
	sudo mn -c
#	sudo python ./ECMP/fattree.py --k $k --duration $duration --dir $dir --cpu $cpu
	sleep 2
#
# #PureSDN
#	dir=$out_dir/$flow_num/$traffic/PureSDN
#	mkdir -p $dir
#	mn -c
#	sudo python ./PureSDN/SegmentECMPfattree4.py --k $k --duration $duration --dir $dir --cpu $cpu
#
#Hedera
	dir1=$out_dir1/Hedera
	dir=$dir1/pingTest
	mkdir -p $dir
	dir=$dir1/bwmng
	mkdir -p $dir
	dir=$out_dir1/Hedera
	sudo mn -c
#	sudo python ./Hedera/fattree4.py --k $k --duration $duration --dir $dir --cpu $cpu
  sleep 2
##myNormal
#  dir=$out_dir/$flow_num/$traffic/Normalrouting/bwmng
#	mkdir -p $dir
#	dir=$out_dir/$flow_num/$traffic/Normalrouting/pingTest
#	mkdir -p $dir
#	dir=$out_dir/$flow_num/$traffic/Normalrouting
#	sudo mn -c
#	sudo python ./PureSDNPkt/NormalFattree.py --k $k --dir $dir --fnum $flow_num
#
#  sleep 1
  sleep 2
#mySR
  dir1=$out_dir1/SRMF
	dir=$dir1/pingTest
	mkdir -p $dir
	dir=$dir1/bwmng
	mkdir -p $dir
	dir=$out_dir1/SRMF
	sudo mn -c
#	sudo python ./PureSDNPkt/SegmentFattree.py --k $k --dir $dir --fnum $flow_num --miceIndex $miceIndex

	sleep 2
#myNormal
  dir1=$out_dir1/NMF
	dir=$dir1/pingTest
	mkdir -p $dir
	dir=$dir1/bwmng
	mkdir -p $dir
	dir=$out_dir1/NMF
	sudo mn -c
#	sudo python ./PureSDNPkt/SegmentFattree.py --k $k --dir $dir --fnum $flow_num --miceIndex $miceIndex

	# NonBlocking
#	dir=$out_dir/$flowsPerHost/$traffic/NonBlocking
#	mkdir -p $dir
#	mn -c
#	sudo python ./NonBlocking/NonBlocking.py --k $k --duration $duration --dir $dir --cpu $cpu



# Plot results.
#sudo python ./plot_results_Chinese.py --k $k --duration $duration --dir $out_dir --fnum $flowsPerHost
