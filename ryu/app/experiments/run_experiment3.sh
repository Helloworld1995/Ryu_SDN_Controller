#!/bin/bash
# Copyright (C) 2016 Huang MaChi at Chongqing University
# of Posts and Telecommunications, China.

k=$1

flows_num_per_host=$2   # number of iperf flows per host.
duration=$3
#out_dir=$5

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
round="1 2 7 8 9 10"
index="0.1 0.2 0.3 0.4 0.5 0.6 0.7 0.8 0.9"
out_dir=./miceIndex_Result_random2
mkdir -p $out_dir
# Run experiments.
sudo mn -c
for r in $round
  do
  sudo python ./create_link_loss.py
  sleep 1
	# Create iperf peers.
  sudo python ./create_peers.py --k $k --traffic $traffics --fnum $flows_num_per_host
  sleep 1
  dir=$out_dir/$r
  mkdir -p $dir
  for idx in $index
  do
  dir1=$dir/$idx/SRMF
  mkdir -p $dir1
  sleep 1
  sudo python ./PureSDNPkt/SegmentFattree.py --k $k --dir $dir1 --fnum $flows_num_per_host --duration $duration --index $idx --miceIndex 0.7
  done
done

#	# ECMP
#	dir=$out_dir/$flowsPerHost/$traffic/ECMP
#	mkdir -p $dir
#	mn -c
#	sudo python ./ECMP/fattree.py --k $k --duration $duration --dir $dir --cpu $cpu
#
# #PureSDN
#	dir=$out_dir/$flowsPerHost/$traffic/PureSDN
#	mkdir -p $dir
#	mn -c
#	sudo python ./PureSDN/SegmentECMPfattree4.py --k $k --duration $duration --dir $dir --cpu $cpu
#
##Hedera
#	dir=$out_dir/$flowsPerHost/$traffic/Hedera
#	mkdir -p $dir
#	mn -c
#	sudo python ./Hedera/fattree4.py --k $k --duration $duration --dir $dir --cpu $cpu
#	# NonBlocking
##	dir=$out_dir/$flowsPerHost/$traffic/NonBlocking
##	mkdir -p $dir
##	mn -c
##	sudo python ./NonBlocking/NonBlocking.py --k $k --duration $duration --dir $dir --cpu $cpu
#
#done
#
## Plot results.
#sudo python ./plot_results_Chinese.py --k $k --duration $duration --dir $out_dir --fnum $flowsPerHost
