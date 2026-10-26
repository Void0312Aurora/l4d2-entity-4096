#!/usr/bin/env python3
"""Collect process and host-network counters for a bounded D63 load stage."""
import argparse
import json
from pathlib import Path
import time


def proc_sample(pid, interface):
    root = Path(f'/proc/{pid}')
    stat = (root/'stat').read_text().split()
    status = (root/'status').read_text()
    rss = next(int(line.split()[1]) for line in status.splitlines() if line.startswith('VmRSS:'))
    net = (Path('/proc/net/dev')).read_text()
    fields = next(line.split(':',1)[1].split() for line in net.splitlines() if line.split(':',1)[0].strip()==interface)
    udp = (Path('/proc/net/snmp')).read_text().splitlines()
    udp_values = {}
    for i, line in enumerate(udp[:-1]):
        if line.startswith('Udp:') and udp[i+1].startswith('Udp:'):
            keys, vals = line.split()[1:], udp[i+1].split()[1:]
            udp_values = dict(zip(keys, map(int, vals)))
    return dict(time=time.time(), pid=pid, cpu_user_ticks=int(stat[13]), cpu_system_ticks=int(stat[14]),
                rss_kib=rss, interface=interface,
                interface_rx_bytes=int(fields[0]), interface_rx_packets=int(fields[1]),
                interface_tx_bytes=int(fields[8]), interface_tx_packets=int(fields[9]),
                udp=udp_values)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('pid', type=int)
    ap.add_argument('--out', type=Path, required=True)
    ap.add_argument('--interface', default='lo')
    ap.add_argument('--duration', type=float, default=15)
    ap.add_argument('--interval', type=float, default=1)
    a = ap.parse_args()
    rows=[]
    end=time.monotonic()+a.duration
    while time.monotonic()<end:
        rows.append(proc_sample(a.pid,a.interface))
        time.sleep(min(a.interval,max(0,end-time.monotonic())))
    result=dict(schema='d63-process-network-series-v1', pid=a.pid, interface=a.interface,
                duration_seconds=a.duration, samples=rows)
    a.out.parent.mkdir(parents=True,exist_ok=True)
    a.out.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(pid=a.pid,samples=len(rows),first=rows[0],last=rows[-1]),indent=2))


if __name__=='__main__':
    main()
