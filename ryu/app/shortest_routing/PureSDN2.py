#coding:utf-8
#传统的网络是交换机or路由器拥有转发和控制双重身份,路由器之间通过协议来进行路由计算,各个路由器参与到路由计算中,计算好的路由通过路由表的方式装载在路由器中，数据到来后通过路由表转发
#而SDN是将路由计算功能抽象出来交由一个专门的设备来计算,我们称之为SDN控制器. 而交换机or路由器只负责转发,控制器计算好路由后将流表下发到交换机上,数据通过流表来转发。
#实际上，为交换机手动添加流表也能指导数据的转发。这样看来，SDN控制器其实是一个可以自动下发流表的设备，无需人们手动下发。
#代码比较复杂，细节短时间很难去搞清楚，先把各部分搞清楚。
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

import network_awareness

import setting

#此代码是我以及学校实验室学长学姐的代码模板加以改进，所以这个代码有较好的复用性，然而结构有些复杂，为了复用性强进行了大量模块化。希望读者能弄清楚各个模块,函数的意义，通过参数和返回值知道其作用。
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
		"network_awareness": network_awareness.NetworkAwareness}

	WEIGHT_MODEL = {'hop': 'weight'}

	def __init__(self, *args, **kwargs):
		super(ShortestForwarding, self).__init__(*args, **kwargs)
		self.name = "shortest_forwarding"
		self.awareness = kwargs["network_awareness"] #依赖了network_awareness.NetworkAwareness,如名字所示，这是一个网络探测模块。

		self.datapaths = {}
		self.weight = self.WEIGHT_MODEL[CONF.weight]

	@set_ev_cls(ofp_event.EventOFPStateChange, [MAIN_DISPATCHER, DEAD_DISPATCHER])
	def _state_change_handler(self, ev):  #@set_ev_cls 等这种带@的都是一套机制，只要加了这个注解，就能实现特定功能，这是RYU控制器自带的功能。这是对应
											#控制器和网络初始化阶段，控制器需要读取网络（各交换机的信息）并保存，每个交换机对应一个datapath
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

	@set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER) #控制器能控制网络中各种数据包的转发，那一定需要知道各种数据包的特点，想必读者应该了解SDN网络下，当数据包进入交换机找不到匹配
														  #的流表，则需要传到控制器一个数据包。（packet_in)
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

																		        #控制器将这个数据包解开，知道这个数据包特点(是从哪传到哪的，所TCP数据包还是UDP，是ARP数据包还是ICMP阿等等，
																				#最重要的是知道这个数据包是哪传到哪#
		if isinstance(ip_pkt, ipv4.ipv4):
			self.logger.debug("IPV4 processing")
			if len(pkt.get_protocols(ethernet.ethernet)):
				eth_type = pkt.get_protocols(ethernet.ethernet)[0].ethertype
				self.shortest_forwarding(msg, eth_type, ip_pkt.src, ip_pkt.dst)   #通过这个进行最短路径转发，跳转到shortest_forwarding

	def add_flow(self, dp, priority, match, actions, idle_timeout=0, hard_timeout=0): #构造流表所需的相关信息
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
		dp.send_msg(mod)									#通过send_msg()由控制器下发到db这个交换机，这是RYU自带的功能函数

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

	def get_port_pair_from_link(self, link_to_port, src_dpid, dst_dpid): #两个交换机连接叫做交换机对(pair)，两个交换机连接肯定对应两个端口，所以这个函数代表由两个相连的交换机获得哪两个端口连接
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

	def arp_forwarding(self, msg, src_ip, dst_ip): #由计算机网络知识，两个主机进行通信必须知道对方的Mac地址，这个函数用来发送ARP请求获得对方的Mac地址
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
			self.flood(msg)           #一般所通过洪泛的方式来传输ARP

	def get_path(self, src, dst, weight):  #跳转到这里是获得最短路径
		"""
			Get shortest path from network_awareness module.
			generator (nx.shortest_simple_paths( )) produces
			lists of simple paths, in order from shortest to longest.
		"""
		shortest_paths = self.awareness.shortest_paths  #这里调用了network_awareness中的shortest_path集合,实际上，network_awareness 不停的在计算各个节点对的最短路径
		# Create bandwidth-sensitive datapath graph.    #network_awareness中是通过networkX自带的图的最短路径算法来计算，这里用到的是Dijkstra最短路径算法
		graph = self.awareness.graph

		if weight == self.WEIGHT_MODEL['hop']:
			return shortest_paths.get(src).get(dst)[0]	#从最短路径集合里挑选出是属于本目的地址和源地址的路径，最短路径所根据hop计算，hop
															#是指的跳数，也就是经过的交换机数目

		else:
			pass

	def get_sw(self, dpid, in_port, src, dst): #由源 目的地址获得的两个主机相连的交换机，也即目的交换机和源交换机
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
		match = parser.OFPMatch(
						in_port=src_port, eth_type=flow_info[0],
						ipv4_src=flow_info[1], ipv4_dst=flow_info[2])

		self.add_flow(datapath, 30, match, actions,idle_timeout=5, hard_timeout=0)

	def install_flow(self, datapaths ,link_to_port, path, flow_info, buffer_id,ip_src, ip_dst,data=None):
		'''
			Install flow entries for datapaths.
			path=[dpid1, dpid2, ...]
			flow_info = (eth_type, src_ip, dst_ip, in_port)
			or
			flow_info = (eth_type, src_ip, dst_ip, in_port, ip_proto, Flag, L4_port)
		'''
		#这里必须搞清楚，数据一定根据流表转发，所以一条路径上所有交换机必须有相关流表，
		# 则这个函数就是为该条路径上所有交换机下发指定的流表。
		#下发流表的原则是先给一条路径中的第二个到最后一个交换机下发流表，最后给第一个交换机下发。
		#试想，如果先给第一个交换机下发流表，则还没等到后面交换机的流表下发好，则数据包就通过第一个交换机转发了，当数据包到达后续交换机时同样发现没有
		#流表，则又触发了packet_in

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
		if(len(path)==Pathlen):
			self.logger.info("[PATH]%s<-->%s: %s" % (ip_src, ip_dst, path))


	def shortest_forwarding(self, msg, eth_type, ip_src, ip_dst):  #负责最短路径转发的主要工作
		"""
			Calculate shortest forwarding path and Install them into datapaths.
			flow_info = (eth_type, ip_src, ip_dst, in_port)
			or
			flow_info = (eth_type, ip_src, ip_dst, in_port, ip_proto, Flag, L4_port)
		"""

		datapath = msg.datapath
		in_port = msg.match['in_port']
		result = self.get_sw(datapath.id, in_port, ip_src, ip_dst)   # result = (src_sw, dst_sw)
		if result:
			src_sw, dst_sw = result[0], result[1]

			if dst_sw:
				flow_info = (eth_type, ip_src, ip_dst, in_port)
				# dst_host and src_host link one same switch
				if (src_sw == dst_sw):                             #如果是目的和源主机连在同一个交换机上，则无需路径计算，直接获取相应端口转发
					dst_port = self.awareness.get_host_location(ip_dst)[1]
					self.send_flow_mod(datapath, flow_info, in_port, dst_port)

					self.send_packet_out(datapath, msg.buffer_id, in_port, dst_port, msg.data)

				# Path has already been calculated, just get it.
				else:
					path = self.get_path(src_sw, dst_sw, weight=self.weight)  #如果不是则通过get_path获取转发路径
					if path==None:
						return
					# Install flow entries to datapaths along the path.
					self.install_flow(self.datapaths ,						#安装要下发的流表的所需相关信息
									  self.awareness.link_to_port,
									  path, flow_info, msg.buffer_id,ip_src, ip_dst, msg.data)
		else:
			# Flood is not good.

			self.flood(msg)
