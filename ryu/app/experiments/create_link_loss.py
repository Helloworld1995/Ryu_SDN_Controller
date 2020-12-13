import random

def create_links_loss():
    host2edge=random.uniform(0,0.33)
    edge2agg=random.uniform(0.67,1)
    agg2core=random.uniform(0.33,0.67)
    list=[]
    list.append(host2edge)
    list.append(edge2agg)
    list.append(agg2core)
    writeFile(list)
def writeFile(list):
    file_save = open('link_loss.txt', 'w+')
    file_save.write(str(list)[1:-1])
    file_save.close()
if __name__ == '__main__':
    create_links_loss()