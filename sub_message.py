import redis
import json
import time
import subprocess
import random
import asyncio
from threading import Thread
import uuid

class SubMessage(object):
    def __init__(self,host="47.106.253.159",port=6379,db=0,password='sjdtwigkvsmdsjfkgiw23usfvmkj2'):
        self.machine_channel = "BrokerMachineChannel"
        self.pool = redis.ConnectionPool(host=host, port=port, db=db,password=password)
        self.conn = redis.Redis(connection_pool=self.pool)
        self.ps = self.conn.pubsub()
        self._loop = asyncio.new_event_loop()
        node = uuid.getnode()
        self.mac = uuid.UUID(int=node).hex[-12:]
        self.syn = None
        self.ack = None

    @staticmethod
    def start_loop(loop):
        asyncio.set_event_loop(loop)
        loop.run_forever()

    def start_thread(self):
        t = Thread(target=self.start_loop,args=(self._loop,))
        t.setDaemon(True)
        t.start()

    def receive(self):
        """
        该方法从服务器端接收到执行命令，数据格式如下：
                {"action":"", "parameter":{}, "maclist":[], "taskid":""}
        """
        while True:
            receive_data = self.conn.brpop(self.machine_channel,timeout=0)
            receive_data = receive_data[1].decode()
            receive_data = eval(receive_data)
            # 创建一个协程完成与服务器的所有交互
            asyncio.run_coroutine_threadsafe(self.handler(receive_data),self._loop)

    async def handler(self,receive_data):
        """
        该方法从Redis通道“BrokerMachineChannel”中获得操作命令，完成与服务器交互的整个过程。
        :param receive_data:
        :return:
        """
        # 首先判断消息是否需要进行处理
        maclist = receive_data['maclist']
        if self.mac in maclist:
            # 创建一个协程完成接收到命令的回报通知
            self.syn = random.randint(0, 100000000)
            response_data = {"taskid":receive_data['taskid'], "maclist":[self.mac], "resp_type":"confirm", "syn":self.syn}
            response_data_str = json.dumps(response_data)
            asyncio.run_coroutine_threadsafe(self.handler_publish(response_data_str),self._loop)
            # 监听 BrokerMachineChannel 通道，等待服务器的应答
            handle_taskid = receive_data['taskid']
            self.ps.subscribe(self.machine_channel)
            for item in self.ps.listen():
                if item['type'] == 'message':
                    resp_dict = eval(item['data'])
                    resp_taskid = resp_dict.get('taskid', None)
                    if handle_taskid != resp_taskid:
                        continue
                    resp_mac_list = resp_dict.get('maclist', None)
                    if not len(resp_mac_list):
                        print("machine return data maclist is blank!")
                        continue
                    resp_mac = resp_mac_list[0]
                    if resp_mac != self.mac:
                        continue
                    ack = resp_dict.get('ack', None)
                    if self.syn+1 != ack:
                        continue
                    resp_type = resp_dict.get('resp_type', None)
                    if resp_type != 'confirm':
                        continue
                    syn = resp_dict.get('syn', None)
                    self.handler_response(resp_dict,resp_type,syn)

    def handler_response(self,data,resp_type,syn):
        """
        矿机执行命令，然后给服务器发送完成的命令
        :param data:
        :param resp_type:
        :param syn:
        :return:
        """
        parameter = data['parameter']
        self.process(self.mac,parameter)
        # 给服务器发送完成的命令
        data['resp_type'] = 'completed'
        self.handler_publish(self.machine_channel,data)

    async def handler_publish(self,data,count=3):
        """用来给服务器发布回报通知，连续发3次，间隔逐渐增大"""
        for cnt in range(count):
            self.conn.publish(self.machine_channel,data)
            time.sleep(cnt)

    def run_forver(self):
        self.start_thread()
        self.receive()

    def process(self,mac0,data):
        try:
            data = str(data, encoding='utf-8')
            message = json.loads(data)
            mac = message['mac']
            if mac0 == mac:
                time_ = message['time']
                # set a timeout 5 min
                now = int(time.time())
                timeout = now - time_
                if timeout < 5 * 60:
                    type = data["type"]
                    id = data["id"]
                    userid = data["userid"]
                    if type == "miner":
                        operate = data["operate"]
                        if operate == "start":
                            params = data["params"]
                            Overclock = params["Overclock"]
                            json_str = json.dumps(params)
                            if Overclock is not None and Overclock == 1:
                                overclock_info = data['overclock_info']
                                if overclock_info is not None:
                                    cmd = "python3 ./operate-script/overlock.py " + json_str
                                    subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE)
                            else:
                                cmd = "python3 ./operate-script/notoverlock.py"
                                subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE)
                            cmd = "python3 ./operate-script/start.py " + json_str + " " + userid + " " + id
                            subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE)
                        elif operate == "restart":
                            kill = data["kill"]
                            if kill is not None:
                                cmd = "python3 ./operate-script/stop.py " + kill + " " + userid + " " + id
                                subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE)
                            params = data["params"]
                            Overclock = params["Overclock"]
                            json_str = json.dumps(params)
                            if Overclock is not None and Overclock == 1:
                                overclock_info = data['overclock_info']
                                if overclock_info is not None:
                                    cmd = "python3 ./operate-script/overlock.py " + json_str
                                    subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE)
                            else:
                                cmd = "python3 ./operate-script/notoverlock.py"
                                subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE)
                            cmd = "python3 ./operate-script/start.py " + json_str
                            subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE)
                    elif type == "operate":
                        operate = data['operate']
                        kill = data["kill"]
                        if operate == "stop":
                            cmd = "python3 ./operate-script/stop.py " + kill + " " + userid + " " + id
                            subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE)
                        elif operate == "remove":
                            cmd = "python3 ./operate-script/remove.py " + kill + " " + userid + " " + id
                            subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE)
                        elif operate == "reboot":
                            cmd = "python3 ./operate-script/reboot.py " + userid + " " + id
                            subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE)
                        elif operate == "shutdown":
                            cmd = "python3 ./operate-script/shutdown.py " + userid + " " + id
                            subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE)
                    elif type == "others":
                        cmd = data['operate']
                        subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE)
        except Exception as e:
            print(e)

if __name__ == '__main__':
    submessage = SubMessage()
    submessage.run_forver()