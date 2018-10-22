# -*- coding:utf-8 -*-
import json
import os
import sys

from threading import Thread, Timer

MINE_BIN_PATH = "/opt/miner/bin"
MINE_SCRIPT_PATH = '../miner-script'
MINE_BIN2_PATH = "/opt/miner/iMiner/miner-script"


LOGGER_PATH = "/opt/miner/iMiner"
if LOGGER_PATH not in sys.path:
    sys.path.insert(0, LOGGER_PATH)

import logger

log = logger.create_logger(file_name='mine_stop.log', enable_stream=False)


def get_mineprogram():
    """
    获取系统中所有的挖矿程序名称的列表
    """
    try:
        for root, dirs, files in os.walk(MINE_SCRIPT_PATH):
            return dirs
    except Exception:
        raise


def output_exit(result):
    """
    输出result的值并结束程序
    :param result:
    :return:
    """
    print(json.dumps(result))
    sys.stdout.flush()  # 十分重要：os._exit()退出时不会清空stdout，导致调用该脚本的进程无法获取返回值
    os._exit(0)


def stop_miner():
    """
    关闭所有的挖矿程序
    """
    try:
        mine_program = get_mineprogram()
        if not mine_program:
            log.warning("No mine program in {0}".format(MINE_SCRIPT_PATH))
            result = {"finish_status": "success", "failed_reason": ""}
            output_exit(result)

        for program in mine_program:
            lines = os.popen('ps -ef | grep ' + program)
            lines = lines.readlines()

            for line in lines:
                find_str = MINE_BIN_PATH + '/' + program + '/' + program
                if line.find(find_str) != -1:
                    pid = line.split()[1]
                    log.warning("program: {program}, pid: {pid} will be killed".format(program=program, pid=pid))
                    os.system('kill ' + pid)

                find2_str = MINE_BIN2_PATH + '/' + program + '/' + program + '.py'
                if line.find(find2_str) != -1:
                    pid = line.split()[1]
                    log.warning("program: {program}, pid: {pid} will be killed".format(program=program, pid=pid))
                    os.system('kill ' + pid)

        result = {"finish_status": "success", "failed_reason": ""}
        output_exit(result)

    except Exception as err:
        log.exception(err)
        result = {"finish_status": "failed", "failed_reason": str(err)}
        output_exit(result)


def shutdown():
    """
    强制退出程序
    :return:
    """
    log.warning("timeout")
    result = {"finish_status": "failed", "failed_reason": "stop miner timeout"}
    output_exit(result)


if __name__ == '__main__':
    if len(sys.argv) == 2:      # 通过taskmanager.py脚本调用，则必须传递operate-script目录的路径
        MINE_SCRIPT_PATH = sys.argv[1]

    t = Thread(name='Thread-stopminer', target=stop_miner)
    t.start()

    tm = Timer(10, shutdown)
    tm.start()

    tm.join()
