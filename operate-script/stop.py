# -*- coding:utf-8 -*-
import json
import os
import sys
import time
import uuid
import logging
import logging.handlers

MINE_BIN_PATH = "/opt/miner/bin"
MINE_SCRIPT_PATH = '../miner-script'
MINE_BIN2_PATH = "/opt/miner/iMiner/miner-script"


LOGGER_PATH = "/opt/miner/iMiner"
if LOGGER_PATH not in sys.path:
    sys.path.insert(0, LOGGER_PATH)

import logger

log = logger.create_logger(file_name='mine_stop.log')


def get_mineprogram():
    """
    获取系统中所有的挖矿程序名称的列表
    """
    try:
        for root, dirs, files in os.walk(MINE_SCRIPT_PATH):
            return dirs
    except Exception:
        raise


def stop_mineprogram():
    """
    关闭所有的挖矿程序
    """
    log.info("=" * 60 + "New Stop" + "="*60)
    log.info("stop all mine program ...")
    try:
        mine_program = get_mineprogram()
        if not mine_program:
            log.error("No mine program in {0}".format(MINE_SCRIPT_PATH))
            return

        for program in mine_program:
            lines = os.popen('ps -ef|grep ' + program)
            lines = lines.readlines()

            for line in lines:
                find_str = MINE_BIN_PATH + '/' + program + '/' + program
                if line.find(find_str) != -1:
                    pid = line.split()[1]
                    log.info("program: {program}, pid: {pid} will be killed".format(program=program, pid=pid))
                    os.system('kill ' + pid)

                find2_str = MINE_BIN2_PATH + '/' + program + '/' + program + '.py'
                if line.find(find2_str) != -1:
                    pid = line.split()[1]
                    log.info("program: {program}, pid: {pid} will be killed".format(program=program, pid=pid))
                    os.system('kill ' + pid)

    except Exception as err:
        log.error(err)

    log.info("=" * 128)


if __name__ == '__main__':
    if len(sys.argv) == 2:      # 通过taskmanager.py脚本调用，则必须传递operate-script目录的路径
        MINE_SCRIPT_PATH = sys.argv[1]
    
    stop_mineprogram()
