# -*- coding: UTF-8 -*-
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
import network_awareness
import network_monitor
import setting
import networkx as nx
import userDao as db
import random as rand
CONF = cfg.CONF
from ryu.lib import hub

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
		"network_monitor": network_monitor.NetworkMonitor}

	WEIGHT_MODEL = {'hop': 'weight','bw':'bw'}

	def __init__(self, *args, **kwargs):
		super(ShortestForwarding, self).__init__(*args, **kwargs)
		self.name = "shortest_forwarding"
		self.awareness = kwargs["network_awareness"]
		self.monitor = kwargs["network_monitor"]
		self.datapaths = {}
		self.weight = self.WEIGHT_MODEL[CONF.weight]
		self.dataBase=db.Dbutil()
		self.deletePaths=set()
		self.allUsersData=set()
		self.deletePath_thread = hub.spawn(self.deletePath_processor) #可以理解为开启一个线程，函数体内在无限循环检测删除（之所以这样是为了减少数据库操作）


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
			result = self.dataBase.select(ip_pkt.src)	#数据据包到来查询一次数据库
			if(result[1]==1): #如果数据库查询不到用户或者查询到了用户然而用户没有登录,则不处理
				degree = result[0]  # 根据数据库中用户degreeid来确定用户的级别,对应不同的路由算法,1为最高级别，2次高，3最低
			if len(pkt.get_protocols(ethernet.ethernet)):
				eth_type = pkt.get_protocols(ethernet.ethernet)[0].ethertype
				self.shortest_forwarding(msg, eth_type, ip_pkt.src, ip_pkt.dst, degree)

	# 如果流表删除后 ，则触发这个函数，获得删除流表的信息，删除的原因有很多，比如 # idle_timeout和hard_timeout，我们只用到idle_timeout，删除后通知数据库的path表将该路径信息删除。
	@set_ev_cls(ofp_event.EventOFPFlowRemoved, MAIN_DISPATCHER)
	def flow_removed_handler(self, ev):
		msg = ev.msg
		dp = msg.datapath
		ofp = dp.ofproto
		currentTime=msg.duration_sec
		ip_src=msg.match.get("ipv4_src")
		ip_dst=msg.match.get("ipv4_dst")
		self.deletePaths.add((ip_src,ip_dst,currentTime)) 	 #由于EventOFPFlowRemoved可能频繁触发，而且一触发就是路径上所有交换机流表，# 重复性高，如果都请求数据库删除，数据库压力大(避免频繁IO)
	def deletePath_processor(self):
		while CONF.weight == 'bw' or CONF.weight=='hop':
			self.deletePathIndataBase()
			hub.sleep(setting.MONITOR_PERIOD)

	def deletePathIndataBase(self):
		while self.deletePaths:					#当有数据时才调用数据库删除
			pair=self.deletePaths.pop()			#处理完一条路径信息就删除
			ip_src=pair[0]
			ip_dst=pair[1]
			t=pair[2]
			self.dataBase.deletePath(ip_src,ip_dst,t)

	def add_flow(self, dp, priority, match, actions):
		"""
			Send a flow entry to datapath.
		"""
		ofproto = dp.ofproto
		parser = dp.ofproto_parser
		inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS, actions)]
		mod = parser.OFPFlowMod(datapath=dp, priority=priority,
								idle_timeout=setting.IDLE_TIMEOUT,
								hard_timeout=setting.HARD_TIMEOUT,
								match=match, instructions=inst,
								flags=ofproto.OFPFF_SEND_FLOW_REM)
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


	def get_path(self, src, dst, degree):
		"""
			Get shortest path from network_awareness module.
			generator (nx.shortest_simple_paths( )) produces
			lists of simple paths, in order from shortest to longest.
		"""
		shortest_paths = self.awareness.shortest_paths
		# Create bandwidth-sensitive datapath graph.
		# graph=self.awareness.graph
		graph = self.monitor.graph
		paths=shortest_paths.get(src).get(dst)
		if degree==3:
			print degree
			return paths[rand.randint(0,CONF.k_paths-1)] #从k条最短路径集合随机取一条
		if degree==2:
			print degree
			return nx.shortest_path(graph, src, dst, weight='BandWeight', method='dijkstra') #根据带宽为链路权重计算最短路径(计算最短路径：权重最小映射为可用带宽最大
		if degree==1:#从最短路径集合中选择一条链路最小剩余带宽最大的路径
			print degree
			try:
				path=self.monitor.get_best_bw_path(graph,paths)
				return path
			except:
				print "未知错误,改为非最优路径"
				return nx.shortest_path(graph,src,dst,'dijkstra')
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

	def send_flow_mod(self, datapath, flow_info, src_port, dst_port,degree):
		"""
			Build flow entry, and send it to datapath.
			flow_info = (eth_type, src_ip, dst_ip, in_port)
			or
			flow_info = (eth_type, src_ip, dst_ip, in_port, ip_proto, Flag, L4_port)
		"""
		dpid=datapath.id
		parser = datapath.ofproto_parser
		actions = []
		if str(dpid).startswith('3'): #只对边缘路由器下发队列
			if degree:
				actions.append(parser.OFPActionSetQueue(degree))
		actions.append(parser.OFPActionOutput(dst_port))
		match = parser.OFPMatch(
						in_port=src_port, eth_type=flow_info[0],
						ipv4_src=flow_info[1], ipv4_dst=flow_info[2])

		self.add_flow(datapath, 30, match, actions)

	def install_flow(self, datapaths ,link_to_port, path, flow_info, buffer_id,ip_src, ip_dst, data, degree):
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
		#先安装第二个到最后一个路由器的流表
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
				self.send_flow_mod(datapath, flow_info, src_port, dst_port,degree)
		if port_pair is None:
			self.logger.info("Port not found in first hop.")
			return
		#最后安装第一个
		out_port = port_pair[0]
		self.send_flow_mod(first_dp, flow_info, in_port, out_port,degree)
		# Send packet_out to the first datapath.
		self.send_packet_out(first_dp, buffer_id, in_port, out_port, data)
		if(len(path)==Pathlen):
			self.logger.info("[PATH]%s<-->%s: %s" % (ip_src, ip_dst, path))

	def shortest_forwarding(self, msg, eth_type, ip_src, ip_dst,degree):
		"""
			Calculate shortest forwarding path and Install them into datapaths.
			flow_info = (eth_type, ip_src, ip_dst, in_port)
			or
			flow_info = (eth_type, ip_src, ip_dst, in_port, ip_proto, Flag, L4_port)
		"""

		datapath = msg.datapath
		in_port = msg.match['in_port']
		result = self.get_sw(datapath.id, in_port, ip_src, ip_dst)   # result = (src_sw, dst_sw)
		print(result)
		if result:
			src_sw, dst_sw = result[0], result[1]

			if dst_sw:
				flow_info = (eth_type, ip_src, ip_dst, in_port)
				# dst_host and src_host link one same switch
				if (src_sw == dst_sw):
					print("same!")
					dst_port = self.awareness.get_host_location(ip_dst)[1]
					self.send_flow_mod(datapath, flow_info, in_port, dst_port)

					self.send_packet_out(datapath, msg.buffer_id, in_port, dst_port, msg.data)

				# Path has already been calculated, just get it.
				else:
					path = self.get_path(src_sw, dst_sw, degree)
					if path==None:
						return
					path2Str=str(path)[1:-1]
					self.dataBase.insert(ip_src,path2Str,ip_dst)
					# Install flow entries to datapaths along the path.
					self.install_flow(self.datapaths ,self.awareness.link_to_port,path, flow_info, msg.buffer_id,ip_src, ip_dst, msg.data,degree)
		else:
			# Flood is not good.

			self.flood(msg)
