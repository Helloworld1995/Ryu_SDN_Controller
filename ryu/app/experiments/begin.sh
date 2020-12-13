#!/bin/bash
# Copyright (C) 2016 Huang MaChi at Chongqing University
# of Posts and Telecommunications, China.
k=$1
#cpu=$2
#flows_num_per_host=$3   # number of iperf flows per host.
#duration=$4
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
traffics="random"
flows_num_per_host="10 20 30 40 50 60 70 80 90 100 110 120 130 140 150 160 170 180 190 200"
#flows_num_per_host="160"
# Output directory.
#dir="./results1 ./results2 ./results3 ./results4 ./results5 ./results6 ./results7 ./results8 ./results9 ./results10"
dir="./results8"
# shellcheck disable=SC1073
for outdir in $dir
do
  out_dir=$outdir
#  rm -f -r $outdir
#  mkdir -p $outdir
# Run experiments.
#for traffic in $traffics
  for flow_num in $flows_num_per_host
  do
# Create iperf peers.
  sudo python ./MyCreatePeers.py --k $k --traffic $traffics --fnum $flow_num
  sleep 3
 ./run_experiment2.sh $k $flow_num $out_dir
	# # BFlows
#	dir=$out_dir/$traffic/BFlows
#	mkdir -p $dir
#	mn -c
#	sudo python ./BFlows/fattree.py --k $k --duration $duration --dir $dir --cpu $cpu
done
done