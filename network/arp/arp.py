from scapy.all import *

gateway = ""

# 发送ARP请求包
ans, unans = srp(Ether(dst="ff:ff:ff:ff:ff:ff")/ARP(pdst=gateway), timeout=2)

# 打印响应结果
for snd, rcv in ans:
    print(rcv.sprintf("%Ether.src% - %ARP.psrc%"))