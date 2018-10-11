# -*- coding:utf-8 -*-
import json
import os
import time
import uuid
import subprocess
import sys

def main():
    params_str = """{"id":24774,"service_type":"Zcash","status":0,"on":true,"config":{"Version":3,"Overclock":1,"Program":"xmrig-amd","Algorithm":"ethash","Extra":"","IsManualPool":0,"Primary":{"CoinName":"eth","WalletAddress":"48LHRj3T9Jfeq87sikft1ijRzuGjo5w21ALP5gnvPeTkdqGgh2qQo7LXwKpuFDnoEUWhyHZrWsiuxVqHkAikyAuo1t9y5zE","PoolAddress":"xmr.f2pool.com:13531","PoolName":"uupool.cn","Algorithm":"","IsUserAddr":false,"CurrentPoolAddr":"","CurrentPoolPort":0,"Status":0},"Secondary":{"CoinName":"","WalletAddress":"","PoolAddresses":null,"PoolName":"","Algorithm":"","IsUserAddr":false,"CurrentPoolAddr":"","CurrentPoolPort":0,"Status":0},"MinerPrefix":"92","MinerPostfix":"92","App":{"Name":"","Version":""}},"overclock_info":{"cpu":{"frequency":2800000,"frequencey":0},"gpu":[{"Id":0,"BusID":"","Level":3,"PowerLimit":117,"GPUGraphicsClockOffset":0,"GPUMemoryTransferRateOffset":1000,"GPUTargetFanSpeed":0}],"fan":[{"Id":0,"BusID":"0000:01:00.0","GPUTargetFanSpeed":90}]}}"""
    # params_str = sys.argv[1]
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
        f.write("python3 /opt/miner/iMiner/miner-script/"+program+"/"+program+".py "+params_str+" \n")
    f.close()

    # 3.吊起shell脚本执行
    subprocess.Popen("sh ./" + shell_name, shell=True, stdout=subprocess.PIPE)

    # 4.检查执行是否起来
    time.sleep(3)
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
    try:
        mac = getMac()
        userid = sys.argv[2]
        id = sys.argv[3]
        str_ = {"id": id, "userid": userid,"operator_type": "start", "status": status, "mac": mac, "time": time.time(),"program":program,"operate_name":"start"}
        json_info = json.dumps(str_)
        print(json_info)
    except Exception as e:
        print(e)

if __name__ == '__main__':
    if len(sys.argv)<4:
        print("please input the params name")
    else:
        main()