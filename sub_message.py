import redis
import json
import time
import subprocess
import random

MAC = None
SYN = None

def getMac():
    import uuid
    node = uuid.getnode()
    mac = uuid.UUID(int=node).hex[-12:]
    return mac

def process(mac0, data):
    try:
        data = str(data,encoding='utf-8')
        message = json.loads(data)
        mac = message['mac']
        if mac0 == mac:
            time_ = message['time']
            # set a timeout 5 min
            now = int(time.time())
            timeout = now-time_
            if timeout<5*60 :
                type = data["type"]
                id = data["id"]
                userid = data["userid"]
                if type=="miner":
                    operate = data["operate"]
                    if operate == "start":
                        params = data["params"]
                        Overclock = params["Overclock"]
                        json_str = json.dumps(params)
                        if Overclock is not None and Overclock == 1:
                            overclock_info = data['overclock_info']
                            if overclock_info is not None:
                                cmd = "python3 ./operate-script/overlock.py "+json_str
                                subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE)
                        else:
                            cmd = "python3 ./operate-script/notoverlock.py"
                            subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE)
                        cmd = "python3 ./operate-script/start.py "+json_str +" "+userid+" "+id
                        subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE)
                    elif operate == "restart":
                        kill = data["kill"]
                        if kill is not None:
                            cmd = "python3 ./operate-script/stop.py "+kill +" "+userid+" "+id
                            subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE)
                        params = data["params"]
                        Overclock = params["Overclock"]
                        json_str = json.dumps(params)
                        if Overclock is not None and Overclock == 1:
                            overclock_info = data['overclock_info']
                            if overclock_info is not None:
                                cmd = "python3 ./operate-script/overlock.py "+json_str
                                subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE)
                        else:
                            cmd = "python3 ./operate-script/notoverlock.py"
                            subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE)
                        cmd = "python3 ./operate-script/start.py " + json_str
                        subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE)
                elif type=="operate":
                    operate = data['operate']
                    kill = data["kill"]
                    if operate == "stop":
                        cmd = "python3 ./operate-script/stop.py " + kill + " " + userid+" "+id
                        subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE)
                    elif operate == "remove":
                        cmd = "python3 ./operate-script/remove.py " + kill + " " + userid+" "+id
                        subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE)
                    elif operate == "reboot":
                        cmd = "python3 ./operate-script/reboot.py " + userid + " " + id
                        subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE)
                    elif operate == "shutdown":
                        cmd = "python3 ./operate-script/shutdown.py " + userid + " " + id
                        subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE)
                elif type=="others":
                    cmd = data['operate']
                    subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE)
    except Exception as e:
        print(e)

if __name__ == '__main__':
    pool = redis.ConnectionPool(host='47.106.253.159', port='6379', db=0, password='sjdtwigkvsmdsjfkgiw23usfvmkj2')
    conn = redis.Redis(connection_pool=pool)
    if MAC is None:
        MAC = getMac()
    channel = MAC[0:2] + "_miner_channel"
    ps = conn.pubsub()
    ps.subscribe(channel)
    for item in ps.listen():
        if item['type'] == 'message':
            data = item['data']
            data = str(data, encoding='utf-8')
            message = json.loads(data)
            maclist = message['maclist']
            if MAC in maclist:
                taskid = message['taskid']
                SYN = random.randint(0, 100000000)
                response = '{"taskid":'+taskid+', "maclist":["'+MAC+'"], "syn":'+SYN+'}'
                conn.publish("BrokerMachineChannel", response)
                time.sleep(0.5)
                ps.subscribe("BrokerMachineChannel")
                for _item_ in ps.listen():
                    if _item_['type'] == 'message':
                        data = _item_['data']
                        data = str(data, encoding='utf-8')
                        message = json.loads(data)
                        maclist = message['maclist']
                        ack = message['ack']
                        if MAC in maclist and ack==SYN+1:
                            parameter = message['parameter']
                            process(MAC, parameter)
                            break
                        else:
                            conn.publish("BrokerMachineChannel", response)
                            time.sleep(1)
                    else:
                        conn.publish("BrokerMachineChannel", response)
                        time.sleep(1)