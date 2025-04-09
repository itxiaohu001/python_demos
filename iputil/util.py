import os
import platform
import socket
import subprocess
import ipaddress
import threading
import time
import logging
from datetime import datetime
from queue import Queue

# 配置日志记录器
log_file = 'network_scan.log'
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# 全局变量
ACTIVE_DEVICES = []
PRINT_LOCK = threading.Lock()

def get_local_ip():
    """获取本机局域网IP地址"""
    try:
        # 创建一个UDP套接字（不会真正发送数据）
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))  # 连接到Google DNS
            local_ip = s.getsockname()[0]
        logger.info(f"获取到本机IP地址: {local_ip}")
        return local_ip
    except Exception as e:
        logger.error(f"获取本机IP地址失败: {str(e)}")
        return "127.0.0.1"

def get_network_range():
    """根据本机IP计算局域网IP范围（如 192.168.1.0/24）"""
    local_ip = get_local_ip()
    network = ipaddress.ip_network(f"{local_ip}/24", strict=False)
    return network.hosts()

def ping_ip(ip):
    """通过Ping检测IP是否在线（跨平台支持）"""
    param = "-n 1" if platform.system().lower() == "windows" else "-c 1"
    command = ["ping", param, "-w", "1", str(ip)]
    return subprocess.call(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL) == 0

def get_hostname(ip):
    """尝试解析IP的主机名"""
    try:
        hostname = socket.gethostbyaddr(str(ip))[0]
        logger.debug(f"成功解析主机名 {ip} -> {hostname}")
        return hostname
    except (socket.herror, socket.gaierror) as e:
        logger.debug(f"无法解析主机名 {ip}: {str(e)}")
        return "N/A"

def scan_port(ip, ports=[445], timeout=1, retries=2):
    """检测设备是否开放指定端口（支持多端口扫描）
    Args:
        ip: 目标IP地址
        ports: 要扫描的端口列表
        timeout: 连接超时时间
        retries: 重试次数
    Returns:
        dict: 端口扫描结果字典 {port: is_open}
    """
    results = {}
    for port in ports:
        for attempt in range(retries + 1):
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.settimeout(timeout)
                    result = s.connect_ex((str(ip), port)) == 0
                    if result or attempt == retries:
                        results[port] = result
                        logger.debug(f"端口扫描 {ip}:{port} - {'开放' if result else '关闭'}")
                        break
            except Exception as e:
                if attempt == retries:
                    logger.debug(f"端口扫描异常 {ip}:{port} - {str(e)}")
                    results[port] = False
    return results

def worker_ip_scan(queue, total_ips, ports=[445]):
    """多线程任务：Ping IP并记录活跃设备"""
    while not queue.empty():
        ip = queue.get()
        if ping_ip(ip):
            hostname = get_hostname(ip)
            port_results = scan_port(ip, ports=ports)
            with PRINT_LOCK:
                ACTIVE_DEVICES.append({
                    "IP": str(ip),
                    "Hostname": hostname,
                    "Ports": port_results
                })
                logger.info(f"发现活跃设备: IP={ip}, 主机名={hostname}, 端口状态={port_results}")
                # 显示扫描进度
                completed = total_ips - queue.qsize()
                progress = (completed / total_ips) * 100
                print(f"\r扫描进度: {progress:.1f}% ({completed}/{total_ips})", end="")
        queue.task_done()

def scan_network(threads=50, ports=[445, 80, 22, 3389]):
    """主扫描函数
    Args:
        threads: 扫描线程数
        ports: 要扫描的端口列表，默认包含常用服务端口
    """
    logger.info(f"开始扫描本地网络 (线程数: {threads}, 目标端口: {ports})")
    ip_queue = Queue()
    network_range = list(get_network_range())
    total_ips = len(network_range)

    # 填充IP队列
    logger.info("正在准备IP地址队列...")
    for ip in network_range:
        ip_queue.put(ip)

    # 启动多线程扫描
    logger.info(f"正在启动{threads}个扫描线程...")
    for _ in range(threads):
        threading.Thread(target=worker_ip_scan, args=(ip_queue, total_ips, ports), daemon=True).start()

    # 等待所有任务完成
    ip_queue.join()
    logger.info("网络扫描完成")

    # 打印结果
    active_count = len(ACTIVE_DEVICES)
    logger.info(f"发现{active_count}个活跃设备")
    print("-" * 60)
    print(f"\n{'IP':<15} | {'Hostname':<25} | 端口状态")
    print("-" * 60)
    for device in sorted(ACTIVE_DEVICES, key=lambda x: ipaddress.ip_address(x["IP"])):
        port_status = ", ".join([f"Port {port}: {'开放' if status else '关闭'}" 
                                for port, status in device['Ports'].items()])
        print(f"{device['IP']:<15} | {device['Hostname']:<25} | {port_status}")

    # 自动保存扫描结果
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    csv_file = f"network_scan_{timestamp}.csv"
    try:
        with open(csv_file, "w", encoding='utf-8') as f:
            # 写入CSV头部
            ports_header = ",".join([f"Port_{port}" for port in ports])
            f.write(f"IP,Hostname,{ports_header}\n")
            # 写入设备数据
            for device in ACTIVE_DEVICES:
                port_values = ",".join([str(device['Ports'].get(port, False)) for port in ports])
                f.write(f"{device['IP']},{device['Hostname']},{port_values}\n")
        logger.info(f"扫描结果已保存到文件: {csv_file}")
    except Exception as e:
        logger.error(f"保存CSV文件失败: {str(e)}")


if __name__ == "__main__":
    scan_network()