# -*- coding: UTF-8 -*-
import pymysql
from DBUtils.PooledDB import PooledDB, SharedDBConnection
class Dbutil:



    POOL = PooledDB(
        creator=pymysql,  #使用链接数据库的模块
        maxconnections=6,  # 连接池允许的最大连接数，0和None表示不限制连接数
        mincached=2,  # 初始化时，链接池中至少创建的空闲的链接，0表示不创建
        maxcached=5,  # 链接池中最多闲置的链接，0和None不限制
        maxshared=3,  # 链接池中最多共享的链接数量，0和None表示全部共享。PS: 无用，因为pymysql和MySQLdb等模块的 threadsafety都为1，所有值无论设置为多少，_maxcached永远为0，所以永远是所有链接都共享。
        blocking=True,  # 连接池中如果没有可用连接后，是否阻塞等待。True，等待；False，不等待然后报错
        maxusage=None,  # 一个链接最多被重复使用的次数，None表示无限制
        setsession=[],  # 开始会话前执行的命令列表。如：["set datestyle to ...", "set time zone ..."]
        ping=0,
        # ping MySQL服务端，检查是否服务可用。# 如：0 = None = never, 1 = default = whenever it is requested, 2 = when a cursor is created, 4 = when a query is executed, 7 = always
        host='127.0.0.1',
        port=3306,
        user='root',
        password='1234',
        database='SDN_project',
        charset='utf8'
    )

    def select(self,ip_src):
        # 检测当前正在运行连接数的是否小于最大链接数，如果不小于则：等待或报raise TooManyConnections异常
        # 否则
        # 则优先去初始化时创建的链接中获取链接 SteadyDBConnection。
        # 然后将SteadyDBConnection对象封装到PooledDedicatedDBConnection中并返回。
        # 如果最开始创建的链接没有链接，则去创建一个SteadyDBConnection对象，再封装到PooledDedicatedDBConnection中并返回。
        # 一旦关闭链接后，连接就返回到连接池让后续线程继续使用。

        # PooledDedicatedDBConnection
        conn = self.POOL.connection()

        # print(th, '链接被拿走了', conn1._con)
        # print(th, '池子里目前有', pool._idle_cache, '\r\n')

        cursor = conn.cursor()
        #cursor.execute("insert into accont(name,ip_address,userGrade) values('%s','%s','%s')" %('lee','10.1.0.1','gold'))

        # cursor.execute(
        #     "insert into accont(name,ip_address,userGrade) values('%s','%s','%s')" % ('wong', '10.1.0.2', 'gold'))
        cursor.execute("select id from account where ip_src='%s'" % (ip_src))
        result=cursor.fetchone()
        # conn.commit()
        # print(result)
        return result
        conn.close()

    def insert(self,id,src,dst,path):
        conn=self.POOL.connection()
        cursor=conn.cursor()
        cursor.execute("insert into path(userid,ip_src,ip_dst,path) values(%d,'%s','%s','%s')"%(id,src,dst,path))
        conn.commit()
        conn.close()


