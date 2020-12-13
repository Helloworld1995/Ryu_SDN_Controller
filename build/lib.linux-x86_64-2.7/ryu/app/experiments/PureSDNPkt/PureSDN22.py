# Copyright (C) 2016 Huang MaChi at Chongqing University
# of Posts and Telecommunications, Chongqing, China.
# Copyright (C) 2016 Li Cheng at Beijing University of Posts
# and Telecommunications. www.muzixing.com
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

from ryu import cfg
from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import MAIN_DISPATCHER, DEAD_DISPATCHER
from ryu.controller.handler import set_ev_cls
from ryu.ofproto import ofproto_v1_3
from ryu.lib.packet import packet
from ryu.lib.packet import ethernet
from ryu.lib.packet import arp
from ryu.lib.packet import ipv4
from ryu.lib.packet import tcp
from ryu.lib.packet import udp
from threading import Thread
import copy
import time
from operator import attrgetter
import GA_compute
from ryu import cfg
from ryu.base import app_manager
from ryu.base.app_manager import lookup_service_brick
from ryu.controller import ofp_event
from ryu.controller.handler import MAIN_DISPATCHER, DEAD_DISPATCHER
from ryu.controller.handler import set_ev_cls
from ryu.ofproto import ofproto_v1_3
from ryu.lib import hub
from DemandEstimation import demand_estimation
from GA_test import GaProcessor
from ryu.lib.packet import ethernet
from SRrouting import ShortestForwarding
CONF = cfg.CONF
import network_awareness
import setting
import networkx as nx

CONF = cfg.CONF


class ShortestForwarding(app_manager.RyuApp):
	"""
		ShortestForwarding is a Ryu app for forwarding packets on shortest path.
		This App does not defined the path computation method.
		To get shortest path, this module depends on network awareness and
		network monitor modules.
	"""

	OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]
	_CONTEXTS = {
		"network_awareness": network_awareness.NetworkAwareness,
		}

	WEIGHT_MODEL = {'hop': 'weight','bw':'bw'}

	def __init__(self, *args, **kwargs):
		super(ShortestForwarding, self).__init__(*args, **kwargs)
		self.name = "shortest_forwarding"
		self.awareness = kwargs["network_awareness"]
		self.datapaths = {}
		self.seletPathIndex=0
		self.weight = self.WEIGHT_MODEL[CONF.weight]
		self.newComingFlows={}
		self.datapaths = {}
		self.port_stats = {}
		self.port_speed = {}
		self.flow_stats = {}
		self.pre_GFF_path = {}
		self.flow_speed = {}
		self.stats = {}
		self.flow_index = []
		self.select = {}
		self.congested = False
		self.flows_len = 0
		self.flows = {}
		self.traffics = {}
		self.hostsList = []
		self.port_features = {}
		self.free_bandwidth = {}  # self.free_bandwidth = {dpid:{port_no:free_bw,},} unit:Kbit/s
		self.current_free_bandwidth = {}
		self.current_dectect_dp = {}
		self.awareness = lookup_service_brick('awareness')
		# self.shortest_forwarding = lookup_service_brick('shortest_forwarding')
		self.graph = None
		self.capabilities = None
		self.best_paths = None
		self.k = 0
		self.gp = GaProcessor()
		self.paths = {}
		# Start to green thread to monitor traffic and calculating
		# free bandwidth of links respectively.
		self.monitor_thread = hub.spawn(self._monitor)


	@set_ev_cls(ofp_event.EventOFPStateChange, [MAIN_DISPATCHER, DEAD_DISPATCHER])
	def _state_change_handler(self, ev):
		"""
			Collect datapath information.
		"""
		datapath = ev.datapath
		if ev.state == MAIN_DISPATCHER:
			if not datapath.id in self.datapaths:
				self.logger.debug('register datapath: %016x', datapath.id)
				self.datapaths[datapath.id] = datapath
		elif ev.state == DEAD_DISPATCHER:
			if datapath.id in self.datapaths:
				self.logger.debug('unregister datapath: %016x', datapath.id)
				del self.datapaths[datapath.id]
	def _monitor(self):
		"""
			Main entry method of monitoring traffic.
		"""
		while CONF.weight == 'bw' or CONF.weight=='hop':
			self.stats['flow'] = {}
			self.stats['port'] = {}
			self.current_dectect_dp=[]
			self.statRecord = []
			self.flows = {}
			print len(self.newComingFlows)
			# self.traffics={}
			self.congested=False
			for dp in self.datapaths.values():
				self.port_features.setdefault(dp.id, {})
				self._request_stats(dp)
			# Refresh data.
			self.capabilities = None
			self.best_paths = None
			self.create_bw_graph(self.free_bandwidth)
			hub.sleep(setting.MONITOR_PERIOD)
			if self.stats['flow'] or self.stats['port']:
				self.show_stat('flow')
				self.show_stat('port')
				hub.sleep(1)

	@set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
	def _packet_in_handler(self, ev):
		'''
			In packet_in handler, we need to learn access_table by ARP and IP packets.
		'''
		msg = ev.msg
		pkt = packet.Packet(msg.data)

		arp_pkt = pkt.get_protocol(arp.arp)
		ip_pkt = pkt.get_protocol(ipv4.ipv4)

		if isinstance(arp_pkt, arp.arp):
			self.logger.debug("ARP processing")
			self.arp_forwarding(msg, arp_pkt.src_ip, arp_pkt.dst_ip)

		if isinstance(ip_pkt, ipv4.ipv4):

			self.logger.debug("IPV4 processing")
			if len(pkt.get_protocols(ethernet.ethernet)):
				eth_type = pkt.get_protocols(ethernet.ethernet)[0].ethertype
				self.shortest_forwarding(msg, eth_type, ip_pkt.src, ip_pkt.dst)

	@set_ev_cls(ofp_event.EventOFPFlowStatsReply, MAIN_DISPATCHER)
	def _flow_stats_reply_handler(self, ev):
		"""
                Save flow stats reply information into self.flow_stats.
                Calculate flow speed and Save it.
                (old) self.flow_stats = {dpid:{(in_port, ipv4_dst, out-port):[(packet_count, byte_count, duration_sec,  duration_nsec),],},}
                (old) self.flow_speed = {dpid:{(in_port, ipv4_dst, out-port):[speed,],},}
                (new) self.flow_stats = {dpid:{(priority, ipv4_src, ipv4_dst):[(packet_count, byte_count, duration_sec,  duration_nsec),],},}
                (new) self.flow_speed = {dpid:{(priority, ipv4_src, ipv4_dst):[speed,],},}
                Because the proactive flow entrys don't have 'in_port' and 'out-port' field.
                Note: table-miss, LLDP and ARP flow entries are not what we need, just filter them.
            """
		body = ev.msg.body
		dpid = ev.msg.datapath.id
		self.statRecord.append(dpid)
		self.stats['flow'][dpid] = body
		self.flow_stats.setdefault(dpid, {})
		self.flow_speed.setdefault(dpid, {})
		for stat in sorted([flow for flow in body if (
				(flow.priority not in [0, 10, 65535]) and (flow.match.get('ipv4_src')) and (flow.match.get('ipv4_dst')))],
						   key=lambda flow: (flow.priority, flow.match.get('ipv4_src'), flow.match.get('ipv4_dst'))):
			src = stat.match['ipv4_src']
			dst = stat.match['ipv4_dst']
			for f in self.newComingFlows.keys():
				if f[0] == src and f[1] == dst:
					swPair = self.newComingFlows.get(f)
					key = (stat.priority, src, dst)
					value = (stat.packet_count, stat.byte_count,
							 stat.duration_sec, stat.duration_nsec)
					self._save_stats(self.flow_stats[dpid], key, value, 5)
					# Get flow's speed and Save it.
					pre = 0
					period = setting.MONITOR_PERIOD
					tmp = self.flow_stats[dpid][key]
					if len(tmp) > 1:
						pre = tmp[-2][1]
						period = self._get_period(tmp[-1][2], tmp[-1][3], tmp[-2][2], tmp[-2][3])
					speed = self._get_speed(self.flow_stats[dpid][key][-1][1], pre, period)
					self._save_stats(self.flow_speed[dpid], key, speed, 5)
					# Record flows thatport need to be rescheduled. (hmc)
					flowDemand = speed * 8.0 / (setting.MAX_CAPACITY * 1024)
					if flowDemand > 0.0:
						# if src not in self.hostsList:
						# 	self.hostsList.append(src)
						# if dst not in self.hostsList:
						# 	self.hostsList.append(dst)
						self.flows[key] = {'src': src, 'dst': dst, 'speed': speed, 'match':stat.match,'priority': stat.priority,
										   'swPair': swPair}
				# if not self.pre_GFF_path.has_key((src, dst)):
				# 	self.pre_GFF_path[(src, dst)] = None
		# Estimate flows' demands if all the flow_stat replies are received.
		if len(self.statRecord) == 8 and self.flows:
			#  #clear the new coming flows avoid impacting next round rerouting
			flows = sorted([flow for flow in self.flows.values()], key=lambda flow: (flow['src'], flow['dst']))
			# hostsList = sorted(self.hostsList)
			# self._demandEstimator(flows, hostsList)
			# if self.congested==1:
			print("it is time to reroute!")
			# self._demandEstimator(flows,hostsList)
			self._reroute(flows)
			self.newComingFlows.clear()
		else:
			pass

	def _demandEstimator(self, flows, hostsList):
		estimated_flows = demand_estimation(flows, hostsList)
		self._reroute(estimated_flows)

	def _reroute(self, flows):

		# estimated_flows = demand_estimation(flows, hostsList)
		self.traffics = {}
		count = 0
		j = 0
		route_list = []
		for flow in flows:
			self.paths[flow['swPair']] = self._ip2sw(flow['swPair'])
			print self.paths
			self.traffics[count] = flow
			count = count + 1
		currentFlows = self.traffics
		flow_len = len(currentFlows)
		if flow_len > 1:
			start = time.time()
			route_list = GA_compute._GA_start(flow_len)
			end = time.time()
			print("computing time " + str(end - start))
		if route_list != []:
			for k in route_list:
				flow = currentFlows[j]
				j = j + 1
				core = 1001 + k % 4
				Thread(target=self._GlobalFirstFit, args=(flow, core)).start()
	def _ip2sw(self, swPair):
		src_dp = swPair[0]
		dst_dp = swPair[1]
		paths = self.awareness.shortest_paths.get(src_dp).get(dst_dp)
		return paths
	def swToSegments(self,path):
		datapaths=self.datapaths
		link_to_port=self.awareness.link_to_port
		first_dp = datapaths[path[0]]
		portList = []  # it includes all push mpls labels of the path
		Pathlen = len(path)
		if Pathlen == '':
			self.logger.info("Path error!")
			return
		port_pair = self.get_port_pair_from_link(link_to_port, path[0], path[1])
		if port_pair is None:
			self.logger.info("Port not found in first hop.")
			return
		first_output = port_pair[0]
		portList.append(first_output)
		for i in xrange(1, Pathlen - 1):
			port_next = self.get_port_pair_from_link(link_to_port, path[i], path[i + 1])
			if port_next:
				port = port_next[0]
				portList.append(port)
		return first_dp,portList
	def _GlobalFirstFit(self,flow,core):
		'''
			Do the Hedera Global First Fit here.
			self.awareness.link_to_port = {(src_dpid,dst_dpid):(src_port,dst_port),}
			self.free_bandwidth = {dpid:{port_no:free_bw,},} Unit:Kbit/s
		'''
		swPair=flow['swPair']
		paths=self.paths.get(swPair)
		if paths==None:
			paths=self._ip2sw(swPair)
		for path in paths:
			if path[int((len(path) - 1) / 2)] == core:
				bucket=self.swToSegments(path)
				self._install_GFF_path(bucket, flow['match'], flow['priority'])

	def _install_GFF_path(self, bucket, match, priority):
		'''
			Installing the Global First Fit path.
			"match": {"dl_type": 2048, "in_port": 3,
						"ipv4_src": "10.1.0.1", "ipv4_dst": "10.8.0.2"}
			flow_info = (eth_type, src_ip, dst_ip, priority)
		'''
		flow_info = (match['eth_type'], match['ipv4_src'], match['ipv4_dst'], priority)
		self.Segment_forwarding(flow_info,bucket)
		# Install flow entries to datapaths along the path.
	def add_flow(self, dp, priority, match, actions, idle_timeout=0, hard_timeout=0):
		"""
			Send a flow entry to datapath.
		"""
		ofproto = dp.ofproto
		parser = dp.ofproto_parser
		inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS, actions)]
		mod = parser.OFPFlowMod(datapath=dp, priority=priority,
								idle_timeout=idle_timeout,
								hard_timeout=hard_timeout,
								match=match, instructions=inst)
		dp.send_msg(mod)

	@set_ev_cls(ofp_event.EventOFPFlowRemoved, MAIN_DISPATCHER)
	def flow_removed_handler(self, ev):
		msg = ev.msg
		dp = msg.datapath
		ofp = dp.ofproto
		ip_src = msg.match.get("ipv4_src")
		ip_dst = msg.match.get("ipv4_dst")
		if self.newComingFlows!={}:
			self.newComingFlows.pop((ip_src,ip_dst))

	def _build_packet_out(self, datapath, buffer_id, src_port, dst_port, data):
			"""
				Build packet out object.
			"""
			actions = []
			if dst_port:
				actions.append(datapath.ofproto_parser.OFPActionOutput(dst_port))

			msg_data = None
			if buffer_id == datapath.ofproto.OFP_NO_BUFFER:
				if data is None:
					return None
				msg_data = data

			out = datapath.ofproto_parser.OFPPacketOut(
				datapath=datapath, buffer_id=buffer_id,
				data=msg_data, in_port=src_port, actions=actions)
			return out
	def get_port_pair_from_link(self, link_to_port, src_dpid, dst_dpid):
		"""
			Get port pair of link, so that controller can install flow entry.
			link_to_port = {(src_dpid,dst_dpid):(src_port,dst_port),}
		"""
		if (src_dpid, dst_dpid) in link_to_port:
			return link_to_port[(src_dpid, dst_dpid)]
		else:
			self.logger.info("Link from dpid:%s to dpid:%s is not in links" %
			 (src_dpid, dst_dpid))
			return None

	@set_ev_cls(ofp_event.EventOFPPortStatsReply, MAIN_DISPATCHER)
	def _port_stats_reply_handler(self, ev):
		"""
			Save port's stats information into self.port_stats.
			Calculate port speed and Save it.
			self.port_stats = {(dpid, port_no):[(tx_bytes, rx_bytes, rx_errors, duration_sec,  duration_nsec),],}
			self.port_speed = {(dpid, port_no):[speed,],}
			Note: The transmit performance and receive performance are independent of a port.
			We calculate the load of a port only using tx_bytes.
		"""
		body = ev.msg.body
		dpid = ev.msg.datapath.id
		self.current_dectect_dp.append(dpid)
		self.stats['port'][dpid] = body
		self.current_free_bandwidth.setdefault(dpid,{})
		self.free_bandwidth.setdefault(dpid, {})
		for stat in sorted(body, key=attrgetter('port_no')):
			port_no = stat.port_no
			print stat
			if port_no != ofproto_v1_3.OFPP_LOCAL:
				key = (dpid, port_no)
				value = (stat.tx_bytes, stat.rx_bytes, stat.rx_errors,
						 stat.duration_sec, stat.duration_nsec)
				self._save_stats(self.port_stats, key, value, 5)
				# Get port speed and Save it.
				pre = 0
				period = setting.MONITOR_PERIOD
				tmp = self.port_stats[key]
				if len(tmp) > 1:
					# Calculate only the tx_bytes, not the rx_bytes. (hmc)
					pre = tmp[-2][0]
					period = self._get_period(tmp[-1][3], tmp[-1][4], tmp[-2][3], tmp[-2][4])
				speed = self._get_speed(self.port_stats[key][-1][0], pre, period)
				self._save_stats(self.port_speed, key, speed, 5)
				self._save_freebandwidth(dpid, port_no, speed)
	def get_sw(self, dpid, in_port, src, dst):
		"""
			Get pair of source and destination switches.
		"""
		src_sw = dpid
		dst_sw = None
		src_location = self.awareness.get_host_location(src)   # src_location = (dpid, port)
		if in_port in self.awareness.access_ports[dpid]:
			if (dpid, in_port) == src_location:
				src_sw = src_location[0]
			else:
				return None
		dst_location = self.awareness.get_host_location(dst)   # dst_location = (dpid, port)
		if dst_location:
			dst_sw = dst_location[0]
		if src_sw and dst_sw:
			return src_sw, dst_sw
		else:
			return None

	@set_ev_cls(ofp_event.EventOFPPortDescStatsReply, MAIN_DISPATCHER)
	def port_desc_stats_reply_handler(self, ev):
		"""
			Save port description info.
		"""
		msg = ev.msg
		dpid = msg.datapath.id
		ofproto = msg.datapath.ofproto

		config_dict = {ofproto.OFPPC_PORT_DOWN: "Down",
					   ofproto.OFPPC_NO_RECV: "No Recv",
					   ofproto.OFPPC_NO_FWD: "No Farward",
					   ofproto.OFPPC_NO_PACKET_IN: "No Packet-in"}

		state_dict = {ofproto.OFPPS_LINK_DOWN: "Down",
					  ofproto.OFPPS_BLOCKED: "Blocked",
					  ofproto.OFPPS_LIVE: "Live"}

		ports = []
		for p in ev.msg.body:
			ports.append('port_no=%d hw_addr=%s name=%s config=0x%08x '
						 'state=0x%08x curr=0x%08x advertised=0x%08x '
						 'supported=0x%08x peer=0x%08x curr_speed=%d '
						 'max_speed=%d' %
						 (p.port_no, p.hw_addr,
						  p.name, p.config,
						  p.state, p.curr, p.advertised,
						  p.supported, p.peer, p.curr_speed,
						  p.max_speed))

			if p.config in config_dict:
				config = config_dict[p.config]
			else:
				config = "up"

			if p.state in state_dict:
				state = state_dict[p.state]
			else:
				state = "up"

			# Recording data.
			port_feature = (config, state, p.curr_speed)
			self.port_features[dpid][p.port_no] = port_feature

	@set_ev_cls(ofp_event.EventOFPPortStatus, MAIN_DISPATCHER)
	def _port_status_handler(self, ev):
		"""
			Handle the port status changed event.
		"""
		msg = ev.msg
		ofproto = msg.datapath.ofproto
		reason = msg.reason
		dpid = msg.datapath.id
		port_no = msg.desc.port_no

		reason_dict = {ofproto.OFPPR_ADD: "added",
					   ofproto.OFPPR_DELETE: "deleted",
					   ofproto.OFPPR_MODIFY: "modified", }

		if reason in reason_dict:
			print "switch%d: port %s %s" % (dpid, reason_dict[reason], port_no)
		else:
			print "switch%d: Illeagal port state %s %s" % (dpid, port_no, reason)

	def _request_stats(self, datapath):
		"""
			Sending request msg to datapath
		"""
		self.logger.debug('send stats request: %016x', datapath.id)
		ofproto = datapath.ofproto
		parser = datapath.ofproto_parser
		req = parser.OFPPortDescStatsRequest(datapath, 0)
		datapath.send_msg(req)
		if(str(datapath.id).startswith('3')):
			req = parser.OFPFlowStatsRequest(datapath)
			datapath.send_msg(req)
		req = parser.OFPPortStatsRequest(datapath, 0, ofproto.OFPP_ANY)
		datapath.send_msg(req)

	def get_min_bw_of_links(self, graph, path, min_bw):
		"""
			Getting bandwidth of path. Actually, the mininum bandwidth
			of links is the path's bandwith, because it is the bottleneck of path.
		"""
		_len = len(path)
		if _len > 1:
			minimal_band_width = min_bw
			for i in xrange(_len-1):
				pre, curr = path[i], path[i+1]
				if 'bandwidth' in graph[pre][curr]:
					bw = graph[pre][curr]['bandwidth']
					minimal_band_width = min(bw, minimal_band_width)
				else:
					continue
			return minimal_band_width
		else:
			return min_bw

	def get_best_path_by_bw(self, graph, paths):
		"""
			Get best path by comparing paths.
			Note: This function is called in EFattree module.
		"""
		capabilities = {}
		best_paths = copy.deepcopy(paths)

		for src in paths:
			for dst in paths[src]:
				if src == dst:
					best_paths[src][src] = [src]
					capabilities.setdefault(src, {src: setting.MAX_CAPACITY})
					capabilities[src][src] = setting.MAX_CAPACITY
				else:
					max_bw_of_paths = 0
					best_path = paths[src][dst][0]
					for path in paths[src][dst]:
						min_bw = setting.MAX_CAPACITY
						min_bw = self.get_min_bw_of_links(graph, path, min_bw)
						if min_bw > max_bw_of_paths:
							max_bw_of_paths = min_bw
							best_path = path
					best_paths[src][dst] = best_path
					capabilities.setdefault(src, {dst: max_bw_of_paths})
					capabilities[src][dst] = max_bw_of_paths

		# self.capabilities and self.best_paths have no actual utility in this module.
		self.capabilities = capabilities
		self.best_paths = best_paths
		return capabilities, best_paths
	def create_static_bw_graph(self):
		"""
			Save bandwidth data into networkx graph object.
		"""
		try:
			graph = self.awareness.graph
			for link in graph.edges():
				node1=link[0]
				node2=link[1]
				graph[node1][node2]['bandwidth']=setting.MAX_CAPACITY*1024
			return graph
		except:
			self.logger.info("Create bw graph exception")
			if self.awareness is None:
				self.awareness = lookup_service_brick('awareness')
			return self.awareness.graph
	def create_bw_graph(self, bw_dict):
		"""
			Save bandwidth data into networkx graph object.
		"""
		try:
			graph = self.awareness.graph
			link_to_port = self.awareness.link_to_port
			for link in link_to_port:
				(src_dpid, dst_dpid) = link
				(src_port, dst_port) = link_to_port[link]
				if src_dpid in bw_dict and dst_dpid in bw_dict:
					bandwidth = bw_dict[src_dpid][src_port]
					# Add key:value pair of bandwidth into graph.
					if graph.has_edge(src_dpid, dst_dpid):
						# graph[src_dpid][dst_dpid]['bandwidth'] = setting.MAX_CAPACITY
						graph[src_dpid][dst_dpid]['bandwidth'] = bandwidth
					# else:
					# 	graph.add_edge(src_dpid, dst_dpid)
					# 	graph[src_dpid][dst_dpid]['bandwidth'] = bandwidth
				else:
					if graph.has_edge(src_dpid, dst_dpid):
						graph[src_dpid][dst_dpid]['bandwidth'] = setting.MAX_CAPACITY
					# else:
					# 	graph.add_edge(src_dpid, dst_dpid)
					# 	graph[src_dpid][dst_dpid]['bandwidth'] = setting.MAX_CAPACITY
			return graph
		except:
			self.logger.info("Create bw graph exception")
			if self.awareness is None:
				self.awareness = lookup_service_brick('awareness')
			return self.awareness.graph

	def _save_freebandwidth(self, dpid, port_no, speed):
		"""
			Calculate free bandwidth of port and Save it.
			port_feature = (config, state, p.curr_speed)
			self.port_features[dpid][p.port_no] = port_feature
			self.free_bandwidth = {dpid:{port_no:free_bw,},}
		"""
		port_state = self.port_features.get(dpid).get(port_no)
		if port_state:
			capacity = setting.MAX_CAPACITY   # The true bandwidth of link, instead of 'curr_speed'.
			free_bw = self._get_free_bw(capacity, speed)
			if free_bw==0:
				self.congested=True
			self.free_bandwidth[dpid].setdefault(port_no, None)
			self.free_bandwidth[dpid][port_no] = free_bw
		else:
			self.logger.info("Port is Down")

	def _save_stats(self, _dict, key, value, length=5):
		if key not in _dict:
			_dict[key] = []
		_dict[key].append(value)
		if len(_dict[key]) > length:
			_dict[key].pop(0)

	def _get_speed(self, now, pre, period):
		if period:
			return (now - pre) / (period)
		else:
			return 0

	def _get_free_bw(self, capacity, speed):
		# freebw: Kbit/s
		return max(capacity - speed * 8 / 1000.0, 0)

	def _get_time(self, sec, nsec):
		return sec + nsec / 1000000000.0

	def _get_period(self, n_sec, n_nsec, p_sec, p_nsec):
		return self._get_time(n_sec, n_nsec) - self._get_time(p_sec, p_nsec)
	def show_topology(self):
		# It means the link_to_port table has changed.
		_graph = self.graph
		print "\n---------------------Link Port---------------------"
		print '%6s' % ('switch'),
		for node in sorted([node for node in _graph.nodes()], key=lambda node: node):
			print '%6d' % node,
		print
		for node1 in sorted([node for node in _graph.nodes()], key=lambda node: node):
			print '%6d' % node1,
			for node2 in sorted([node for node in _graph.nodes()], key=lambda node: node):
				if (node1, node2) in self.awareness.link_to_port.keys():
					print '%6s' % str(self.awareness.link_to_port[(node1, node2)]),
					print('%6s' %str(_graph[node1][node2]['bandwidth']))
				else:
					print '%6s' % '/',
			print
		print
	def show_stat(self, _type):
		'''
			Show statistics information according to data type.
			_type: 'port' / 'flow'
		'''
		if setting.TOSHOW is False:
			return

		bodys = self.stats[_type]
		if _type == 'flow':
			print('\ndatapath  '
				'priority        ip_src        ip_dst  '
				'  packets        bytes  flow-speed(Kb/s)')
			print('--------  '
				'--------  ------------  ------------  '
				'---------  -----------  ----------------')
			for dpid in sorted(bodys.keys()):

				for stat in sorted([flow for flow in bodys[dpid] if ((flow.priority not in [0, 65535]) and (flow.match.get('ipv4_src')) and (flow.match.get('ipv4_dst')))],
						   key=lambda flow: (flow.priority, flow.match.get('ipv4_src'), flow.match.get('ipv4_dst'))):
					print('%8d  %8s  %12s  %12s  %9d  %11d  %16.1f' % (
						dpid,
						stat.priority, stat.match.get('ipv4_src'), stat.match.get('ipv4_dst'),
						stat.packet_count, stat.byte_count,
						abs(self.flow_speed[dpid][(stat.priority, stat.match.get('ipv4_src'), stat.match.get('ipv4_dst'))][-1])*8/1000.0))
			print

		if _type == 'port':
			print('\ndatapath  port '
				'   rx-pkts     rx-bytes ''   tx-pkts     tx-bytes '
				' port-bw(Kb/s)  port-speed(b/s)  port-freebw(Kb/s) '
				' port-state  link-state')
			print('--------  ----  '
				'---------  -----------  ''---------  -----------  '
				'-------------  ---------------  -----------------  '
				'----------  ----------')
			_format = '%8d  %4x  %9d  %11d  %9d  %11d  %13d  %15.1f  %17.1f  %10s  %10s'
			for dpid in sorted(bodys.keys()):
				for stat in sorted(bodys[dpid], key=attrgetter('port_no')):
					if stat.port_no != ofproto_v1_3.OFPP_LOCAL:
						print(_format % (
							dpid, stat.port_no,
							stat.rx_packets, stat.rx_bytes,
							stat.tx_packets, stat.tx_bytes,
							10000,
							abs(self.port_speed[(dpid, stat.port_no)][-1] * 8),
							self.free_bandwidth[dpid][stat.port_no],
							self.port_features[dpid][stat.port_no][0],
							self.port_features[dpid][stat.port_no][1]))
			print
	def send_packet_out(self, datapath, buffer_id, src_port, dst_port, data):
		"""
			Send packet out packet to assigned datapath.
		"""
		out = self._build_packet_out(datapath, buffer_id,
									 src_port, dst_port, data)
		if out:
			datapath.send_msg(out)

	def get_port(self, dst_ip, access_table):
		"""
			Get access port of dst host.
			access_table = {(sw,port):(ip, mac),}
		"""
		if access_table:
			if isinstance(access_table.values()[0], tuple):
				for key in access_table.keys():
					if dst_ip == access_table[key][0]:   # Use the IP address only, not the MAC address. (hmc)
						dst_port = key[1]
						return dst_port
		return None

	def get_port_pair_from_link(self, link_to_port, src_dpid, dst_dpid):
		"""
			Get port pair of link, so that controller can install flow entry.
			link_to_port = {(src_dpid,dst_dpid):(src_port,dst_port),}
		"""
		if (src_dpid, dst_dpid) in link_to_port:
			return link_to_port[(src_dpid, dst_dpid)]
		else:
			self.logger.info("Link from dpid:%s to dpid:%s is not in links" %
			 (src_dpid, dst_dpid))
			return None

	def flood(self, msg):
		"""
			Flood packet to the access ports which have no record of host.
			access_ports = {dpid:set(port_num,),}
			access_table = {(sw,port):(ip, mac),}
		"""
		datapath = msg.datapath
		ofproto = datapath.ofproto

		for dpid in self.awareness.access_ports:
			for port in self.awareness.access_ports[dpid]:
				if (dpid, port) not in self.awareness.access_table.keys():
					datapath = self.datapaths[dpid]
					out = self._build_packet_out(
						datapath, ofproto.OFP_NO_BUFFER,
						ofproto.OFPP_CONTROLLER, port, msg.data)
					datapath.send_msg(out)
		self.logger.debug("Flooding packet to access port")

	def arp_forwarding(self, msg, src_ip, dst_ip):
		"""
			Send ARP packet to the destination host if the dst host record
			is existed, else flow it to the unknow access port.
			result = (datapath, port)
		"""
		datapath = msg.datapath
		ofproto = datapath.ofproto

		result = self.awareness.get_host_location(dst_ip)
		if result:
			# Host has been recorded in access table.
			datapath_dst, out_port = result[0], result[1]
			datapath = self.datapaths[datapath_dst]
			out = self._build_packet_out(datapath, ofproto.OFP_NO_BUFFER,
										 ofproto.OFPP_CONTROLLER,
										 out_port, msg.data)
			datapath.send_msg(out)
			self.logger.debug("Deliver ARP packet to knew host")
		else:
			# Flood is not good.
			self.flood(msg)
	def _news_Segment_forwarding_(self,flow_info,bucket):

		datapath=bucket[0]
		segmentStack=bucket[1]
		ofproto=datapath.ofproto
		parser = datapath.ofproto_parser
		eth_mpls=ethernet.ether.ETH_TYPE_MPLS
		actions = []
		while len(segmentStack)>1:
			mpls_label=segmentStack.pop()
			f_label = datapath.ofproto_parser.OFPMatchField.make(datapath.ofproto.OXM_OF_MPLS_LABEL, mpls_label)
			actions.append(parser.OFPActionPushMpls(eth_mpls))
			actions.append(parser.OFPActionSetField(f_label))
		actions.append(parser.OFPActionOutput(segmentStack.pop(),0))
		inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS, actions)]

		match = parser.OFPMatch(
			eth_type=flow_info[0],ipv4_src=flow_info[1], ipv4_dst=flow_info[2],in_port=flow_info[-1]
		)
		mod = parser.OFPFlowMod(datapath=datapath, priority=25,
								table_id=0,
								idle_timeout=3,
								hard_timeout=0,
								match=match, instructions=inst)
		datapath.send_msg(mod)
	def Segment_forwarding(self,flow_info,bucket):

		datapath=bucket[0]
		segmentStack=bucket[1]
		ofproto=datapath.ofproto
		parser = datapath.ofproto_parser
		eth_mpls=ethernet.ether.ETH_TYPE_MPLS
		actions = []
		while len(segmentStack)>1:
			mpls_label=segmentStack.pop()
			f_label = datapath.ofproto_parser.OFPMatchField.make(datapath.ofproto.OXM_OF_MPLS_LABEL, mpls_label)
			actions.append(parser.OFPActionPushMpls(eth_mpls))
			actions.append(parser.OFPActionSetField(f_label))
		actions.append(parser.OFPActionOutput(segmentStack.pop(),0))
		inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS, actions)]

		match = parser.OFPMatch(
			eth_type=flow_info[0],ipv4_src=flow_info[1], ipv4_dst=flow_info[2]
		)
		mod = parser.OFPFlowMod(datapath=datapath, priority=flow_info[-1]+1,
								table_id=0,
								idle_timeout=2,
								hard_timeout=0,
								match=match, instructions=inst)
		datapath.send_msg(mod)

	def get_path(self, src, dst, weight):
		"""
			Get shortest path from network_awareness module.
			generator (nx.shortest_simple_paths( )) produces
			lists of simple paths, in order from shortest to longest.
		"""
		shortest_paths = self.awareness.shortest_paths
		if self.seletPathIndex==CONF.k_paths:
			self.seletPathIndex=0
		if weight == self.WEIGHT_MODEL['hop']:
			try:
				path= shortest_paths.get(src).get(dst)[self.seletPathIndex]
				self.seletPathIndex += 1
				return path
			except:
				return shortest_paths.get(src).get(dst)[0]


	def get_path2(self, src, dst, weight):
		"""
			Get shortest path from network_awareness module.
			generator (nx.shortest_simple_paths( )) produces
			lists of simple paths, in order from shortest to longest.
		"""
		#shortest_paths = self.awareness.shortest_paths
		# Create bandwidth-sensitive datapath graph.
		if weight == self.WEIGHT_MODEL['hop']:
			graph = self.awareness.graph
			return nx.shortest_path(graph,src,dst,method='dijkstra')

		elif weight == self.WEIGHT_MODEL['bw']:
			graph = self.graph
			path = nx.shortest_path(graph, src, dst, weight='bandwidth', method='dijkstra')
			return path
		else:
			pass
	def get_sw(self, dpid, in_port, src, dst):
		"""
			Get pair of source and destination switches.
		"""
		src_sw = dpid
		dst_sw = None
		src_location = self.awareness.get_host_location(src)   # src_location = (dpid, port)
		if in_port in self.awareness.access_ports[dpid]:
			if (dpid, in_port) == src_location:
				src_sw = src_location[0]
			else:
				return None
		dst_location = self.awareness.get_host_location(dst)   # dst_location = (dpid, port)
		if dst_location:
			dst_sw = dst_location[0]
		if src_sw and dst_sw:
			return src_sw, dst_sw
		else:
			return None

	def send_flow_mod(self, datapath, flow_info, src_port, dst_port):
		"""
			Build flow entry, and send it to datapath.
			flow_info = (eth_type, src_ip, dst_ip, in_port)
			or
			flow_info = (eth_type, src_ip, dst_ip, in_port, ip_proto, Flag, L4_port)
		"""
		parser = datapath.ofproto_parser
		actions = []
		actions.append(parser.OFPActionOutput(dst_port))
		if len(flow_info) == 7:
			if flow_info[-3] == 6:
				if flow_info[-2] == True:
					match = parser.OFPMatch(
						in_port=src_port, eth_type=flow_info[0],
						ipv4_src=flow_info[1], ipv4_dst=flow_info[2],
						ip_proto=6, tcp_src=flow_info[-1][0],tcp_dst=flow_info[-1][1])
				else:
					pass
			elif flow_info[-3] == 17:
				if flow_info[-2] == True:
					match = parser.OFPMatch(
						in_port=src_port, eth_type=flow_info[0],
						ipv4_src=flow_info[1], ipv4_dst=flow_info[2],
						ip_proto=17, udp_src=flow_info[-1][0],udp_dst=flow_info[-1][1])
				else:
					pass
		elif len(flow_info) == 4:
			match = parser.OFPMatch(
				in_port=src_port, eth_type=flow_info[0],
				ipv4_src=flow_info[1], ipv4_dst=flow_info[2])
		else:
			pass

		self.add_flow(datapath, 30, match, actions,
					  idle_timeout=1, hard_timeout=0)

	def install_flow(self, datapaths ,link_to_port, path, flow_info, buffer_id,ip_src, ip_dst,data=None):
		'''
			Install flow entries for datapaths.
			path=[dpid1, dpid2, ...]
			flow_info = (eth_type, src_ip, dst_ip, in_port)
			or
			flow_info = (eth_type, src_ip, dst_ip, in_port, ip_proto, Flag, L4_port)
		'''

		Pathlen=len(path)
		if Pathlen == 0:
			self.logger.info("Path error!")
			return
		in_port = flow_info[3]
		first_dp = datapaths[path[0]]
		port_pair = self.get_port_pair_from_link(link_to_port, path[0], path[1])
		#install flow entry of the second switch to the last switch
		for i in xrange(1, Pathlen-1):
			port = self.get_port_pair_from_link(link_to_port, path[i - 1], path[i])
			if (i < Pathlen-1):
				port_next = self.get_port_pair_from_link(link_to_port, path[i], path[i + 1])
			else:
				port_next=self.awareness.get_host_location(ip_dst)[1]
			if port and port_next:
				src_port=port[1]
				if(i<Pathlen-1):
					dst_port =port_next[0]
				else:
					dst_port=port_next

				datapath = datapaths[path[i]]
				self.send_flow_mod(datapath, flow_info, src_port, dst_port)

		# if Pathlen>2:
		# 	for i in xrange(1, Pathlen-1):
		# 		port = self.get_port_pair_from_link(link_to_port, path[i-1], path[i])
		# 		port_next = self.get_port_pair_from_link(link_to_port, path[i], path[i+1])
		#
		# 		if port and port_next:
		# 			src_port, dst_port = port[1], port_next[0]
		# 			final_output=port_next[1]
		# 			datapath = datapaths[path[i]]
		# 			self.send_flow_mod(datapath, flow_info, src_port, dst_port)
		#
		#
		# 	last_in_port = final_output
		#
		# else:
		# 	last_in_port=port_pair[1]
		#
		# #  Install flow entry for the last datapath.
		#
		#
		# if last_in_port is None:
		# 	return
		# self.send_flow_mod(last_dp,flow_info,last_in_port,last_out_port)


		#  Install flow entry for the first datapath.

		if port_pair is None:
			self.logger.info("Port not found in first hop.")
			return
		out_port = port_pair[0]
		self.send_flow_mod(first_dp, flow_info, in_port, out_port)
		# Send packet_out to the first datapath.
		self.send_packet_out(first_dp, buffer_id, in_port, out_port, data)
		if(len(path)==Pathlen):
			self.logger.info("[PATH]%s<-->%s: %s" % (ip_src, ip_dst, path))

	def get_L4_info(self, tcp_pkt, udp_pkt):
		"""
			Get ip_proto and L4 port number.
		"""
		ip_proto = None
		L4_port = None
		Flag = None
		if tcp_pkt:
			ip_proto = 6
			if tcp_pkt.src_port and tcp_pkt.dst_port:
				L4_port = tcp_pkt.src_port,tcp_pkt.dst_port
				Flag = True
			else:
				Flag=False

		elif udp_pkt:
			ip_proto = 17
			if udp_pkt.src_port and udp_pkt.dst_port:
				L4_port = udp_pkt.src_port,udp_pkt.dst_port
				Flag = True
			else:
				Flag=False

		else:
			pass
		return (ip_proto, L4_port, Flag)

	def shortest_forwarding(self, msg, eth_type, ip_src, ip_dst):
		"""
			Calculate shortest forwarding path and Install them into datapaths.
			flow_info = (eth_type, ip_src, ip_dst, in_port)
			or
			flow_info = (eth_type, ip_src, ip_dst, in_port, ip_proto, Flag, L4_port)
		"""
		datapath = msg.datapath
		in_port = msg.match['in_port']
		pkt = packet.Packet(msg.data)
		tcp_pkt = pkt.get_protocol(tcp.tcp)
		udp_pkt = pkt.get_protocol(udp.udp)
		ip_proto = None
		L4_port = None
		Flag = None
		# Get ip_proto and L4 port number.
		result = self.get_sw(datapath.id, in_port, ip_src, ip_dst)  # result = (src_sw, dst_sw)
		src_sw, dst_sw = result[0], result[1]
		if setting.enable_Flow_Entry_L4Port:
			ip_proto, L4_port, Flag = self.get_L4_info(tcp_pkt, udp_pkt)
			if result:
				if dst_sw:
					src_sw, dst_sw = result[0], result[1]
					if ip_proto and L4_port and Flag:
						if ip_proto == 6:
							L4_Proto = 'TCP'
						elif ip_proto == 17:
							L4_Proto = 'UDP'
						else:
							pass
						flow_info = (eth_type, ip_src, ip_dst, in_port, ip_proto, Flag, L4_port)
					else:
						flow_info = (eth_type, ip_src, ip_dst, in_port)
		else:
			flow_info = (eth_type, ip_src, ip_dst, in_port)
		# dst_host and src_host link one same switch
		if src_sw == dst_sw:
			dst_port = self.awareness.get_host_location(ip_dst)[1]
			self.send_flow_mod(datapath, flow_info, in_port, dst_port)
			self.send_packet_out(datapath, msg.buffer_id, in_port, dst_port, msg.data)
		else:
			path = self.get_path(src_sw, dst_sw, weight=self.weight)
			if len(path)==5:
				self.newComingFlows[(ip_src,ip_dst)]=(path[0],path[-1])
			# Path has already been calculated, just get it.
			if path == None:
				return
			try:
				bucket=self.swToSegments(path)
				self._news_Segment_forwarding_(flow_info,bucket)
			except:
				self.flood(msg)


