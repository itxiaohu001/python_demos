from scapy.all import *

# 半开放扫描（SYN扫描）
ans, unans = sr(IP(dst="127.0.0.1")/TCP(dport=(1,1024), flags="S"), timeout=2)

# 分析开放端口
for snd, rcv in ans:
    if rcv[TCP].flags == "SA":  # SYN-ACK响应
        print(f"Port {snd[TCP].dport} is open")