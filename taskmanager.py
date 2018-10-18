import pika
import pika.exceptions
import json
# import demjson
import uuid
import time
import os
import subprocess
import logging
import logging.handlers

from queue import Queue
from threading import Thread, Lock
from datetime import datetime
from peewee import Model, SqliteDatabase, CharField, IntegerField, \
    DateTimeField, AutoField, TextField, BooleanField


CONFIG = {
    'RABBITMQ': {
        'ACCOUNT': 'machine',
        'PASSWORD': '161e85c737a844cd',
        'URL': '192.168.0.64',
        'PORT': 5672
    },
    'READ_SWITCH': 'BrokerSendSwitch',
    'WRITE_QUEUE': 'BrokerReadQueue',

    'CONFIG_NAME': 'mine.conf',
    'TRACE_ENABLE': True,
    'DEV_ENV': False,
}

MAC = 'e0d55e69c514' if CONFIG['DEV_ENV'] else uuid.UUID(int=uuid.getnode()).hex[-12:]
OPERATE_STATUS = None
OPERATE_STATUS_LOCK = Lock()
PWD = os.getcwd()
MINE_SCRIPT_DIRNAME = 'miner-script'
MINE_SCRIPT_PWD = PWD + '/' + MINE_SCRIPT_DIRNAME


def create_logger(file_name='taskmanager.log', file_handler_level=logging.WARNING, stream_handler_level=logging.DEBUG):
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
        ch = logging.StreamHandler()
        ch.setLevel(stream_handler_level)

        # 定义handler的输出格式
        fh.setFormatter(formatter)
        ch.setFormatter(formatter)

        # 将logger添加到handler中
        logger.addHandler(fh)
        logger.addHandler(ch)

    return logger


# 建立Sqlite数据库连接
SQDB = SqliteDatabase('operation.db')

log = create_logger()


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


class RabbitMQServer(object):
    def __init__(self):
        self.connection = None
        self.channel = None

    def connect(self):
        log.info("Initalizing network connection")
        credentials = pika.PlainCredentials(CONFIG['RABBITMQ']['ACCOUNT'], CONFIG['RABBITMQ']['PASSWORD'])
        parameters = pika.ConnectionParameters(CONFIG['RABBITMQ']['URL'], CONFIG['RABBITMQ']['PORT'], '/', credentials)

        connected = False
        while not connected:  # retry if establishing a connection fails
            try:
                log.info("Trying to establish a connection to the manager")
                self.connection = pika.BlockingConnection(parameters=parameters)
                self.channel = self.connection.channel()
                connected = True
                log.info("Connection to manager established")
            except pika.exceptions.AMQPConnectionError as pe:  # if connection can't be established
                log.error("Wasn't able to open a connection to the manager: %s" % pe)
                time.sleep(30)

    def connection_cleanup(self):
        self.channel.close()
        self.connection.close()


class TaskReceiver(Thread, RabbitMQServer):
    def __init__(self, queue):
        self.queue = queue

        Thread.__init__(self)
        RabbitMQServer.__init__(self)

    def handler(self, ch, method, properties, body):
        """
        接收到来自服务器的任务数据格式（JSON字符串）为：
        {"taskid": "fa23dad", "maclist": [], "user_id": 1, "parameter": {}, "action": ""}
        """
        global OPERATE_STATUS
        try:
            task_data = json.loads(body.decode('utf-8'))
            log.info("[x] Received %r" % (task_data,))

            if MAC not in task_data['maclist']:
                log.info('the task does not belong to me')
                return

            taskid = task_data['taskid']
            maclist = task_data['maclist']
            userid = task_data['user_id']
            parameter = task_data['parameter']
            action = task_data['action']

            OPERATE_STATUS_LOCK.acquire()
            if OPERATE_STATUS is not None:
                log.warning('the machine is busy')
                Operation.create(taskid=taskid, userid=userid, action=action,
                                 parameter=json.dumps(parameter),
                                 maclist='|'.join(maclist),
                                 accept=False,
                                 issued_time=datetime.now())
                OPERATE_STATUS_LOCK.release()
                return

            OPERATE_STATUS_LOCK.release()

            # 将任务添加到数据库中
            log.info('insert task into database')
            operation = Operation(taskid=taskid, userid=userid, action=action,
                                  parameter=json.dumps(parameter), maclist='|'.join(maclist))
            operation.accept = True
            operation.status = 'running'
            operation.issued_time = datetime.now()
            operation.save()

            # 通知TaskHandler线程完成任务
            self.queue.put(json.dumps(task_data))

        except Exception as err:
            log.error(err)

    def run(self):
        log.info('TaskReceiver running ...')

        # 生成队列，并绑定到交换机上
        read_queue = 'MechineReadQueue' + MAC.upper()

        self.connect()      # 连接RabbitMQ，并返回connection和channel
        self.channel.exchange_declare(exchange=CONFIG['READ_SWITCH'], exchange_type='fanout')
        self.channel.queue_declare(queue=read_queue)
        self.channel.queue_bind(exchange=CONFIG['READ_SWITCH'], queue=read_queue)
        self.channel.basic_consume(self.handler, queue=read_queue, no_ack=True)

        while True:
            try:
                self.channel.start_consuming()  # blocking call
            except pika.exceptions.ConnectionClosed:    # when connection is lost, e.g. rabbitmq not running
                log.warning("Lost connection to rabbitmq service on manager")
                # time.sleep(10)      # reconnect timer
                logging.info("Trying to reconnect...")
                self.connect()
                self.channel.exchange_declare(exchange=CONFIG['READ_SWITCH'], exchange_type='fanout')
                self.channel.queue_declare(queue=read_queue)
                self.channel.queue_bind(exchange=CONFIG['READ_SWITCH'], queue=read_queue)
                self.channel.basic_consume(self.handler, queue=read_queue, no_ack=True)


def create_or_update_mine_info(parameter, mine_status):
    """
    创建或者更新当前的挖矿信息，当mine_status不为None时，仅仅更新挖矿状态，parameter必须为字典类型
    :return:
    """
    log.info("create or update mine info table")

    if parameter is not None:
        secondary_coin_name = parameter.get('params', None).get('config', None) \
            .get('Secondary', None).get('CoinName', None)

        if secondary_coin_name is not None:
            coin_name = parameter['params']['config']['Primary']['CoinName'] + '|' + secondary_coin_name
        else:
            coin_name = parameter['params']['config']['Primary']['CoinName']

        overclock = parameter.get('params', None).get('config', None).get('Overclock', None)
        program = parameter.get('params', None).get('config', None).get('Program', None)
        algorithm = parameter.get('params', None).get('config', None).get('Algorithm', None)

        secondary_wallet_address = parameter.get('params', None).get('config', None) \
            .get('Secondary', None).get('WalletAddress', None)

        if secondary_coin_name:
            wallet_address = parameter.get('params', None).get('config', None) \
                                 .get('Primary', None).get('WalletAddress',
                                                           None) + "|" + secondary_wallet_address
        else:
            wallet_address = parameter.get('params', None).get('config', None) \
                .get('Primary', None).get('WalletAddress', None)

        secondary_pool_address = parameter.get('params', None).get('config', None) \
            .get('Secondary', None).get('PoolAddresses', None)
        if secondary_pool_address:
            pool_address = parameter.get('params', None).get('config', None) \
                               .get('Primary', None).get('PoolAddresses', None) + "|" + secondary_pool_address
        else:
            pool_address = parameter.get('params', None).get('config', None) \
                .get('Primary', None).get('PoolAddresses', None)

        miner_prefix = parameter.get('params', None).get('config', None) \
            .get('MinerPrefix', None)
        miner_postfix = parameter.get('params', None).get('config', None) \
            .get('MinerPostfix', None)

    mine_info = MineInfo.select().order_by(MineInfo.create_time.desc()).limit(1)
    try:
        mine_info = MineInfo.get_or_none(id=mine_info[0])
        if parameter is not None:
            mine_info.coin_name = coin_name
            mine_info.overclock = overclock
            mine_info.program = program
            mine_info.algorithm = algorithm
            mine_info.wallet_address = wallet_address
            mine_info.pool_address = pool_address
            mine_info.miner_prefix = miner_prefix
            mine_info.miner_postfix = miner_postfix

        mine_info.mine_status = mine_info
        mine_info.update_time = datetime.now()
        mine_info.save()
    except Exception as err:
        log.warning(str(err) + ': ' + 'no mine info recode in table, so create it!')

        # 将执行任务的信息保存到数据库中
        if parameter is not None:
            MineInfo.create(coin_name=coin_name, overclock=overclock, program=program, algorithm=algorithm,
                            wallet_address=wallet_address, pool_address=pool_address, miner_prefix=miner_prefix,
                            miner_postfix=miner_postfix, update_time=datetime.now(), mine_status=mine_status)
        else:
            MineInfo.create(mine_status=mine_status, update_time=datetime.now())


class TaskHandler(Thread, RabbitMQServer):
    def __init__(self, queue):
        self.queue = queue

        Thread.__init__(self)
        RabbitMQServer.__init__(self)

    @staticmethod
    def filling_result(finish_status='nostatus', failed_reason='', is_random=False):
        """
        填充需要返回给服务器的执行结果值，结果值数据格式为：
        {'finish_status': success or failed, 'finish_time': int(time.time())}
        """
        if is_random:
            return {'finish_status': 'nostatus', 'failed_reason': failed_reason, 'finish_time': int(time.time())}
        else:
            return {'finish_status': finish_status, 'failed_reason': failed_reason, 'finish_time': int(time.time())}

    def update_feedback(self, taskid, userid, action, write_queue, finish_status,
                        failed_reason='', status='finished'):
        """
        任务完成后，更新本地数据库及将结果反馈给服务器
        :param taskid:
        :param userid:
        :param action:
        :param write_queue:
        :param finish_status: 任务执行的状态，success or failed
        :param failed_reason: 任务执行失败的原因
        :param status: 任务当前的执行状态：running, finished, reboot
        :return:
        """
        # 执行完成后根据执行结果更新变量及数据库
        operation = Operation.get_or_none(taskid=taskid)
        if operation is None:
            log.info('taskid is not in database')
            return False

        result = self.filling_result(finish_status)
        operation.result = json.dumps(result)
        operation.finish_time = datetime.now()
        operation.status = status
        operation.save()

        if status == 'reboot':      # 重启操作无需上报
            return

        resp_info = {'user_id': userid, 'action': action, 'taskid': taskid,
                     'maclist': [MAC], 'resp_type': 'completed',
                     'result': self.filling_result(finish_status=finish_status,
                                                   failed_reason=failed_reason)}
        log.info('completed response: ' + json.dumps(resp_info))

        if self.connection.is_open:
            try:
                self.channel.basic_publish(exchange='', routing_key=write_queue, body=json.dumps(resp_info))
            except Exception as err:
                log.error("Error while sending data to queue:\n%s" % err)
                return
        else:
            self.connect()
            self.channel.queue_declare(queue=write_queue, auto_delete=True)
            try:
                self.channel.basic_publish(exchange='', routing_key=write_queue, body=json.dumps(resp_info))
            except Exception as err:
                log.error("Error while sending data to queue:\n%s" % err)
                return

    def run(self):
        log.info('TaskHandler running ...')

        self.connect()  # 连接RabbitMQ，并返回connection和channel

        global OPERATE_STATUS
        while True:
            try:
                task_data = self.queue.get()

                # 判断RabbitMQ连接是否打开
                if not self.connection.is_open:
                    self.connect()

                feedback_stage = None

                log.info("Handle Task: " + task_data)

                OPERATE_STATUS_LOCK.acquire()
                OPERATE_STATUS = 'ACCEPT'  # 标记已经接收新的任务，不能再接收，但是可以记录接收的任务，不执行
                OPERATE_STATUS_LOCK.release()

                task_data = json.loads(task_data)

                taskid = task_data['taskid']
                maclist = task_data['maclist']
                userid = task_data['user_id']
                parameter = task_data['parameter']      # json字符串，服务器将该参数值JSON序列化后赋值给parameter字段
                action = task_data['action']

                parameter = json.loads(parameter)       # 将json字符串反序列化
                # parameter = demjson.decode(parameter)

                # 声明一个队列，用于给RabbitMQ发送接收任务的应答消息
                write_queue = CONFIG['WRITE_QUEUE'] + taskid.upper()

                if self.connection.is_open:
                    self.channel.queue_declare(queue=write_queue, auto_delete=True)
                    resp_info = {'user_id': userid, 'action': action, 'taskid': taskid,
                                 'maclist': [MAC], 'resp_type': 'confirm',
                                 'result': self.filling_result(is_random=True)}
                    log.info('confirm response: ' + json.dumps(resp_info))
                    try:
                        self.channel.basic_publish(exchange='', routing_key=write_queue, body=json.dumps(resp_info))
                        feedback_stage = 'confirm'  # 更新反馈阶段变量
                    except Exception as err:
                        log.error("Error while sending data to queue:\n%s" % err)
                        continue
                else:
                    self.connect()
                    self.channel.queue_declare(queue=write_queue, auto_delete=True)
                    resp_info = {'user_id': userid, 'action': action, 'taskid': taskid,
                                 'maclist': [MAC], 'resp_type': 'confirm',
                                 'result': self.filling_result(is_random=True)}
                    log.info('confirm response: ' + json.dumps(resp_info))
                    try:
                        self.channel.basic_publish(exchange='', routing_key=write_queue, body=json.dumps(resp_info))
                        feedback_stage = 'confirm'  # 更新反馈阶段变量
                    except Exception as err:
                        log.error("Error while sending data to queue:\n%s" % err)
                        continue

                # 执行矿机命令
                if action == 'Shutdown':            # 关机
                    log.info("execute shutdown task")

                    # 在关机之前更新数据库及上报执行结果，默认关机操作不会失败
                    self.update_feedback(taskid, userid, action, write_queue, finish_status='success',
                                         status='finished', failed_reason='')

                    feedback_stage = 'completed'    # 更新反馈阶段变量
                    os.system("shutdown -h now")
                elif action == 'Shelve':            # 下架，直接停止所有的挖矿软件
                    log.info("execute shelve task")

                    cmd = "python3 ./operate-script/remove.py"
                    p = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE)
                    # stdout, _ = p.communicate()
                    # out = stdout.decode('utf-8')
                    # 完成下架操作后更新本地数据库并上报执行结果，默认下架操作不会失败
                    self.update_feedback(taskid, userid, action, write_queue,
                                         finish_status='success', status='finished',
                                         failed_reason='')

                    feedback_stage = 'completed'    # 更新反馈阶段变量

                    # 更新本地的挖矿信息数据库
                    create_or_update_mine_info(parameter=None, mine_status="unmining")
                elif action == 'PauseMining':       # 暂停挖矿，与下架一样，直接停止所有的挖矿软件
                    log.info("execute pause mining task")

                    cmd = "python3 ./operate-script/stop.py " + MINE_SCRIPT_PWD
                    p = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE)
                    # stdout, _ = p.communicate()
                    # out = stdout.decode('utf-8')
                    # 完成暂停挖矿操作后更新本地数据库，但不会上报服务器
                    self.update_feedback(taskid, userid, action, write_queue,
                                         finish_status='success', status='finished',
                                         failed_reason='')

                    feedback_stage = 'completed'  # 更新反馈阶段变量

                    # 更新本地的挖矿信息数据库
                    create_or_update_mine_info(parameter=None, mine_status="unmining")
                elif action == 'RestartMining':     # 重启挖矿，读取配置文件，启动挖矿程序
                    log.info("execute restart mining task")

                    # 从配置文件中或者操作数据库中获取配置参数
                    try:
                        with open(CONFIG['CONFIG_NAME'], 'r', encoding='utf-8') as fr:
                            parameter = fr.read()
                    except Exception as error:
                        log.info(str(error) + ': ' + "can't read config from file")
                        # 完成下架操作后更新本地数据库并上报执行结果
                        self.update_feedback(taskid, userid, action, write_queue,
                                             finish_status='failed', status='finished',
                                             failed_reason='No config file')

                        feedback_stage = 'completed'  # 更新反馈阶段变量
                        continue

                    parameter = json.loads(parameter)

                    # 关闭所有的挖矿程序及超频，默认执行成功
                    log.info('stop all mine and overclock')
                    cmd = "python3 ./operate-script/stop.py " + MINE_SCRIPT_PWD
                    subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE)

                    # 根据配置启动挖矿程序及超频
                    log.info('start mine according to config')

                    # json_params = json.dumps(parameter['params'])
                    cmd = "python3 ./operate-script/start.py " + PWD
                    p = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE)
                    stdout, _ = p.communicate()
                    json_result = stdout.decode('utf-8')
                    result = json.loads(json_result)

                    # result格式：{"finish_status": "failed", "failed_reason": "can't start mine program"}
                    finish_status = result['finish_status']
                    failed_reason = result['failed_reason']

                    # 完成下架操作后更新本地数据库并上报执行结果
                    self.update_feedback(taskid, userid, action, write_queue,
                                         finish_status=finish_status, status='finished',
                                         failed_reason=failed_reason)

                    feedback_stage = 'completed'  # 更新反馈阶段变量

                    # 更新本地的挖矿信息数据库
                    mine_status = 'mining' if finish_status == 'success' else 'unmining'
                    create_or_update_mine_info(parameter, mine_status=mine_status)
                elif action == 'ConfigRestart':     # 配置并重启挖矿，将配置保存到本地配置文件中
                    log.info("execute config restart task")

                    # 将配置保存到文件中
                    log.info("save config into file")
                    with open(CONFIG['CONFIG_NAME'], 'w', encoding='utf-8') as fw:
                        fw.write(json.dumps(parameter))

                    # 关闭所有的挖矿程序及超频，默认执行成功
                    log.info('stop all mine and overclock')
                    cmd = "python3 ./operate-script/stop.py " + MINE_SCRIPT_PWD
                    subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE)

                    # 根据配置启动挖矿程序及超频
                    log.info('start mine according to config')

                    # json_params = json.dumps(parameter['params'])
                    cmd = "python3 ./operate-script/start.py " + PWD
                    p = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE)
                    stdout, _ = p.communicate()
                    json_result = stdout.decode('utf-8')
                    result = json.loads(json_result)

                    # result格式：{"finish_status": "failed", "failed_reason": "can't start mine program"}
                    finish_status = result['finish_status']
                    failed_reason = result['failed_reason']

                    # 完成下架操作后更新本地数据库并上报执行结果
                    self.update_feedback(taskid, userid, action, write_queue,
                                         finish_status=finish_status, status='finished',
                                         failed_reason=failed_reason)

                    feedback_stage = 'completed'  # 更新反馈阶段变量

                    # 更新本地的挖矿信息数据库
                    mine_status = 'mining' if finish_status == 'success' else 'unmining'
                    create_or_update_mine_info(parameter, mine_status=mine_status)
                elif action == 'Restart':           # 重启矿机
                    log.info("execute restart task")
                    # 在重启之前更新数据库及上报执行结果，默认关机操作不会失败
                    self.update_feedback(taskid, userid, action, write_queue, finish_status='success',
                                         status='reboot', failed_reason='')

                    feedback_stage = 'completed'    # 更新反馈阶段变量
                    os.system("reboot -h now")
                elif action == 'Overclock':         # 主机超频
                    pass
                else:
                    log.warning('Unknown operation')
            except Exception as err:
                log.error(str(err) + ": " + "task handler occur fatal error!")

                # 声明一个队列，用于给RabbitMQ发送接收任务的应答消息
                write_queue = CONFIG['WRITE_QUEUE'] + taskid.upper()

                if feedback_stage is None:
                    if self.connection.is_open:
                        self.channel.queue_declare(queue=write_queue, auto_delete=True)

                        resp_info = {'user_id': userid, 'action': action, 'taskid': taskid,
                                     'maclist': [MAC], 'resp_type': 'confirm',
                                     'result': self.filling_result(is_random=True)}
                        log.info('confirm response: ' + json.dumps(resp_info))
                        try:
                            self.channel.basic_publish(exchange='', routing_key=write_queue, body=json.dumps(resp_info))
                            self.update_feedback(taskid, userid, action, write_queue,
                                                 finish_status='failed', status='finished',
                                                 failed_reason=str(err))
                        except Exception as err:
                            log.error("Error while sending data to queue:\n%s" % err)
                            continue
                    else:
                        self.connect()
                        self.channel.queue_declare(queue=write_queue, auto_delete=True)

                        resp_info = {'user_id': userid, 'action': action, 'taskid': taskid,
                                     'maclist': [MAC], 'resp_type': 'confirm',
                                     'result': self.filling_result(is_random=True)}
                        log.info('confirm response: ' + json.dumps(resp_info))
                        try:
                            self.channel.basic_publish(exchange='', routing_key=write_queue, body=json.dumps(resp_info))
                            self.update_feedback(taskid, userid, action, write_queue,
                                                 finish_status='failed', status='finished',
                                                 failed_reason=str(err))
                        except Exception as err:
                            log.error("Error while sending data to queue:\n%s" % err)
                            continue
                elif feedback_stage == 'confirm':
                    self.update_feedback(taskid, userid, action, write_queue,
                                         finish_status='failed', status='finished',
                                         failed_reason=str(err))
                elif feedback_stage == 'completed':
                    pass
            finally:
                OPERATE_STATUS_LOCK.acquire()
                OPERATE_STATUS = None  # 标记任务已完成，可以接收新的任务
                OPERATE_STATUS_LOCK.release()


def system_boot():
    log.info('system boot check')

    # RabbitMQ连接
    credentials = pika.PlainCredentials(CONFIG['RABBITMQ']['ACCOUNT'], CONFIG['RABBITMQ']['PASSWORD'])
    connection = pika.BlockingConnection(pika.ConnectionParameters(
        CONFIG['RABBITMQ']['URL'], CONFIG['RABBITMQ']['PORT'], '/', credentials))
    channel = connection.channel()

    # 从数据库中获取最后一条接收的任务
    operation = Operation.get_or_none(accept=True, status='reboot')
    if operation is not None:
        taskid = operation.taskid
        write_queue = CONFIG['WRITE_QUEUE'] + taskid.upper()
        try:
            channel.queue_declare(queue=write_queue)
            resp_info = {'user_id': operation.userid, 'action': operation.action, 'taskid': taskid,
                         'maclist': MAC, 'resp_type': 'completed'}
            channel.basic_publish(exchange='', routing_key=write_queue, body=json.dumps(resp_info))
        except Exception as err:
            log.error("Error while sending data to queue:\n%s" % err)

        # 更新数据库记录
        result = {'isfinished': True, 'create': str(datetime.now())}
        operation.result = json.dumps(result)
        operation.finish_time = datetime.now()
        operation.status = 'finished'
        operation.save()

        connection.close()
    else:
        mine_info = MineInfo.select().order_by(MineInfo.create_time.desc()).limit(1)
        try:
            mine_info = MineInfo.get_or_none(id=mine_info[0])
            if mine_info.mine_status == 'mining':
                # 从配置文件中或者操作数据库中获取配置参数
                try:
                    with open(CONFIG['CONFIG_NAME'], 'r', encoding='utf-8') as fr:
                        parameter = fr.read()
                except Exception as error:
                    log.info(str(error) + ': ' + "can't read config from file")
                    return
                parameter = json.loads(parameter)

                # 关闭所有的挖矿程序及超频，默认执行成功
                log.info('stop all mine and overclock')
                cmd = "python3 ./operate-script/stop.py " + MINE_SCRIPT_PWD
                subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE)

                # 根据配置启动挖矿程序及超频
                log.info('start mine according to config')

                # json_params = json.dumps(parameter['params'])
                cmd = "python3 ./operate-script/start.py " + PWD
                p = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE)
                stdout, _ = p.communicate()
                json_result = stdout.decode('utf-8')
                result = json.loads(json_result)

                # result格式：{"finish_status": "failed", "failed_reason": "can't start mine program"}
                finish_status = result['finish_status']
                # failed_reason = result['failed_reason']

                # 更新本地的挖矿信息数据库
                mine_status = 'mining' if finish_status == 'success' else 'unmining'
                create_or_update_mine_info(parameter, mine_status=mine_status)
        except Exception as err:
            log.error(str(err) + ': ' + 'no mine info recode in table')


if __name__ == '__main__':
    log.info('create operation and info table if not exist')

    Operation.create_table()
    MineInfo.create_table()

    # 开机检查
    system_boot()

    # 声明进程间通信的消息队列
    queue = Queue()

    threads = [TaskReceiver(queue), TaskHandler(queue)]

    for thread in threads:
        thread.start()

    for thread in threads:
        thread.join()

    log.info('MainThread over')

