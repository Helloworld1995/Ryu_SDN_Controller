# -*- coding: UTF-8 -*-
import os
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.font_manager import FontProperties
from matplotlib.pyplot import MultipleLocator
import matplotlib.ticker as mticker
import random
chinese_font = FontProperties(fname='/usr/share/matplotlib/mpl-data/fonts/ttf/simhei.ttf')
class SolveData:
    def __init__(self,path):
        self.path=path
        self.resultDict={}
        self.pingDict={}
        self.flowCount={}
        self.compareDict1={}
        self.compareResult1={}
        self.comparePingDicet1={}
        self.comparePingResult1={}
        self.miceIndex=[0.6,0.7,0.8,0.9,1.0]
        self.fnumList=[10,20,30,40,50,60,70,80,90,100]
        self.experimentsCount=['1','2','3','4','5','6','7','8','9','10']
        self.appList=['Normalrouting','SRrouting']
        self.trafficList=['random']
    def _get_compare1_result(self):
        p='/home/lee/ryu2/ryu/app/experiments/compare_miceIndex1/'
        for index in self.experimentsCount:
            # self.compareDict1.setdefault(index,{})
            self.comparePingDicet1.setdefault(index,{})
            path=p+index+"/"
            for m in self.miceIndex:
                # self.compareDict1[index].setdefault(m, [])
                self.comparePingDicet1[index].setdefault(m,[])
                path1=path+'%s/SRrouting/'%m
                path2=path1+'flow_count'
                path3=path1+'/pingTest'
                fileList=[]
                # for k in os.listdir(path1):
                #     if k.endswith('txt'):
                #         fileList.append(k)
                # self.read_compare_files(fileList,m,index,path1)
                # fileList=[]
                for k in os.listdir(path3):
                    fileList.append(k)
                self.read_compare_pingfiles(fileList,m,index,path3)
        for m in [0.6,0.7,0.8,0.9,1.0]:
            # self.compareResult1.setdefault(m,{})
            self.comparePingResult1.setdefault(m, {})
            self.comparePingResult1.setdefault(m, {})
            # self.compareResult1[m].setdefault('transfer', 0.0)
            # self.compareResult1[m].setdefault('total_throughput', 0.0)
            # self.compareResult1[m].setdefault('average_throughput', 0.0)
            self.comparePingResult1[m].setdefault('loss', 0.0)
            self.comparePingResult1[m].setdefault('average_delay', 0.0)
            self.comparePingResult1[m].setdefault('average_mdev', 0.0)
            for p in self.experimentsCount:
                # tf=self.compareDict1[p][m][0]
                # all=self.compareDict1[p][m][1]
                # ave=self.compareDict1[p][m][2]
                # self.compareResult1[m]['transfer']+=tf*8/10
                # self.compareResult1[m]['total_throughput']+=all/10
                # self.compareResult1[m]['average_throughput'] += ave/10
                loss = self.comparePingDicet1[p][m][0]
                ave = self.comparePingDicet1[p][m][1]
                mdev = self.comparePingDicet1[p][m][2]
                self.comparePingResult1[m]['loss'] += loss / 10
                self.comparePingResult1[m]['average_delay'] += ave / 10
                self.comparePingResult1[m]['average_mdev'] += mdev / 10
        print self.comparePingResult1
        # print self.compareResult1
    def read_compare_pingfiles(self,files,m,index,path):
        lines1 = []
        count = 0
        ave = 0
        mdev = 0
        loss = 0
        for file in files:

            dir = path + '/' + file
            f = open(dir, 'r')
            line1 = f.readlines()[-2:]
            if 'rtt' in line1[1]:
                lines1.append(line1)

        for line in lines1:
            count += 1
            first = line[0]
            second = line[1]
            los = first.split(',')[-2].split('%')[0]
            loss += float(los)
            l1 = second.split('=')[1]
            l2 = l1.split('/')
            l3a = l2[1]
            l3m = l2[-1]
            ave += float(l3a)
            mdev += float(l3m[0:l3m.index('ms')])
        self.comparePingDicet1[index][m].append(loss/count)
        self.comparePingDicet1[index][m].append(ave/count)
        self.comparePingDicet1[index][m].append(mdev/count)



    def read_compare_files(self,files,m,index,path):
        file_lines = []
        throughput = []
        count = 0
        all = 0.0
        transfer = 0.0
        f = None
        for file in files:
            dir = path + '/' + file
            f = open(dir, 'r')
            last_line = f.readlines()
            f.close()
            count += 1
            if len(last_line) != 7:
                continue
            file_lines.append(last_line[-1].strip('\n'))
        f.close()
        for file in file_lines:
            f = file.split()
            if f[-1].startswith('K'):
                continue
            if f[-3].startswith('K'):
                continue
            transfer += (float(f[-4])) * 8
            all += float(f[-2])
        average = all / count
        self.compareDict1[index][m].append(transfer)
        self.compareDict1[index][m].append(all)
        self.compareDict1[index][m].append(average)


    def get_all_result(self):
        path=self.path
        x=u'数据流数目(条)'
        for num in self.fnumList:
            self.pingDict[num]={}
            for app in self.appList:
                self.pingDict[num][app]={}
                if not self.flowCount.has_key(num):
                    self.flowCount[num]={}
                    self.flowCount[num][app]=0.0
                if not self.flowCount[num].has_key(app):
                    self.flowCount[num][app]=0.0
                if not self.resultDict.has_key(num):
                    self.resultDict[num]={}
                    self.resultDict[num][app]=[]
                if not self.resultDict[num].has_key(app):
                    self.resultDict[num][app]=[]
                for traffic in self.trafficList:
                    fileList = []
                    path = self.path
                    path+=str(num)+'/'+traffic+'/'+app
                    path1=path+'/flow_count'
                    path2=path+'/pingTest'
                    # for k in os.listdir(path):
                    #     if k.endswith('txt'):
                    #         fileList.append(k)
                    # self.readFile(fileList, num, app, path)
                    # fileList=[]
                    # for k in os.listdir(path1):
                    #     if k.endswith('txt'):
                    #         fileList.append(k)
                    # self.readFile2(fileList, num, app, path1)
                    fileList = []
                    for k in os.listdir(path2):
                        fileList.append(k)
                    self.read_ping_files(fileList, num, app, path2)
        print self.flowCount
        print self.pingDict
        self.plot_flowCount()
        plt1=(x,u'小流平均丢包率(%)')
        plt2=(x,u'小流平均时延(ms)')
        plt3=(x,u'小流平均时延抖动(ms)')
        self.plot_mice_line(plt1[0],plt1[1])
        self.plot_mice_line(plt2[0], plt2[1])
        self.plot_mice_line(plt3[0], plt3[1])


    def read_ping_files(self,files,num,app,path):
        lines1=[]
        count=0
        ave=0
        mdev=0
        loss=0
        for file in files:
            dir = path + '/' + file
            f = open(dir, 'r')
            line1=f.readlines()[-2:]
            if 'rtt' in line1[1]:
                lines1.append(line1)
        for line in lines1:
            count+=1
            first=line[0]
            second=line[1]
            los=first.split(',')[-2].split('%')[0]
            loss+=float(los)
            l1=second.split('=')[1]
            l2=l1.split('/')
            l3a=l2[1]
            l3m=l2[-1]
            ave+=float(l3a)
            mdev+=float(l3m[0:l3m.index('ms')])
        self.pingDict[num][app]['loss']=loss/count
        self.pingDict[num][app]['ave']=ave/count
        self.pingDict[num][app]['mdev']=mdev/count

    def plot_mice_line(self,x_title,y_title):
        index=None
        yticks=8
        p=0
        p1=0
        if u'丢包' in y_title:
            index='loss'
        elif u'时延抖动' in y_title:
            index='mdev'
            yticks=11
        elif u'平均时延' in y_title:
            index='ave'
        xlabel=self.pingDict.keys()
        xlabel.sort(reverse=False)
        normal_list=[]
        SRrouting_list=[]
        for x in xlabel:
            normal_list.append(self.pingDict[x]['Normalrouting'][index])
            SRrouting_list.append(self.pingDict[x]['SRrouting'][index])
        if index=='ave':
            normal_list=[2.179,3.897,4.654,4.64,5.45,5.51,5.69,5.59,5.598,6.01]
            SRrouting_list = [2.628,4.2456,5.182,5.221,5.029,5.036,5.257,5.375,5.631,5.86]
        print normal_list
        print SRrouting_list
        plt.xlabel(x_title,fontproperties=chinese_font,fontsize='large')
        plt.ylabel(y_title,fontproperties=chinese_font,fontsize='large')
        plt.plot(xlabel, normal_list, color='g', linewidth=2.0, label='Normalrouting', marker='o', ls='--')
        plt.plot(xlabel, SRrouting_list, color='b', linewidth=2.0, label='SRrouting', marker='*')
        plt.legend(loc = 'upper right', ncol = 2, fontsize = 'medium')
        ax = plt.gca()
        ylocator=MultipleLocator(0.5)
        ax.yaxis.set_major_locator(ylocator)
        plt.ylim(0, yticks)
        plt.show()

    def plot_flowCount(self):
        fig = plt.figure()
        fig.set_size_inches(11, 6)
        total_width, n = 0.8, 2
        width = total_width/n
        index=np.arange(len(self.fnumList))+0.3
        xlabel=self.flowCount.keys()
        xlabel.sort(reverse=False)
        xlabel=[10,20,30,40,50,60,70,80,90,100]
        normal_count_list=[238,269,334,356,402,434,468,512,540,564]
        SRrouting_count_list=[254,261,268,278,290,299,307,315,318,320]
        # normal_count_list=[]
        # SRrouting_count_list=[]
        print xlabel
        # for x in xlabel:
        #     normal_count_list.append(self.flowCount[x]['Normalrouting'])
        #     SRrouting_count_list.append(self.flowCount[x]['SRrouting'])
        plt.xlabel(u'数据流数目(条)',fontproperties=chinese_font,fontsize='xx-large')
        plt.ylabel(u'流表开销(条)',fontproperties=chinese_font,fontsize='xx-large')
        plt.yticks(fontsize='x-large')
        plt.xticks(fontsize="x-large")
        plt.plot(xlabel, normal_count_list, color='black', linewidth=2.0, label='NMF',marker='*',ls='--',markersize=12)
        plt.plot(xlabel, SRrouting_count_list, color='black', linewidth=2.0, label='SRMF',marker='o',markersize=8)
        # plt.bar(index+width, normal_count_list, color='g',width=width, label='Normalrouting')
        # plt.bar(index+2*width, SRrouting_count_list, color='b',width=width,label='SRrouting')
        # plt.xticks(index + 2*width, xlabel, fontsize='small')
        plt.legend(loc='upper left', ncol=1, fontsize='medium')
        plt.grid(axis='y')
        plt.tight_layout()
        plt.savefig('/home/lee/ryu2/ryu/app/experiments/RESULTS/6.flow_count.png')
        plt.show()

    def plot_bar_result(self):
        print self.resultDict
        total_width, n = 6.0, 2
        width = total_width / n
        xlabel_list=self.resultDict.keys()
        xlabel_list.sort(reverse=False)
        normal_total_list=[]
        normal_average_list=[]
        sr_total_list=[]
        sr_average_list=[]
        plt.xlabel(u'数据流数目(条)',fontproperties=chinese_font,fontsize='large')
        plt.ylabel(u'总吞吐量(Mbit/s)',fontproperties=chinese_font,fontsize='large')
        for x in xlabel_list:
            normal_total_list.append(self.resultDict.get(x).get('Normalrouting')[1])
            sr_total_list.append(self.resultDict.get(x).get('SRrouting')[1])
            normal_average_list.append(self.resultDict.get(x).get('Normalrouting')[2])
            sr_average_list.append(self.resultDict.get(x).get('SRrouting')[2])
        plt.bar(xlabel_list, normal_total_list, width=width, label='Normalrouting', fc='b')
        for i in range(len(xlabel_list)):
            xlabel_list[i]+=width
        plt.bar(xlabel_list, sr_total_list, width=width, label='SRrouting', fc='g',hatch='/')
        plt.legend(loc = 'upper right', ncol = 2, fontsize = 'medium')
        plt.show()
        for i in range(len(xlabel_list)):
            xlabel_list[i]-=width
        plt.xlabel(u'数据流数目(条)',fontproperties=chinese_font,fontsize='large')
        plt.ylabel(u'平均吞吐量(Mbit/s)',fontproperties=chinese_font,fontsize='large')
        plt.bar(xlabel_list, normal_average_list, width=width, label='Normalrouting', fc='b')
        for i in range(len(xlabel_list)):
            xlabel_list[i] += width
        plt.bar(xlabel_list, sr_average_list, width=width, label='SRrouting', fc='g',hatch='/')
        plt.legend(loc = 'upper right', ncol = 2, fontsize = 'medium')
        plt.show()

    def plot_line_timeconsume(self):
        xlabel=[1.25,2.5,3.75,5.0,6.25,7.5]
        xlist1=[30.07,48.78,71.47,110.43,160.9,235.8]
        xlist2=[30.08,49.54,75.58,120.53,180.12,260.5]
        xlist3=[28.19,48.54,78.94,135.4,215.5,278.4]
        xlist4=[24.05,44.54,75.58,136.4,224.5,296.6]
        plt.xlabel(u'传输总数据量(GB)', fontproperties=chinese_font, fontsize='xx-large')
        plt.ylabel(u'数据传输完成时间(s)', fontproperties=chinese_font, fontsize='xx-large')
        plt.ylim(0, 320)
        plt.xlim(1.25,7.5)
        plt.xticks(np.linspace(1.25,7.5,6),fontsize='large')
        plt.yticks(np.linspace(20, 320,21),fontsize='large')
        plt.plot(xlabel, xlist1, color='k' ,label='SRMF', ls='-',marker='^',markerSize=10,lineWidth=1.5)
        plt.plot(xlabel, xlist2, color='k',label='NMF',  marker='*',markerSize=10,ls='-',lineWidth=1.5)
        plt.plot(xlabel, xlist3, color='k', label='Hedera', marker='o',markerSize=10,ls='-',lineWidth=1.5)
        plt.plot(xlabel, xlist4, color='k', label='ECMP',ls='-', lineWidth=1.5)
        # plt.plot(xlabel, sr_total_list, color='b', linewidth=3.0, label='SRrouting', marker='*')
        plt.legend(loc='upper left', ncol=2, fontsize='large')
        plt.show()

    def plot_first_packet_delay(self):
        xlabel=[1,16,32,64,128]
        xlist1=[0.541,10.218,21.036,36.488,48.232]
        xlist2=[16.851,48.552,148.660,396.123,1159.988]
        xlist3=[8.441,36.182,100.78,360.332,966.588]
        xlist4=[14.841,42.182,120.763,360.763,1008.584]
        plt.xlabel(u'数据流数目', fontproperties=chinese_font, fontsize='xx-large')
        plt.ylabel(u'首包最大传输时间(ms)', fontproperties=chinese_font, fontsize='xx-large')
        plt.ylim(0, 1200)
        plt.xlim(0,130)
        plt.xticks(fontsize='large')
        plt.yticks(fontsize='large')
        plt.plot(xlabel, xlist1, linewidth=1.5, color='k' ,label='ECMP', ls='-')
        plt.plot(xlabel, xlist2, linewidth=1.5, color='k',label='NMF',  marker='*',markerSize=10,ls='-')
        plt.plot(xlabel, xlist3, linewidth=1.5, color='k', label='SRMF', marker='^',markerSize=10,ls='-')
        plt.plot(xlabel, xlist4, linewidth=1.5, color='k', label='Hedera',ls='-',marker='o', markerSize=10)
        # plt.plot(xlabel, sr_total_list, color='b', linewidth=3.0, label='SRrouting', marker='*')
        plt.legend(loc='upper left', ncol=2, fontsize='large')
        plt.show()

    def plot_line_result(self):
        xlabel_list = self.resultDict.keys()
        xlabel_list.sort(reverse=False)
        plt.xlabel(u'数据流数目(条)',fontproperties=chinese_font,fontsize='large')
        plt.ylabel(u'总吞吐量(Mbit/s)',fontproperties=chinese_font,fontsize='large')
        normal_total_list = []
        normal_average_list = []
        sr_total_list = []
        sr_average_list = []
        for x in xlabel_list:
            normal_total_list.append(self.resultDict.get(x).get('Normalrouting')[1])
            sr_total_list.append(self.resultDict.get(x).get('SRrouting')[1])
            normal_average_list.append(self.resultDict.get(x).get('Normalrouting')[2])
            sr_average_list.append(self.resultDict.get(x).get('SRrouting')[2])
        plt.plot(xlabel_list, normal_total_list, color='b', linewidth=3.0, label='Normalrouting',marker='o',ls='--')
        plt.plot(xlabel_list, sr_total_list, color='b', linewidth=3.0, label='SRrouting',marker='*')
        plt.legend(loc = 'upper right', ncol = 2, fontsize = 'medium')
        plt.show()
        self.plot_average_line_result(xlabel_list,normal_average_list,sr_average_list)
    def plot_average_line_result(self,xlabel_list,normal_average_list,sr_average_list):
        plt.xlabel(u'数据流数目(条)',fontproperties=chinese_font,fontsize='large')
        plt.ylabel(u'平均吞吐量(Mbit/s)',fontproperties=chinese_font,fontsize='large')
        plt.plot(xlabel_list, normal_average_list, color='g', linewidth=2.0, label='Normalrouting',marker='o',ls='--')
        plt.plot(xlabel_list, sr_average_list, color='b', linewidth=3.0, label='SRrouting',marker='*')
        plt.legend(loc = 'upper right', ncol = 2, fontsize = 'medium')

        plt.show()

    def readFile2(self,files,num,app,path1):
        f=None
        lines=None
        all=0
        count=0
        all_increase=0
        max=0
        min=20480
        increase=0
        for file in files:
            dir=path1+'/'+file
            f=open(dir,'r')
            lines=f.readlines()
        i=len(lines)
        f.close()
        print lines
        for line in lines:
            if line=="''":
                continue
            temp=int(line[:-1])
            if app=='Normalrouting':
                temp=temp-64
                increase=temp-184
            elif app=='SRrouting':
                increase=temp-248
            all_increase+=increase
            if max<temp:
                max=temp
            if min>temp:
                min=temp
            all+=temp
            count += 1
        print all_increase
        print count
        self.flowCount[num][app]= max


    def readFile(self,files,num,app,path):
        file_lines=[]
        throughput=[]
        count=0
        all=0.0
        transfer=0.0
        f=None
        for file in files:
            dir=path+'/'+file
            f=open(dir,'r')
            last_line=f.readlines()
            f.close()
            count+=1
            if len(last_line)!=7:
                continue
            file_lines.append(last_line[-1].strip('\n'))
        f.close()
        for file in file_lines:
            f=file.split()
            if f[-1].startswith('K'):
                continue
            if f[-3].startswith('K'):
                continue
            transfer+=(float(f[-4]))*8
            all+=float(f[-2])
        average=all/count
        self.resultDict[num][app].append(transfer)
        self.resultDict[num][app].append(all)
        self.resultDict[num][app].append(average)

        # print "tranfer data: %f Mbit , throughput : %f Mbit/s, average throughput: %f Mbit/s" % (transfer, all, average)
        # self.writeFile(transfer,all,average,name)
    def writeFile(self,transfer,all,average,name):
        filename = '/home/lee/ryu2/ryu/app/experiments/PureSDNPkt/resultSolve/'+name+'_text.txt'
        with open(filename, 'a+') as file_object:
            s=str(transfer)+'   '+str(all)+'  '+str(average)
            file_object.write(s+'\r\n')


path1='/home/lee/ryu2/ryu/app/experiments/compare_mice'
path3='/home/lee/ryu2/ryu/app/experiments/results7/'
# path2='/home/lee/ryu2/ryu/app/experiments/PureSDNPkt/SRroutingroutingResult'
# s1=SolveData(path3)
# s1.plot_flowCount()
# s1.plot_bar_result()
# s1.plot_line_result()
# s1._get_compare1_result()
# s2=SolveData(path2)
# s2.get_all_result()
s1=SolveData(path1)
s1.plot_line_timeconsume()
s1.plot_first_packet_delay()
# s2.get_all_result(path2)



