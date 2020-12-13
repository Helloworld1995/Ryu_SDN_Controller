import socket


class socketTest():
    def __init__(self):
        self.port=9991
        self.ip="192.168.16.128"
        self.s=socket.socket()
        self.s.bind((self.ip,self.port))
    def socketRun(self,data):

        conn,addr=self.s.accept()
        conn.send(data.decode("utf-8"))
        print "send success!"



