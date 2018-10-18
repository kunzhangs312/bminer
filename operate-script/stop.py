# -*- coding:utf-8 -*-
import json
import os
import sys
import time
import uuid
import logging
import logging.handlers

MINE_SCRIPT_PATH = '../miner-script'


def create_logger(file_name='stop.log', file_handler_level=logging.DEBUG, stream_handler_level=logging.INFO):
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


log = create_logger(file_name='mine_stop.log')


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
            if len(lines) <= 3:
                continue

            for line in lines:
                if "python3 stop.py" not in line:
                    if line.find("grep " + program) != -1:
                        continue
                    vars = line.split()
                    pid = vars[1]           # get pid
                    log.info("program: {program}, pid: {pid} will be killed".format(program=program, pid=pid))
                    os.system('kill ' + pid)
    except Exception as err:
        log.error(err)

    log.info("=" * 128)


if __name__ == '__main__':
    if len(sys.argv) == 2:      # 通过taskmanager.py脚本调用，则必须传递operate-script目录的路径
        MINE_SCRIPT_PATH = sys.argv[1]
    
    stop_mineprogram()
