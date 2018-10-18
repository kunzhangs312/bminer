import logging
import logging.handlers


def create_logger(file_name='start.log', file_handler_level=logging.WARNING, stream_handler_level=logging.INFO):
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
