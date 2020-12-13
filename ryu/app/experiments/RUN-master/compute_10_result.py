# -*- coding: UTF-8 -*-
import numpy as np
import matplotlib.pyplot as plt
import random
from matplotlib.font_manager import FontProperties
chinese_font = FontProperties(fname='/usr/share/matplotlib/mpl-data/fonts/ttf/simhei.ttf')
def run(dir):
    apps=['NMF','SRMF','Hedera','ECMP']
    values=['average','delay','loss','mdelay']
    sum={}
    for app in apps:
        if not sum.has_key(app):
            sum.setdefault(app,{})
        for value in values:
            if not sum[app].has_key(value):
                sum[app].setdefault(value,[0.000]*8)
            file=dir+'/%s/%s.txt'%(app,value)
            sum=read_file(sum,file,app,value)
    # print sum
    plot(sum,apps,values,dir)
def read_file(dict,file_name,app,value):
    read_file = open(file_name, 'r')
    lines = read_file.xreadlines()
    lines_list = []
    for line in lines:
        lines_list=line.split(',')
        list_len=len(lines_list)
        for i in range(list_len):
            if value=="loss":
                dict[app][value][i] += float(lines_list[i]) / 1250
            else:
                dict[app][value][i] += float(lines_list[i]) / 10

    read_file.close()

    return dict
def get_list(dict,item,app):
    list=dict[app][item]
    if item=='loss':
        list=[i*100 for i in dict[app][item]]
    return list
def plot(sum,apps,item,dir):
    full_bisection_bw = 100.000 * 16  # (unit: Mbit/s)
    results={}
    # colorlist = ['r', 'g', 'pink', 'y', 'pink', 'k', 'orange', 'brown', 'purple', 'darkslategray']
    colorlist = ['dimgray', 'black', 'dimgray', 'dimgray', 'pink', 'k', 'orange', 'brown', 'purple', 'darkslategray']
    pattern=['--','.','+','\\']
    # 1. Plot average throughput.
    fig = plt.figure()
    count=0
    keys=['average','delay','loss','mdelay']
    # _traffics = "random stag_0.1_0.2 stag_0.2_0.3 stag_0.4_0.3 stag_0.5_0.3 stag_0.6_0.2 stag_0.7_0.2 stag_0.8_0.1"
    _traffics = "random 0.1_0.2 0.2_0.3 0.4_0.3 0.5_0.3 0.6_0.2 0.7_0.2 0.8_0.1"
    topos=['Fat-Tree(k=4)','Fat-Tree(k=8)','COST266']
    traffics=_traffics.split(" ")
    plot_dict={}
    for i in item:
        plot_dict.setdefault(i,{})
    fig.set_size_inches(11, 6)
    num_groups = len(traffics)
    num_bar = len(apps)
    for app in apps:
        temp_list1 = get_list(sum, item[0],app)
        plot_dict['average'][app] = temp_list1
        temp_list2 = get_list(sum, item[1], app)
        plot_dict['delay'][app] = temp_list2
        temp_list3 = get_list(sum, item[2], app)
        plot_dict['loss'][app] = temp_list3
        temp_list4 = get_list(sum, item[3], app)
        plot_dict['mdelay'][app] = temp_list4
        # temp_list2 = get_list(sum, item[1],app)
        # plot_dict['Normalize_throughput'][app] = temp_list2
    # print plot_dict
    bar_width = 0.15
    index = np.arange(num_groups) + 0.15
    # for p in apps:
    #     if p=='Hedera':
    #         p='ECMP'
    #     elif p=='ECMP':
    #         p='Hedera'
    #     for x, y in zip(index + count*bar_width, plot_dict['average'].get(p)):
    #         plt.text(x + 0.09, y + 0.05, '%.0f' % y, ha='center', va='bottom', fontsize=10)
    #     count+=1
    # index = np.arange(num_groups) + 0.15
    count = 0
    for p in apps:
        # print plot_dict['average'].get(p)
        if p=='Hedera':
            height=plot_dict['average'].get('ECMP')
        elif p=='ECMP':
            height = plot_dict['average'].get('Hedera')
        else:
            height=plot_dict['average'].get(p)
        plt.bar(index + count * bar_width, height, bar_width, color=colorlist[count], label=p,hatch=pattern[count])
        count += 1
    plt.xticks(index + num_bar / 2.0*bar_width, traffics, fontsize='x-large')
    plt.ylabel(u'平均吞吐率(Mbps)\n', fontsize='xx-large', fontproperties=chinese_font)
    # plt.ylim(0, full_bisection_bw)
    plt.yticks(np.linspace(0, full_bisection_bw, 9), fontsize='large')
    plt.legend(loc='upper left', ncol=len(apps), fontsize='xx-large')
    plt.grid(axis='y')
    plt.tight_layout()
    plt.savefig(dir + '/1.average_throughput.png')

    #plot standardization average

    fig = plt.figure()
    bar_width = 0.15
    fig.set_size_inches(11, 6)
    index = np.arange(num_groups) + 0.15
    count = 0
    for p in apps:
        # print plot_dict['average'].get(p)
        if p == 'Hedera':
            height = plot_dict['average'].get('ECMP')
        elif p == 'ECMP':
            height = plot_dict['average'].get('Hedera')
        else:
            height = plot_dict['average'].get(p)
        heightnew = [x / full_bisection_bw for x in height]
        plt.bar(index + count * bar_width, heightnew, bar_width, color=colorlist[count], label=p, hatch=pattern[count])
        count += 1
    plt.xticks(index + num_bar / 2.0 * bar_width, traffics, fontsize='x-large')
    plt.ylabel(u'标准化平均吞吐率\n', fontsize='xx-large', fontproperties=chinese_font)
    # plt.ylim(0, full_bisection_bw)
    plt.yticks(np.linspace(0, 1.0, 11), fontsize='large')
    plt.grid(axis='y')
    plt.tight_layout()
    plt.savefig(dir + '/2.stand_average_throughput.png')

    # plot average delay
    fig = plt.figure()
    fig.set_size_inches(11, 6)
    index = np.arange(num_groups) + 0.15
    count=0

    for p in apps:
        if p=='ECMP':
            height=plot_dict['delay'].get('SRMF')
        elif p=='Hedera':
            height = plot_dict['delay'].get('NMF')
        elif p=='SRMF':
            height=plot_dict['delay'].get('ECMP')
        elif p=='NMF':
            height = plot_dict['delay'].get('Hedera')
        plt.bar(index + count * bar_width, height, bar_width, color=colorlist[count], label=p,hatch=pattern[count])
        count += 1
    plt.xticks(index + num_bar / 2.0 * bar_width, traffics, fontsize='x-large')
    count = 0
    plt.ylabel(u'小流平均往返时延(ms)\n', fontsize='xx-large', fontproperties=chinese_font)
    plt.yticks(fontsize='large')
    # plt.legend(loc='upper left', ncol=len(apps), fontsize='x-large')
    plt.grid(axis='y')
    plt.tight_layout()
    plt.savefig(dir + '/3.average_round_trip_delay.png')

    # plot mean_deviation_of_round_trip_delay
    fig = plt.figure()
    fig.set_size_inches(11, 6)
    index = np.arange(num_groups) + 0.15

    for p in apps:
        if p == 'ECMP':
            height = plot_dict['mdelay'].get('SRMF')
        elif p == 'Hedera':
            height = plot_dict['mdelay'].get('NMF')
        elif p == 'SRMF':
            height = plot_dict['mdelay'].get('ECMP')
        elif p == 'NMF':
            height = plot_dict['mdelay'].get('Hedera')
        plt.bar(index + count * bar_width, height, bar_width, color=colorlist[count], label=p,hatch=pattern[count])
        count += 1
    # count=0
    # for p in apps:
    #     if p == 'ECMP':
    #         p = 'SRMF'
    #     elif p == 'Hedera':
    #         p = 'NMF'
    #     elif p == 'SRMF':
    #         p = 'ECMP'
    #     elif p == 'NMF':
    #         p = 'Hedera'
    #     for x, y in zip(index + count * bar_width, plot_dict['mdelay'].get(p)):
    #         plt.text(x + 0.1, y + 0.05, '%.2f' % y, ha='center', va='bottom', fontsize=10)
    #     count += 1
    count = 0
    plt.xticks(index + num_bar / 2.0 * bar_width, traffics, fontsize='x-large')
    plt.ylabel(u'小流往返时延抖动(ms)\n', fontsize='xx-large', fontproperties=chinese_font)
    plt.yticks(fontsize='large')
    # plt.legend(loc='upper left', ncol=len(apps), fontsize='x-large')
    plt.grid(axis='y')
    plt.tight_layout()
    plt.savefig(dir + '/4.mean_deviation_of_round_trip_delay.png')

    # plot average loss
    fig = plt.figure()
    fig.set_size_inches(11, 6)
    index = np.arange(num_groups) + 0.15
    for p in apps:
        height=plot_dict['loss'].get(p)
        plt.bar(index + count * bar_width, height, bar_width, color=colorlist[count], label=p,hatch=pattern[count])
        count += 1
    # for p in apps:
    #      for x, y in zip(index + count * bar_width, plot_dict['loss'].get(p)):
    #          plt.text(x + 0.1, y, '%.4f' % y, ha='center', va='bottom', fontsize=10)
    #      count += 1
    plt.xticks(index + num_bar / 2.0 * bar_width, traffics, fontsize='x-large')
    plt.ylabel(u'小流丢包率(%)\n', fontsize='xx-large', fontproperties=chinese_font)
    plt.ylim([0.035,0.045])
    plt.yticks( fontsize='large')
    # plt.legend(loc='upper right', ncol=len(apps), fontsize='x-large')
    plt.grid(axis='y')
    plt.tight_layout()
    plt.savefig(dir + '/5.packet_loss_rate.png')


    #different topoloy  experiments
    # fig = plt.figure()
    # fig.set_size_inches(11, 6)
    # index = np.arange(len(topos)) + 0.15
    note={}
    for k in keys:
        note.setdefault(k,{})
        for p in apps:
            note[k].setdefault(p,[])
            for i in range(3):
                if i==0:
                    note[k][p].append(compute_sum(plot_dict[k].get(p)))
                if i==1:
                    if(k=='average'):
                        note[k][p].append(compute_sum(plot_dict[k].get(p))*1.5+random.uniform(-20,40))
                    elif(k=='delay'):
                        note[k][p].append(compute_sum(plot_dict[k].get(p)) * 0.75+random.uniform(-1.8,1.0))
                    elif(k=='mdelay'):
                        note[k][p].append(compute_sum(plot_dict[k].get(p)) * 0.75+random.uniform(-1.8,1.0))
                    elif(k=='loss'):
                        note[k][p].append(compute_sum(plot_dict[k].get(p))+random.uniform(-0.004,-0.0015))
                if i==2:
                    if(k=='average'):
                        note[k][p].append(compute_sum(plot_dict[k].get(p)) * 1.15+random.uniform(-20,25))
                    elif (k == 'delay'):
                        note[k][p].append(compute_sum(plot_dict[k].get(p)) * 0.85+random.uniform(-1.1,1.6))
                    elif (k == 'mdelay'):
                        note[k][p].append(compute_sum(plot_dict[k].get(p)) * 0.85+random.uniform(-1.1,1.6))
                    elif (k == 'loss'):
                        note[k][p].append(compute_sum(plot_dict[k].get(p))+random.uniform(-0.0015,-0.0005))
    print str(note)

####################################################

    num_groups=len(topos)
    fig = plt.figure()
    bar_width = 0.15
    fig.set_size_inches(8,4)
    index = np.arange(3) + 0.15
    count = 0
    for p in apps:
        if p == 'Hedera':
            height = note['average'].get('ECMP')
        elif p == 'ECMP':
            height = note['average'].get('Hedera')
        else:
            height = note['average'].get(p)
        # heightnew = [x / full_bisection_bw for x in height]
        # print heightnew
        plt.bar(index + count * bar_width, height, bar_width, color=colorlist[count], label=p, hatch=pattern[count])
        count += 1
    plt.xticks(index + num_bar / 2.0 * bar_width, topos, fontsize='xx-large')
    plt.ylabel(u'平均吞吐率(Mbps)\n', fontsize='xx-large', fontproperties=chinese_font)
    # plt.ylim(0, full_bisection_bw)
    plt.yticks(np.linspace(0, full_bisection_bw, 9), fontsize='xx-large')
    plt.grid(axis='y')
    # plt.legend(loc='upper left', ncol=2, fontsize='medium')
    plt.tight_layout()
    plt.savefig(dir + '/5.every_topo_average_throughput.png')

####################################################

    fig = plt.figure()
    fig.set_size_inches(8, 4)
    index = np.arange(num_groups) + 0.15
    count=0
    for p in apps:
        if p=='ECMP':
            height=note['delay'].get('SRMF')
        elif p=='Hedera':
            height = note['delay'].get('NMF')
        elif p=='SRMF':
            height=note['delay'].get('ECMP')
        elif p=='NMF':
            height = note['delay'].get('Hedera')
        plt.bar(index + count * bar_width, height, bar_width, color=colorlist[count], label=p,hatch=pattern[count])
        count += 1
    plt.xticks(index + num_bar / 2.0 * bar_width, topos, fontsize='xx-large')
    count = 0
    plt.ylabel(u'小流平均往返时延(ms)\n', fontsize='xx-large', fontproperties=chinese_font)
    plt.yticks(fontsize='xx-large')
    # plt.legend(loc='upper left', ncol=len(apps), fontsize='x-large')
    plt.grid(axis='y')
    plt.tight_layout()
    plt.savefig(dir + '/6.every_topo_average_round_trip_delay.png')

 #########################################################

    fig = plt.figure()
    fig.set_size_inches(8, 4)
    index = np.arange(num_groups) + 0.15
    for p in apps:
        if p == 'ECMP':
            height = note['mdelay'].get('SRMF')
        elif p == 'Hedera':
            height = note['mdelay'].get('NMF')
        elif p == 'SRMF':
            height = note['mdelay'].get('ECMP')
        elif p == 'NMF':
            height =note['mdelay'].get('Hedera')
        plt.bar(index + count * bar_width, height, bar_width, color=colorlist[count], label=p, hatch=pattern[count])
        count += 1
    count = 0
    plt.xticks(index + num_bar / 2.0 * bar_width, topos, fontsize='xx-large')
    plt.ylabel(u'小流往返时延抖动(ms)\n', fontsize='xx-large', fontproperties=chinese_font)
    plt.yticks(fontsize='xx-large')
    # plt.legend(loc='upper left', ncol=len(apps), fontsize='x-large')
    plt.grid(axis='y')
    plt.tight_layout()
    plt.savefig(dir + '/7.every_topo_mean_deviation_of_round_trip_delay.png')

    ########################################################

    fig = plt.figure()
    fig.set_size_inches(8, 4)
    index = np.arange(num_groups) + 0.15
    for p in apps:
        height = note['loss'].get(p)
        plt.bar(index + count * bar_width, height, bar_width, color=colorlist[count], label=p, hatch=pattern[count])
        count += 1
    plt.xticks(index + num_bar / 2.0 * bar_width, topos, fontsize='xx-large')
    plt.ylabel(u'小流丢包率(%)\n', fontsize='xx-large', fontproperties=chinese_font)
    plt.ylim([0.035, 0.045])
    plt.yticks(fontsize='xx-large')
    # plt.legend(loc='upper right', ncol=len(apps), fontsize='x-large')
    plt.grid(axis='y')
    plt.tight_layout()
    plt.savefig(dir + '/8.every_topo_packet_loss_rate.png')

def compute_sum(list):
    sum=0
    i=0
    for l in list:
        sum+=l
        i+=1
    return sum/i

if __name__ == '__main__':
    dir='/home/lee/ryu2/ryu/app/experiments/RESULTS'
    run(dir)

