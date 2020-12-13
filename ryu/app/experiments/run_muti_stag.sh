#!/bin/bash
# Copyright (C) 2016 Huang MaChi at Chongqing University
# of Posts and Telecommunications, China.

k=$1
#cpu=$2
flows_num_per_host=$2   # number of iperf flows per host.
duration=$3

# Exit on any failure.
set -e

# Check for uninitialized variables.
set -o nounset

ctrlc() {
	killall -9 python
	killall -9 ryu-manager
	mn -c
	exit
}

trap ctrlc INT

# Traffic patterns.
# "stag_0.2_0.3" means 20% under the same Edge switch,
# 30% between different Edge switches in the same Pod,
# and 50% between different Pods.
# "random" means choosing the iperf server randomly.
# Change it if needed.
#traffics="random7 random8 random9
#stag1_0.1_0.2 stag2_0.1_0.2 stag3_0.1_0.2 stag4_0.1_0.2 stag5_0.1_0.2 stag6_0.1_0.2 stag7_0.1_0.2 stag8_0.1_0.2 stag9_0.1_0.2 stag10_0.1_0.2
#stag1_0.2_0.3 stag2_0.2_0.3 stag3_0.2_0.3 stag4_0.2_0.3 stag5_0.2_0.3 stag6_0.2_0.3 stag7_0.2_0.3 stag8_0.2_0.3 stag9_0.2_0.3 stag10_0.2_0.3
#stag1_0.3_0.3 stag2_0.3_0.3 stag3_0.3_0.3 stag4_0.3_0.3 stag5_0.3_0.3 stag6_0.3_0.3 stag7_0.3_0.3 stag8_0.3_0.3 stag9_0.3_0.3 stag10_0.3_0.3
#stag1_0.4_0.3 stag2_0.4_0.3 stag3_0.4_0.3 stag4_0.4_0.3 stag5_0.4_0.3 stag6_0.4_0.3 stag7_0.4_0.3 stag8_0.4_0.3 stag9_0.4_0.3 stag10_0.4_0.3
#stag1_0.5_0.3 stag2_0.5_0.3 stag3_0.5_0.3 stag4_0.5_0.3 stag5_0.5_0.3 stag6_0.5_0.3 stag7_0.5_0.3 stag8_0.5_0.3 stag9_0.5_0.3 stag10_0.5_0.3
#stag1_0.6_0.2 stag2_0.6_0.2 stag3_0.6_0.2 stag4_0.6_0.2 stag5_0.6_0.2 stag6_0.6_0.2 stag7_0.6_0.2 stag8_0.6_0.2 stag9_0.6_0.2 stag10_0.6_0.2
#stag1_0.7_0.2 stag2_0.7_0.2 stag3_0.7_0.2 stag4_0.7_0.2 stag5_0.7_0.2 stag6_0.7_0.2 stag7_0.7_0.2 stag8_0.7_0.2 stag9_0.7_0.2 stag10_0.7_0.2
#stag1_0.8_0.1 stag2_0.8_0.1 stag3_0.8_0.1 stag4_0.8_0.1 stag5_0.8_0.1 stag6_0.8_0.1 stag7_0.8_0.1 stag8_0.8_0.1 stag9_0.8_0.1 stag10_0.8_0.1"

#traffics="random stag1_0.1_0.2 stag1_0.2_0.3 stag1_0.4_0.3 stag1_0.5_0.3 stag1_0.6_0.2 stag1_0.7_0.2 stag1_0.8_0.1"
traffics="stag1_0.8_0.1"
#traffics="stag1_0.8_0.1"

#stag1_0.3_0.3 stag2_0.3_0.3 stag3_0.3_0.3 stag4_0.3_0.3 stag5_0.3_0.3 stag6_0.3_0.3 stag7_0.3_0.3 stag8_0.3_0.3 stag9_0.3_0.3 stag10_0.3_0.3
#stag1_0.4_0.3 stag2_0.4_0.3 stag3_0.4_0.3 stag4_0.4_0.3 stag5_0.4_0.3 stag6_0.4_0.3 stag7_0.4_0.3 stag8_0.4_0.3 stag9_0.4_0.3 stag10_0.4_0.3
#stag1_0.5_0.3 stag2_0.5_0.3 stag3_0.5_0.3 stag4_0.5_0.3 stag5_0.5_0.3 stag6_0.5_0.3 stag7_0.5_0.3 stag8_0.5_0.3 stag9_0.5_0.3 stag10_0.5_0.3
#stag1_0.6_0.2 stag2_0.6_0.2 stag3_0.6_0.2 stag4_0.6_0.2 stag5_0.6_0.2 stag6_0.6_0.2 stag7_0.6_0.2 stag8_0.6_0.2 stag9_0.6_0.2 stag10_0.6_0.2
#stag1_0.7_0.2 stag2_0.7_0.2 stag3_0.7_0.2 stag4_0.7_0.2 stag5_0.7_0.2 stag6_0.7_0.2 stag7_0.7_0.2 stag8_0.7_0.2 stag9_0.7_0.2 stag10_0.7_0.2
#stag1_0.8_0.1 stag2_0.8_0.1 stag3_0.8_0.1 stag4_0.8_0.1 stag5_0.8_0.1 stag6_0.8_0.1 stag7_0.8_0.1 stag8_0.8_0.1 stag9_0.8_0.1 stag10_0.8_0.1"
#traffics="stag6_0.7_0.2"
# Output directory.
out_dir=./RESULTS02
#rm -f -r $out_dir
#mkdir -p $out_dir
round="1"
# Run experiments.
  mkdir -p $out_dir
  for r in $round
  do
    out_dir1=$out_dir/$r
    mkdir -p $out_dir1
    sudo python ./create_link_loss.py
    sleep 2
for traffic in $traffics
do

	# Create iperf peers.
	sudo python ./create_stag_peers.py --k $k --traffic $traffic --fnum $flows_num_per_host
	sleep 5
	#NMF
	dir=$out_dir1/$traffic/NMF
	mkdir -p $dir
	mn -c
  sudo python ./PureSDNPkt/NormalFattree.py --k $k --dir $dir --fnum $flows_num_per_host

  sleep 5
	#SRMF
	dir=$out_dir1/$traffic/SRMF
	mkdir -p $dir
	mn -c
	sudo python ./PureSDNPkt/SegmentFattree.py --k $k --dir $dir --fnum $flows_num_per_host

	sleep 5

	#Hedera
	dir=$out_dir1/$traffic/Hedera
	mkdir -p $dir
  mn -c
	sudo python ./Hedera/fattree4.py --k $k --duration $duration --dir $dir
  sleep 5

  #ECMP

  dir=$out_dir1/$traffic/ECMP
  mkdir -p $dir
  mn -c
  sudo mn -c
	sudo python ./ECMP/fattree.py --k $k --duration $duration --dir $dir
  sleep 5
	# # BFlows
#	dir=$out_dir/$traffic/BFlows
#	mkdir -p $dir
#	mn -c
#	sudo python ./BFlows/fattree.py --k $k --duration $duration --dir $dir --cpu $cpu



done
done
