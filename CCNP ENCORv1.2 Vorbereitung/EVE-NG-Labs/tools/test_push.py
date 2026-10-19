import socket, threading, tempfile, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import eve_push_configs as e
got = {}
def server(port, key, ready):
    srv = socket.socket(); srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1); srv.bind(("127.0.0.1", port)); srv.listen(1); ready.set()
    c, _ = srv.accept(); buf = b""; c.settimeout(3)
    try:
        while True:
            d = c.recv(4096)
            if not d: break
            buf += d
    except socket.timeout: pass
    got[key] = buf.decode(); c.close(); srv.close()
d = tempfile.mkdtemp(); os.makedirs(d + "/build"); os.makedirs(d + "/vpcs")
open(d + "/build/R1.cfg", "w").write("hostname R1\ninterface Gi0/0\n ip address 10.0.0.1 255.255.255.0\n no shutdown\n")
open(d + "/build/N1.cfg", "w").write("feature ospf\nrouter ospf 1\n")
open(d + "/vpcs/H1.vpc", "w").write("ip 10.0.0.2/24 10.0.0.1\nsave\n")
ths = []
for port, key in ((45011, "R1"), (45012, "N1"), (45013, "H1")):
    r = threading.Event(); t = threading.Thread(target=server, args=(port, key, r)); t.start(); r.wait(); ths.append(t)
e.main(["127.0.0.1", d, "--mode", "build", "--ports", "R1=45011", "N1=45012", "--vpcs", "H1=45013", "--delay", "0.01"])
for t in ths: t.join()
r1 = got["R1"].split("\r\n"); n1 = got["N1"].split("\r\n"); h1 = got["H1"].split("\r\n")
assert "configure terminal" in r1 and r1.index("hostname R1") > r1.index("configure terminal") and r1[-3:-1] == ["end", "write memory"], r1
assert " ip address 10.0.0.1 255.255.255.0" in r1
assert "copy running-config startup-config" in n1 and "enable" not in n1, n1
assert "ip 10.0.0.2/24 10.0.0.1" in h1 and "save" in h1
e.main(["127.0.0.1", d, "--ports", "R1=1", "--dry-run"])
print("test ok")
