import psutil
from loguru import logger


def check_port(port: int, protocol: str = 'tcp') -> tuple:
    """
    检查指定端口和协议是否被占用
    :param port: 要检查的端口号
    :param protocol: 协议类型(tcp/udp)
    :return: (是否被占用, 占用进程信息)
    """
    try:
        logger.debug(f'正在检查{port}/{protocol}端口')
        connections = psutil.net_connections(kind=protocol)
        for conn in connections:
            if conn.status == 'LISTEN' and conn.laddr.port == port:
                process = psutil.Process(conn.pid) if conn.pid else None
                process_name = process.name() if process else '未知进程'
                # 如果是27017端口被mongod.exe占用，则认为是正常情况，不视为占用
                if port == 27017 and process_name == 'mongod.exe':
                    logger.debug(f'端口{port}被mongod.exe占用，视为正常情况。')
                    return (False, {})

                process_path = process.exe() if process and hasattr(process, 'exe') else '未知路径'
                info = {
                    'pid': conn.pid,
                    'process_name': process_name,
                    'exe_path': process_path
                }
                logger.warning(f'端口{port}被进程{info["process_name"]}占用 PID:{info["pid"]}')
                return (True, info)
        return False, {}
    except Exception as e:
        logger.error(f'端口{port}检查异常: {e}')
        return False, {}


def check_ports(ports: list) -> list:
    """
    批量检查多个端口的占用情况
    :param ports: 端口配置列表，格式示例:
        [
            (27017, 'tcp'),
            (443, 'tcp'),
            (22102, 'udp')
        ]
    :return: 检查结果列表，每个元素格式:(端口号, 协议, 是否被占用, 占用信息)
    """
    results = []
    occupied_count = 0
    logger.info(f'开始批量检查{len(ports)}个端口')
    for port_config in ports:
        port, protocol = port_config
        occupied, info = check_port(port, protocol)
        if occupied:
            occupied_count += 1
        results.append((port, protocol, occupied, info))
    logger.success(f'端口检查完成 被占用:{occupied_count} 可用:{len(ports)-occupied_count}')
    return results