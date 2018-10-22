# -*- coding:utf-8 -*-
import json
import os
import subprocess
import time
import sys

from threading import Thread, Timer

MINE_CONF_NAME = 'mine.conf'
MINE_CONF_PATH = '../' + MINE_CONF_NAME

LOGGER_PATH = "/opt/miner/iMiner"
if LOGGER_PATH not in sys.path:
    sys.path.insert(0, LOGGER_PATH)

import logger

log = logger.create_logger(file_name='mine_start.log', enable_stream=False)


def output_exit(result):
    """
    输出result的值并结束程序
    :param result:
    :return:
    """
    print(json.dumps(result))
    sys.stdout.flush()          # 十分重要：os._exit()退出时不会清空stdout，导致调用该脚本的进程无法获取返回值
    os._exit(0)


def start_miner():
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
    try:
        with open(MINE_CONF_PATH, 'r', encoding='utf-8') as fr:
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
            with open(shell_name, "w") as fp:
                fp.truncate()
        with open(shell_name, "r+") as f:
            f.write("# !/bin/sh \n")
            f.write("python3 /opt/miner/iMiner/miner-script/" + program + "/"
                    + program + ".py " + "'" + params_str + "'" + " \n")

        # 3.吊起shell脚本执行
        subprocess.Popen("sh ./" + shell_name, shell=True, stdout=open('/dev/null', 'w'), stderr=open('/dev/null', 'w'))

        # 4.检查执行是否起来
        time.sleep(3)
        lines = os.popen('ps -ef | grep ' + program)
        lines = lines.readlines()
        if len(lines) > 2:
            result = {"finish_status": "success", "failed_reason": ""}
            output_exit(result)
        else:
            result = {"finish_status": "failed", "failed_reason": "can't start mine program"}
            output_exit(result)
    except Exception as err:
        log.exception(err)
        result = {"finish_status": "failed", "failed_reason": "can't read config from file"}
        output_exit(result)


def shutdown():
    """
    强制退出程序
    :return:
    """
    log.warning("timeout")
    result = {"finish_status": "failed", "failed_reason": "start miner timeout"}
    output_exit(result)


if __name__ == '__main__':
    """
    根据配置参数启动挖矿，并返回启动结果，返回格式如下：{"finish_status": "success", "failed_reason": ""}
    通过startmanger.py调用该脚本是需要传入挖矿配置的文件目录路径
    """
    if len(sys.argv) == 2:  # 通过taskmanager.py脚本调用，则必须传递operate-script目录的路径
        MINE_CONF_PATH = sys.argv[1] + '/' + MINE_CONF_NAME

    t = Thread(name='Thread-startminer', target=start_miner)
    t.start()

    tm = Timer(60, shutdown)
    tm.start()

    tm.join()
