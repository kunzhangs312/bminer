import asyncio
import json
import random
import subprocess
import time
import uuid
from copy import deepcopy
from threading import Thread
import redis

AUTO_RESET_TIMEOUT = 20 * 60        # 自动恢复超时时间(s)，防止当服务器超时关闭后，矿机一直陷入非listen状态，无法接收新的任务。


class SubMessage(object):
    def __init__(self, host="47.106.253.159", port=6379, db=3, password='sjdtwigkvsmdsjfkgiw23usfvmkj2'):
        self.subscribe_task_channel = "BrokerMachineChannel"
        self.publish_task_channel = "MachineBrokerChannel"
        self.subscribe_channel = None
        self.publish_channel = None
        self.pool = redis.ConnectionPool(host=host, port=port, db=db, password=password)
        self.conn = redis.Redis(connection_pool=self.pool)
        self.ps = self.conn.pubsub()
        self._loop = asyncio.new_event_loop()
        node = uuid.getnode()
        self.mac = uuid.UUID(int=node).hex[-12:]
        self.syn = random.randint(10, 100000)
        self.ack = None
        self.state = "INITIALIZE"  # ["INITIALIZE", "LISTEN", "RESPONSE_SYNCHRONIZE", "RESPONSE_ACKNOWLEDGE",
                                   #  "EXECUTING", "FINISH_SYNCHRONIZE", "FINISH_ACKNOWLEDGE"]
        self.taskid = None  # 正在执行的指令ID
        self.parameter = None
        self._start_time = None

    def is_json(myjson):
        try:
            json.loads(myjson)
        except ValueError:
            return False
        return True

    @staticmethod
    def start_loop(loop):
        asyncio.set_event_loop(loop)
        loop.run_forever()

    def start_thread(self):
        t = Thread(target=self.start_loop, args=(self._loop,))
        t.setDaemon(True)
        t.start()

    def timeout(self):
        """检查任务是否超时，如果超时，则复位任务"""
        now = time.time()
        if (now-self._start_time) >= AUTO_RESET_TIMEOUT:
            self.taskid = None
            self.parameter = None
            self._start_time = None
            self.state = "LISTEN"

            # reset subscribe and publish channel
            self.ps.close()
            self.subscribe_channel = None
            self.publish_channel = None
            self.ps.subscribe(self.subscribe_task_channel)
            return True
        else:
            return False

    def receive(self):
        """
        该方法从服务器端接收到执行命令，数据格式如下：
        {"action":"", "parameter":{}, "maclist":[], "taskid":""}
        """
        print("machine mac: {}, start receive task from server ...".format(self.mac))

        # 监听machine_channel通道，等待服务器下发操作指令
        self.ps.subscribe(self.subscribe_task_channel)
        self.state = "LISTEN"
        while True:
            # 监听subscribe_channel通道，等待矿机的应答
            mess = self.ps.get_message(timeout=1.0)
            if mess is None:
                continue

            if mess and mess['type'] == 'message':
                try:
                    receive_data = eval(mess['data'])
                except Exception as error:
                    print(error)
                    continue

            resp_mac_list = receive_data.get('maclist', None)
            print("receive new task: ", receive_data)
            if self.mac in resp_mac_list:
                if self.state == "LISTEN":
                    # 创建一个协程发送同步响应，并等待服务器的应答
                    print("in LISTEN")
                    if self.taskid == receive_data.get("taskid", None):     # 跳过已经执行或者正在执行的指令
                        continue
                    self.taskid = receive_data.get("taskid", None)
                    self._start_time = time.time()                          # 记录该任务开始执行的时间

                    if self.taskid:         # 更换订阅和发布通道
                        self.ps.close()
                        self.subscribe_channel = self.subscribe_task_channel + self.taskid.upper()
                        self.publish_channel = self.publish_task_channel + self.taskid.upper()
                        print("change subscribe and publish channel")
                        self.ps.subscribe(self.subscribe_channel)

                    self.parameter = receive_data.get("parameter", None)
                    print("change state to RESPONSE_SYNCHRONIZE")
                    self.state = "RESPONSE_SYNCHRONIZE"
                    asyncio.run_coroutine_threadsafe(self.response_synchronize(), self._loop)
                elif self.state == "RESPONSE_SYNCHRONIZE":
                    print("in RESPONSE_SYNCHRONIZE")

                    # 检查当前的任务是否超时
                    if self.timeout():
                        continue

                    if self.taskid != receive_data.get("taskid", None):     # 跳过不是当前执行的指令
                        continue

                    # 参数检查
                    if not self.check_response(deepcopy(receive_data), resp_type="confirm"):
                        continue
                    print("change state to RESPONSE_ACKNOWLEDGE")
                    self.state = "RESPONSE_ACKNOWLEDGE"     # 修改状态机的状态，终止synchronize方法持续发送同步信息
                    # 创建一个协程完成服务器下发的指令
                    asyncio.run_coroutine_threadsafe(self.handler(deepcopy(receive_data)), self._loop)
                elif self.state == "FINISH_SYNCHRONIZE":
                    print("in FINISH_SYNCHRONIZE")

                    # 检查当前任务是否超时
                    if self.timeout():
                        continue

                    if self.taskid != receive_data.get("taskid", None):     # 跳过不是当前执行的指令
                        continue

                    # 参数检查
                    if not self.check_response(deepcopy(receive_data), resp_type="completed"):
                        continue
                    print("change state to FINISH_ACKNOWLEDGE")
                    self.state = "FINISH_ACKNOWLEDGE"       # 修改状态机的状态，终止synchronize方法持续发送同步信息
                    print("change state to LISTEN")
                    self.state = "LISTEN"                   # 将状态机恢复到LISTEN状态，准备接收服务器的操作指令

                    # 更换订阅和发布通道，等待下一个任务的到来
                    self.ps.close()
                    self.subscribe_channel = None
                    self.publish_channel = None
                    print("reset subscribe and publish channel")
                    self.ps.subscribe(self.subscribe_task_channel)
                else:
                    if self.timeout():
                        continue

    async def response_synchronize(self, result=None):
        """
        将数据发送给服务器，并等待服务器的应答
        :return:
        """
        if self.state != "RESPONSE_SYNCHRONIZE":
            return

        if self.publish_channel[-8:] != self.taskid.upper():
            return

        response_data = {"taskid": self.taskid, "maclist": [self.mac], "resp_type": "confirm", "syn": self.syn}

        # response_data_str = json.dumps(response_data)
        while self.state == "RESPONSE_SYNCHRONIZE":
            print("state: {0},channel-{1} send synchronize: {2}".format(self.state, self.publish_channel, response_data))
            self.conn.publish(self.publish_channel, response_data)
            await asyncio.sleep(1)

    async def finish_synchronize(self, result=None):
        """
        将数据发送给服务器，并等待服务器的应答
        :return:
        """
        if self.state != "FINISH_SYNCHRONIZE":
            return

        if self.publish_channel[-8:] != self.taskid.upper():
            return

        response_data = {"taskid": self.taskid, "maclist": [self.mac],
                         "resp_type": "completed", "syn": self.syn, "result": result}

        # response_data_str = json.dumps(response_data)
        while self.state == "FINISH_SYNCHRONIZE":
            print("state: {0},channel-{1} send synchronize: {2}".format(self.state, self.publish_channel, response_data))
            self.conn.publish(self.publish_channel, response_data)
            await asyncio.sleep(1)

    def check_response(self, receive_data, resp_type):
        """
        对服务器的同步信息的应答做检查
        :param receive_data:
        :param resp_type:
        :return:
        """
        if receive_data.get('taskid', None) != self.taskid or \
                receive_data.get('ack', None) != self.syn + 1 or \
                receive_data.get('resp_type', None) != resp_type:
            return False

        return True

    async def handler(self, receive_data):
        """
        完成服务器下发的操作指令
        :param receive_data:
        :return:
        """
        if self.state != "RESPONSE_ACKNOWLEDGE":
            return
        else:
            print("change state to EXECUTING")
            self.state = "EXECUTING"
            parameter = self.parameter
            result = self.process(self.mac, parameter)
            # 给服务器发送指令完成的同步信息
            print("change state to FINISH_SYNCHRONIZE")
            self.state = "FINISH_SYNCHRONIZE"
            asyncio.run_coroutine_threadsafe(self.finish_synchronize(result), self._loop)

    def run_forever(self):
        self.start_thread()
        self.receive()

    def process0(self, mac, action, parameter):
        if action == 'ConfigRestart':       # 配置并重启

            pass
        elif action == 'RestartMining':     # 重启挖矿
            pass
        elif action == 'PauseMining':       # 暂停挖矿
            pass
        elif action == 'Shelve':            # 下架矿机
            pass
        elif action == 'Overclock':         # 主机超频
            pass
        elif action == 'Restart':           # 重启矿机
            pass
        else:
            return False
        pass

    def process(self, mac0, data):
        try:
            data = str(data, encoding='utf-8')
            message = json.loads(data)
            mac = message['mac']
            id = data["id"]
            userid = data["userid"]
            operate = data["operate"]
            if mac0 == mac:
                time_ = message['time']
                # set a timeout 5 min
                now = int(time.time())
                timeout = now - time_
                if timeout < 5 * 60:
                    type = data["type"]
                    if type == "miner":
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
                            p = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE)
                            stdout, _ = p.communicate()
                            out = stdout.decode('utf-8')
                            if self.is_json(out):
                                return json.loads(out)
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
                            p = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE)
                            stdout, _ = p.communicate()
                            out = stdout.decode('utf-8')
                            if self.is_json(out):
                                return json.loads(out)
                    elif type == "operate":
                        operate = data['operate']
                        if operate == "stop":
                            kill = data["kill"]
                            cmd = "python3 ./operate-script/stop.py " + kill + " " + userid + " " + id
                            p = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE)
                            stdout, _ = p.communicate()
                            out = stdout.decode('utf-8')
                            if self.is_json(out):
                                return json.loads(out)
                        elif operate == "remove":
                            kill = data["kill"]
                            cmd = "python3 ./operate-script/remove.py " + kill + " " + userid + " " + id
                            p = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE)
                            stdout, _ = p.communicate()
                            out = stdout.decode('utf-8')
                            if self.is_json(out):
                                return json.loads(out)
                        elif operate == "reboot":
                            cmd = "python3 ./operate-script/reboot.py " + userid + " " + id
                            p = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE)
                            stdout, _ = p.communicate()
                            out = stdout.decode('utf-8')
                            if self.is_json(out):
                                return json.loads(out)
                        elif operate == "shutdown":
                            cmd = "python3 ./operate-script/shutdown.py " + userid + " " + id
                            p = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE)
                            stdout, _ = p.communicate()
                            out = stdout.decode('utf-8')
                            if self.is_json(out):
                                return json.loads(out)
                    elif type == "others":
                        cmd = data['operate']
                        p = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE)
                        stdout, _ = p.communicate()
                        out = stdout.decode('utf-8')
                        if self.is_json(out):
                            return json.loads(out)
                else:
                    resp = {"mac":mac,"time":time.time(),"id":id,"userid":userid,"status":"命令超时","program":"null","operate_name":operate}
                    return resp
            else:
                resp = {"mac": mac, "time": time.time(), "id": id, "userid": userid, "status": "MAC匹配错误", "program": "null", "operate_name": operate}
                return resp
        except Exception as e:
            print(e)

if __name__ == '__main__':
    submessage = SubMessage()
    submessage.run_forever()