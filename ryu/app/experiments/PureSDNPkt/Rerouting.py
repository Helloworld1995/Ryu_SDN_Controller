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
from ryu.lib.packet import icmp
import network_awareness
import network_monitor_predict
import setting
import networkx as nx
import random

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
		"network_monitor": network_monitor_predict.NetworkMonitor}


	WEIGHT_MODEL = {'hop': 'weight','bw':'bw'}

	def __init__(self, *args, **kwargs):
		super(ShortestForwarding, self).__init__(*args, **kwargs)
		self.name = "shortest_forwarding"
		self.awareness = kwargs["network_awareness"]
		self.monitor = kwargs["network_monitor"]
		self.datapaths = {}
		self.seletPathIndex=0
		self.weight = self.WEIGHT_MODEL[CONF.weight]
		self.newComingFlows={'src':{},'dst':{}}
		self.graph=None
		self.register=[]



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
				# del self.datapaths[datapath.id]

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
			protocol = pkt.get_protocols(ethernet.ethernet)
			self.logger.debug("IPV4 processing")
			if len(protocol):
				eth_type = pkt.protocols[0].ethertype
				self.shortest_forwarding(msg, eth_type, ip_pkt.src, ip_pkt.dst)
	def add_flow(self, dp, priority, match, actions, idle_timeout=0, hard_timeout=0):
		"""
			Send a flow entry to datapath.
		"""
		ofproto = dp.ofproto
		parser = dp.ofproto_parser
		inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS, actions)]
		if dp.id/1000==1:
			mod = parser.OFPFlowMod(datapath=dp, priority=priority,
									idle_timeout=idle_timeout,
									hard_timeout=hard_timeout,
									match=match, instructions=inst,flags=ofproto.OFPFF_SEND_FLOW_REM)
		else:
			mod = parser.OFPFlowMod(datapath=dp, priority=priority,
									idle_timeout=idle_timeout,
									hard_timeout=hard_timeout,
									match=match, instructions=inst)
		dp.send_msg(mod)
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
			eth_type=flow_info[0],ipv4_src=flow_info[1], ipv4_dst=flow_info[2],in_port=flow_info[-1],
						ip_proto=6, tcp_src=flow_info[-2],tcp_dst=flow_info[-1]
		)
		mod = parser.OFPFlowMod(datapath=datapath, priority=25,
								table_id=0,
								idle_timeout=2,
								hard_timeout=0,
								match=match, instructions=inst,flags=ofproto.OFPFF_SEND_FLOW_REM)
		datapath.send_msg(mod)

	@set_ev_cls(ofp_event.EventOFPFlowRemoved, MAIN_DISPATCHER)
	def flow_removed_handler(self, ev):
		msg = ev.msg
		dp = msg.datapath
		l4port1=None
		l4port2=None
		protocol=msg.match.get("ip_proto")
		ip_src = msg.match.get("ipv4_src")
		ip_dst = msg.match.get("ipv4_dst")
		if protocol==6:
			l4port1 = msg.match.get("tcp_src")
			l4port2 = msg.match.get("tcp_dst")
		elif protocol==17:
			l4port1 = msg.match.get("udp_src")
			l4port2 = msg.match.get("udp_dst")
		if self.newComingFlows['src'].has_key(ip_src):
			if self.newComingFlows['src'][ip_src] > 0:
				self.newComingFlows['src'][ip_src] -= 1
		if self.newComingFlows['dst'].has_key(ip_dst):
			if self.newComingFlows['dst'][ip_dst] > 0:
				self.newComingFlows['dst'][ip_dst] -= 1
		deleteInfo=set([ip_src,ip_dst,protocol,l4port1,l4port2])
		for info in self.register:
			if deleteInfo.intersection(info)==deleteInfo:
				self.register.remove(info)
		print self.register

	def get_path(self, src, dst):
		"""
			Get shortest path from network_awareness module.
			generator (nx.shortest_simple_paths( )) produces
			lists of simple paths, in order from shortest to longest.
		"""
		shortest_paths = self.awareness.shortest_paths
		if self.seletPathIndex==CONF.k_paths:
			self.seletPathIndex=0
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
		if weight == self.WEIGHT_MODEL['hop']:
			graph = self.awareness.graph
			return nx.shortest_path(graph,src,dst,method='dijkstra')

		elif weight == self.WEIGHT_MODEL['bw']:
			graph = self.monitor.graph
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
		elif len(flow_info) == 5:
			match = parser.OFPMatch(
				in_port=src_port, eth_type=flow_info[0],ip_proto=flow_info[-1],
				ipv4_src=flow_info[1], ipv4_dst=flow_info[2])
		else:
			pass

		self.add_flow(datapath, 30, match, actions,idle_timeout=2, hard_timeout=0)

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
		if port_pair is None:
			self.logger.info("Port not found in first hop.")
			return
		out_port = port_pair[0]
		self.send_flow_mod(first_dp, flow_info, in_port, out_port)
		# Send packet_out to the first datapath.
		self.send_packet_out(first_dp, buffer_id, in_port, out_port, data)

	def get_L4_info(self, tcp_pkt, udp_pkt):
		"""
			Get ip_proto and L4 port number.
		"""
		ip_proto = None
		L4_port = []
		Flag = None
		if tcp_pkt:
			ip_proto = 6
			if tcp_pkt.src_port and tcp_pkt.dst_port:
				L4_port = [tcp_pkt.src_port,tcp_pkt.dst_port]
				Flag = True
			else:
				Flag=False

		elif udp_pkt:
			ip_proto = 17
			if udp_pkt.src_port and udp_pkt.dst_port:
				L4_port = [udp_pkt.src_port,udp_pkt.dst_port]
				Flag = True
			else:
				Flag=False

		else:
			pass
		return (ip_proto, L4_port, Flag)

	def icmp_forwarding(self, msg, ip_protocol, eth_type, ip_src, ip_dst):
		datapath = msg.datapath
		in_port = msg.match['in_port']
		dst_port = self.awareness.get_host_location(ip_dst)[1]
		result = self.get_sw(datapath.id, in_port, ip_src, ip_dst)
		flow_info = (eth_type,ip_src,ip_dst, in_port,ip_protocol)
		flow_info_reverse=(eth_type,ip_dst,ip_src, dst_port,ip_protocol)
		src_sw, dst_sw = result[0], result[1]
		if src_sw == dst_sw:
			dst_port = self.awareness.get_host_location(ip_dst)[1]
			self.send_packet_out(datapath, msg.buffer_id, in_port, dst_port, msg.data)
		else:
			path = self.get_path(src_sw, dst_sw)
			if path == None:
				return
			path.reverse()
			try:
				self.install_flow(self.datapaths,self.awareness.link_to_port,path, flow_info_reverse, msg.buffer_id,ip_dst,ip_src, None)
				path.reverse()
				self.install_flow(self.datapaths, self.awareness.link_to_port, path, flow_info, msg.buffer_id, ip_src,ip_dst, msg.data)
			except:
				self.flood(msg)
	def shortest_forwarding(self, msg, eth_type, ip_src, ip_dst):
		"""
			Calculate shortest forwarding path and Install them into datapaths.
			flow_info = (eth_type, ip_src, ip_dst, in_port)
			or
			flow_info = (eth_type, ip_src, ip_dst, in_port, ip_proto, Flag, L4_port)
		"""
		pkt = packet.Packet(msg.data)
		icmp_pkt = pkt.get_protocol(icmp.icmp)
		if icmp_pkt:
			ip_protocol = 1
			print 'icmp forwarding!'
			self.icmp_forwarding(msg, ip_protocol, eth_type, ip_src, ip_dst)
			return
		datapath = msg.datapath
		in_port = msg.match['in_port']
		dst_port = self.awareness.get_host_location(ip_dst)[1]
		tcp_pkt = pkt.get_protocol(tcp.tcp)
		udp_pkt = pkt.get_protocol(udp.udp)
		L4_port = None
		flow_info = None
		flow_info_reverse = None

		# if not icmp packet,Get ip_proto and L4 port number.
		result = self.get_sw(datapath.id, in_port, ip_src, ip_dst)  # result = (src_sw, dst_sw)
		if (result):
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
						L4_port.reverse()
						flow_info = (eth_type, ip_src, ip_dst, in_port, ip_proto, Flag,L4_port)
						flow_info_reverse = (eth_type, ip_dst, ip_src, dst_port, ip_proto, Flag, L4_port)
					else:
						flow_info = (eth_type, ip_src, ip_dst, in_port)
						flow_info_reverse = (eth_type, ip_dst, ip_src, dst_port)
		else:
			flow_info = (eth_type, ip_src, ip_dst, in_port)
			flow_info_reverse = (eth_type, ip_dst, ip_src, dst_port)
		info= (ip_src,ip_dst,ip_proto,L4_port[0],L4_port[1])
		info2=(ip_dst,ip_src,ip_proto,L4_port[1],L4_port[0])
		if src_sw == dst_sw:
			self.send_packet_out(datapath, msg.buffer_id, in_port, dst_port, msg.data)
		else:
			if not (str(src_sw).startswith('3') and str(dst_sw).startswith('3')):
				return
			paths = self.awareness.shortest_paths.get(src_sw).get(dst_sw)
			self.graph = self.monitor.graph
			path=self._select_paths1(paths)
			print path
			# path = self.get_path(src_sw, dst_sw, weight=self.weight)
			# Path has already been calculated, just get it.
			if path == None:
				return
			path.reverse()
			print flow_info
			try:
				self.install_flow(self.datapaths, self.awareness.link_to_port, path, flow_info_reverse, msg.buffer_id, ip_dst, ip_src, msg.data)
				path.reverse()
				if len(flow_info_reverse)==7:
					L4_port.reverse()
				self.install_flow(self.datapaths ,self.awareness.link_to_port,path, flow_info, msg.buffer_id,ip_src, ip_dst, msg.data)
			except:
				self.flood(msg)

	def _select_paths1(self,paths):
		pathDict = {}
		temp_paths=[]
		pathMaxBw=-1
		pathMinBw=setting.MAX_CAPACITY*10
		pathMaxBwWave = -1
		pathMinBwWave=setting.MAX_CAPACITY*10
		str2Path = {}
		for path in paths:
			p = str(path)
			temp = self.get_minBand_ofPath(path)
			free = 0.9 * temp[0]
			str2Path[p]=path
			if free>=0:
				temp_paths.append(p)
				pathDict.setdefault(p,[])
				pathDict[p].append(free)  # {path:[bw,d,loss,errors]}
				pathDict[p].append(temp[1])
				if pathMinBw>free:
					pathMinBw=free
				if pathMaxBw<free:
					pathMaxBw=free
				if pathMaxBwWave<temp[1]:
					pathMaxBwWave=temp[1]
				if pathMinBwWave>temp[1]:
					pathMinBwWave=temp[1]
		randomPath = paths[random.randint(0, len(paths) - 1)]
		print 'random path is %s' % str(randomPath)
		if temp_paths==[]:
			return randomPath
		maxWeight=-1
		bestPath = None
		try:
			for p in temp_paths:
				a = setting.a
				c2=(pathMaxBwWave-pathDict[p][1])/(pathMaxBwWave-pathMinBwWave)
				c1=(pathMaxBw-pathDict[p][0])/(pathMaxBw-pathMinBw)
				c = a*c1+(1-a)*c2
				if maxWeight<c:
					maxWeight=c
					bestPath=p
			print 'best path is %s'%bestPath
			return str2Path.get(bestPath)
		except:
			return randomPath


	def get_minBand_ofPath(self, path):
		"""
            Getting bandwidth of path. Actually, the mininum bandwidth
            of links is the path's bandwith, because it is the bottleneck of path.
        """
		waveBw=[] # every link bw
		allBw=0
		sd=0 # link wave value
		_len = len(path)
		if _len > 1:
			minBw = setting.MAX_CAPACITY
			for i in xrange(_len - 1):
				pre, curr = path[i], path[i + 1]
				# if 'bandwidth' in graph[pre][curr]:
				bw = self.graph[pre][curr]['bandwidth']
				allBw+=bw
				if minBw > bw:
					minBw = bw
				waveBw.append(bw)
			averageBw=allBw/len(waveBw)
			for  b in waveBw:
				sd=sd+(b-averageBw)**2
			return minBw,pow(sd,0.5)
