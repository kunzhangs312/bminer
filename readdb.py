import pika
import json
import uuid
import time
import os
import sys
import subprocess

from queue import Queue
from threading import Thread, Lock
from datetime import datetime
from peewee import Model, SqliteDatabase, CharField, IntegerField, \
    DateTimeField, AutoField, TextField, BooleanField

# 建立Sqlite数据库连接
SQDB = SqliteDatabase('operation.db')


class Operation(Model):
    id = AutoField()

    # 下发任务详情
    taskid = CharField(verbose_name='任务ID', unique=True)
    userid = IntegerField(verbose_name='用户ID')
    action = CharField(verbose_name='操作名称')
    parameter = TextField(verbose_name='操作参数')
    maclist = TextField(verbose_name='需要执行命令的主机MAC')

    # 任务的执行状态及结果
    accept = BooleanField(verbose_name='是否接收该任务')
    status = CharField(verbose_name='操作状态', choices=(("running", "running"),
                                                     ("finished", "finished"),
                                                     ("reboot", "reboot")), null=True)
    result = TextField(verbose_name='任务执行结果', null=True)

    # 时间相关
    issued_time = DateTimeField(verbose_name='接收任务的时间')
    finish_time = DateTimeField(verbose_name='完成任务的时间', null=True)
    create_time = DateTimeField(verbose_name='记录创建时间', default=datetime.now)

    class Meta:
        verbose_name = "矿机操作日志"
        database = SQDB
        db_table = 'mine_operation'


class MineInfo(Model):
    id = AutoField()

    # 挖矿参数相关
    coin_name = CharField(verbose_name='当前正在挖的币种', null=True)
    overclock = BooleanField(verbose_name='是否超频', null=True)
    program = CharField(verbose_name='挖矿程序', null=True)
    algorithm = CharField(verbose_name='挖矿算法', null=True)
    wallet_address = CharField(verbose_name='钱包地址', null=True)      # 多个钱包地址|分割，这针对双挖
    pool_address = CharField(verbose_name='矿池地址', null=True)        # 多个矿池地址,|分割，,分割同一矿池，|分割不同矿池
    miner_prefix = CharField(verbose_name='矿工前缀', null=True)
    miner_postfix = CharField(verbose_name='矿工后缀', null=True)

    # 挖矿状态: mining-正在挖矿，unmining-没有挖矿
    mine_status = CharField(verbose_name='当前的挖矿状态', null=True)

    # 时间相关
    update_time = DateTimeField(verbose_name='记录更新时间')
    create_time = DateTimeField(verbose_name='记录创建时间', default=datetime.now)

    class Meta:
        verbose_name = "正在挖矿信息"
        database = SQDB
        db_table = 'mine_info'


def read_db(table=None, lines=10):
    if table is None:
        print("*"*50 + "Operation Table" + "*"*50)
        tasks = Operation.select().order_by(Operation.finish_time.desc()).limit(lines)
        print("id, taskid, userid, action, parameter, maclist, accept, status, "
              "result, issued_time, finish_time, create_time")
        for task in tasks:
            print(task.id, task.taskid, task.userid, task.action, task.parameter, task.maclist,
                  task.accept, task.status, task.result, task.issued_time, task.finish_time, task.create_time)

        print("*" * 50 + "Mine Info Table" + "*" * 50)
        infos = MineInfo.select().order_by(MineInfo.create_time.desc()).limit(lines)
        print('id, coin_name, overclock, program, algorithm, wallet_address, pool_address, miner_prefix, '
              'miner_postfix, mine_status, update_time, create_time')
        for info in infos:
            print(info.id, info.coin_name, info.overclock, info.program, info.algorithm, info.wallet_address,
                  info.pool_address, info.miner_prefix, info.miner_postfix, info.mine_status, info.update_time,
                  info.create_time)


if __name__ == '__main__':
    if len(sys.argv) == 2 and sys.argv[1] == '-h':
        print('readdb [tablename, operate or info] [lines]')
        sys.exit(1)

    table = None if len(sys.argv) == 1 else sys.argv[1]
    read_db(table)

