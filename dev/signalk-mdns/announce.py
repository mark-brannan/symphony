"""Announce this dev box's Signal K on the LAN so SensESP devices (HALMET) find it.

Signal K runs in a Docker bridge here, so its own mDNS never leaves the bridge
and would carry a bridge address. This runs host-network and announces the LAN
address instead, re-read every 30 s so a DHCP change follows without a restart.
"""
import socket
import time

from zeroconf import ServiceInfo, Zeroconf

PORT = 3000
HOST = socket.gethostname()


def lan_ip():
    # The source address the kernel would use to leave the box: nothing is sent.
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("192.0.2.1", 9))  # TEST-NET-1, never routed
        return s.getsockname()[0]
    finally:
        s.close()


def services(ip):
    addr = [socket.inet_aton(ip)]
    # SensESP asks for _signalk-wss._tcp then _signalk-ws._tcp; clients also browse _signalk-http._tcp.
    return [
        ServiceInfo(f"_signalk-{kind}._tcp.local.", f"signalk-dev-{HOST}._signalk-{kind}._tcp.local.",
                    addresses=addr, port=PORT, server=f"{HOST}.local.",
                    properties={"txtvers": "1", "roles": "master,main"})
        for kind in ("ws", "http")
    ]


zc = Zeroconf()
current, infos = None, []
try:
    while True:
        ip = lan_ip()
        if ip != current:
            for i in infos:
                zc.unregister_service(i)
            infos = services(ip)
            for i in infos:
                zc.register_service(i)
            current = ip
            print(f"announcing _signalk-ws/_http on {ip}:{PORT}", flush=True)
        time.sleep(30)
finally:
    zc.close()
