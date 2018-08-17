# -*- coding:utf-8 -*-
from pykafka import KafkaClient
import json
import os
import time
import uuid
import subprocess
import sys

def main():
    params_str = """{"id":24774,"service_type":"AION","status":0,"on":true,"config":{"GpuNum":1,"Version":3,"Overclock":1,"Program":"ewbf-miner-new","Algorithm":"ethash","Extra":"","IsManualPool":0,"Primary":{"CoinName":"aion","WalletAddress":"0xa0c238f3b427320e5231e8703335fe52620895b08ded92fcd05f9775698bc321","PoolAddress":"aion.f2pool.com:6677","PoolName":"uupool.cn","Algorithm":"","IsUserAddr":false,"CurrentPoolAddr":"","CurrentPoolPort":0,"Status":0},"Secondary":{"CoinName":"","WalletAddress":"","PoolAddresses":null,"PoolName":"","Algorithm":"","IsUserAddr":false,"CurrentPoolAddr":"","CurrentPoolPort":0,"Status":0},"MinerPrefix":"92","MinerPostfix":"92","App":{"Name":"","Version":""}},"overclock_info":{"cpu":{"frequency":2800000,"frequencey":0},"gpu":[{"Id":0,"BusID":"","Level":3,"PowerLimit":117,"GPUGraphicsClockOffset":0,"GPUMemoryTransferRateOffset":1000,"GPUTargetFanSpeed":0}],"fan":[{"Id":0,"BusID":"0000:01:00.0","GPUTargetFanSpeed":90}]}}
    """
    params_str = sys.argv[1]
    # 1.解析参数
    params = json.loads(params_str)
    program = params["config"]["Program"]
    shell_name = program+".sh"

    # 2.写入shell脚本
    file = os.path.isfile("./"+shell_name)
    if not file:
        os.mknod(shell_name)
        os.chmod(shell_name,755)
    else:
        fp = open(shell_name,"w")
        fp.truncate()
    with open(shell_name,"r+") as f:
        f.write("# !/bin/sh \n")
        f.write("python3 ../miner-script/"+program+"/"+program+".py "+params_str+" \n")
    f.close()

    # 3.吊起shell脚本执行
    subprocess.Popen("sh ./" + shell_name, shell=True, stdout=subprocess.PIPE)

    # 4.检查执行是否起来
    time.sleep(10)
    lines = os.popen('ps -ef|grep ' + program)
    lines = lines.readlines()
    status = "异常"
    if len(lines)>2:
        status = "正常"
    # 5.上报操作数据
    def getMac():
        node = uuid.getnode()
        mac = uuid.UUID(int=node).hex[-12:]
        return mac
    producer = None
    try:
        client = KafkaClient(hosts="192.168.0.69:9092")
        topic = client.topics[b'operate']
        producer = topic.get_producer()
        mac = getMac()
        userid = sys.argv[2]
        id = sys.argv[3]
        str_ = {"id": id, "userid": userid,"operator_type": "start", "status": status, "mac": mac, "time": time.time(),"program":program,"operate_name":"start"}
        json_info = json.dumps(str_)
        producer.produce(bytes(json_info, encoding="utf8"))
        print(json_info)
    except Exception as e:
        print(e)
    finally:
        producer.stop()

if __name__ == '__main__':
    if len(sys.argv)<4:
        print("please input the params name")
    else:
        main()