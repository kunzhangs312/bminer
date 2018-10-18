# -*- coding:utf-8 -*-
import json
import os
import subprocess
import time
import sys
import logging
import logging.handlers

MINE_CONF_NAME = 'mine.conf'
MINE_CONF_PATH = '../' + MINE_CONF_NAME


def create_logger(file_name='start.log', file_handler_level=logging.DEBUG, stream_handler_level=logging.INFO):
    """
    创建一个logging对象，并将日志按照特定Log等级输出到特定日志文件和控制台。
    :param file_name: 日志文件的名称，默认为log.txt
    :param file_handler_level: 将特定等级的日志写入到文件中
    :param stream_handler_level: 将特定等级的日志输出到控制台
    :return: logging对象
    """
    logger = logging.getLogger(file_name)
    # 这里进行判断，如果logger.handlers列表为空，则添加，否则，直接去写日志
    # 这样做可以避免不同文件中都调用该函数时都添加addHandler，造成重复输出的问题。
    if not logger.handlers:
        logger.setLevel(logging.INFO)       # Log等级总开关
        # 定义handle的输出格式
        formatter = logging.Formatter("%(asctime)s [%(filename)s-%(lineno)d: %(funcName)s]"
                                      " %(levelname)s: %(message)s")
        fh = logging.handlers.TimedRotatingFileHandler(file_name, 'D', 1, 10, 'UTF-8')

        fh.setLevel(file_handler_level)   # 设置输出到日志文件的Log等级

        # 创建一个handler，用于输出到控制台
        # ch = logging.StreamHandler()
        # ch.setLevel(streamHandlerLevel)

        # 定义handler的输出格式
        fh.setFormatter(formatter)
        # ch.setFormatter(formatter)

        # 将logger添加到handler中
        logger.addHandler(fh)
        # logger.addHandler(ch)

    return logger


log = create_logger(file_name='mine_start.log')


def start_mine():
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
    log.info("=" * 60 + "New Start" + "=" * 60)
    log.info("start mine program ...")
    try:
        with open(MINE_CONF_PATH, 'r', encoding='utf-8') as fr:
            parameter = fr.read()

        log.info(parameter)

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
        log.error(err)

    log.info("=" * 129)


if __name__ == '__main__':
    """
    根据配置参数启动挖矿，并返回启动结果，返回格式如下：{"finish_status": "success", "failed_reason": ""}
    通过startmanger.py调用该脚本是需要传入挖矿配置的文件目录路径
    """
    if len(sys.argv) == 2:  # 通过taskmanager.py脚本调用，则必须传递operate-script目录的路径
        MINE_CONF_PATH = sys.argv[1] + '/' + MINE_CONF_NAME

    start_mine()
