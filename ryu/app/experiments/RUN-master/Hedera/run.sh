k=4
cpu=0.2
flows_num_per_host=$3   # number of iperf flows per host.
duration=30

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
# Output directory.
dir=~/ryu/ryu/app/Hedera/results
rm -f -r ./results
mkdir -p $dir
sudo python ./fattree.py --k $k --cpu $cpu --duration $duration --dir $dir

