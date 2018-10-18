# -*- coding:utf-8 -*-
import json
import os
import subprocess
import time
import sys

MINE_CONF_NAME = 'mine.conf'


def main(conf_path):
    # params_str = """{"id":24774,"service_type":"Zcash","status":0,"on":true,
    # "config":{"Version":3,"Overclock":1,"Program":"xmrig-amd","Algorithm":"ethash",
    # "Extra":"","IsManualPool":0,"Primary":{"CoinName":"eth",
    # "WalletAddress":"48LHRj3T9Jfeq87sikft1ijRzuGjo5w21ALP5gnvPeTkdqGgh2qQo7LXwKpuFDnoEUWhyHZrWs
    # iuxVqHkAikyAuo1t9y5zE","PoolAddress":"xmr.f2pool.com:13531","PoolName":"uupool.cn",
    # "Algorithm":"","IsUserAddr":false,"CurrentPoolAddr":"","CurrentPoolPort":0,"Status":0},
    # "Secondary":{"CoinName":"","WalletAddress":"","PoolAddresses":null,"PoolName":"",
    # "Algorithm":"","IsUserAddr":false,"CurrentPoolAddr":"","CurrentPoolPort":0,"Status":0},
    # "MinerPrefix":"92","MinerPostfix":"92","App":{"Name":"","Version":""}},"overclock_info":
    # {"cpu":{"frequency":2800000,"frequencey":0},"gpu":[{"Id":0,"BusID":"","Level":3,
    # "PowerLimit":117,"GPUGraphicsClockOffset":0,"GPUMemoryTransferRateOffset":1000,
    # "GPUTargetFanSpeed":0}],"fan":[{"Id":0,"BusID":"0000:01:00.0","GPUTargetFanSpeed":90}]}}"""
    mine_conf_path = conf_path + '/' + MINE_CONF_NAME
    try:
        with open(mine_conf_path, 'r', encoding='utf-8') as fr:
            parameter = fr.read()

        parameter = json.loads(parameter)
        params_str = json.dumps(parameter['params'])
        # 1.解析参数
        params = json.loads(params_str)
        program = params["config"]["Program"]
        shell_name = program + ".sh"

        # 2.写入shell脚本
        file = os.path.isfile("./" + shell_name)
        if not file:
            os.mknod(shell_name)
            os.chmod(shell_name, 755)
        else:
            fp = open(shell_name, "w")
            fp.truncate()
        with open(shell_name, "r+") as f:
            f.write("# !/bin/sh \n")
            f.write("python3 /opt/miner/iMiner/miner-script/" + program + "/" + program + ".py " + params_str + " \n")

        # 3.吊起shell脚本执行
        subprocess.Popen("sh ./" + shell_name, shell=True, stdout=subprocess.PIPE)

        # 4.检查执行是否起来
        time.sleep(3)
        lines = os.popen('ps -ef|grep ' + program)
        lines = lines.readlines()
        if len(lines) > 2:
            result = {"finish_status": "success", "failed_reason": ""}
            print(json.dumps(result))
        else:
            result = {"finish_status": "failed", "failed_reason": "can't start mine program"}
            print(json.dumps(result))
    except Exception as err:
        result = {"finish_status": "failed", "failed_reason": "can't read config from file"}
        print(json.dumps(result))


if __name__ == '__main__':
    """
    根据配置参数启动挖矿，并返回启动结果，返回格式如下：{"finish_status": "success", "failed_reason": ""}
    调用该脚本是需要传入挖矿配置的文件目录路径
    """
    if len(sys.argv) != 2:
        result = {"finish_status": "failed", "failed_reason": "the number of start script parameters is not equal to 2"}
        print(json.dumps(result))
    else:
        conf_path = sys.argv[1]
        main(conf_path)
