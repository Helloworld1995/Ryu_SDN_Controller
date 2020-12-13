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
flows_num_per_host="64"
round="1 2 3 4 5 6 7 8 9 10"
#flows_num_per_host="160"
# Output directory.
#dir="./results1 ./results2 ./results3 ./results4 ./results5 ./results6 ./results7 ./results8 ./results9 ./results10"
out_dir=./compare_miceIndex1
rm -f -r $out_dir
mkdir -p $out_dir
# shellcheck disable=SC1073
for r in $round
do
  outdir=$out_dir/$r
#  rm -f -r $outdir
  sudo mkdir -p $outdir

# Run experiments.
#for traffic in $traffics
  for flow_num in $flows_num_per_host
  do
# Create iperf peers.
  sudo python ./MyCreatePeers.py --k $k --traffic $traffics --fnum $flow_num
  sleep 1
  ./experiment_run_compare1.sh $k $flow_num $outdir

	# # BFlows
#	dir=$out_dir/$traffic/BFlows
#	mkdir -p $dir
#	mn -c
#	sudo python ./BFlows/fattree.py --k $k --duration $duration --dir $dir --cpu $cpu
done
done