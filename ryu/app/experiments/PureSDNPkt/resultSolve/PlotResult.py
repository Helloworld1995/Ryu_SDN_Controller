# -*- coding: utf-8 -*-
import matplotlib.pyplot as plt
plt.rcParams['font.sans-serif']=['SimHei']

def plot_bar_result(name_list,num_list,num_list2,ylabel):

    x = list(range(len(num_list)))
    total_width, n = 0.8, 2
    width = total_width / n
    plt.bar(x, num_list, width=width, label='Normal', fc='b')
    plt.xlabel('number of flows ')
    plt.ylabel(ylabel)
    for i in range(len(x)):
        x[i] += width
    plt.bar(x, num_list2, width=width, label='SR', tick_label=name_list, fc='g')
    plt.legend(loc=2)
    plt.show()
def plot_line_result(name_list,num_list,num_list2,ylabel):

    plt.xlabel('number of flows ')
    plt.ylabel(ylabel)
    plt.plot(name_list, num_list, color='red', linewidth=2.0, label='Normal')
    plt.plot(name_list, num_list2, color='blue', linewidth=3.0, label='SR')
    plt.legend(loc=2)
    plt.show()

name_list = ['25', '50', '75', '100','125']
num_list = [3.8632, 5.184, 4.168, 3.5124, 3.35932,]
num_list2 = [3.6432, 5.2398, 4.4429, 3.5272,3.19192]
ylabel='average throughput (Mbit/s)'
plot_bar_result(name_list,num_list,num_list2,ylabel)