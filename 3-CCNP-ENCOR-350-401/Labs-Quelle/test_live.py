#!/usr/bin/env python3
"""Prüft den Telnet-Zugang von live_test.py gegen eine nachgebaute IOS-Konsole (kein echtes Gerät)."""
import socket, threading
import live_test


def console(conn):
    mode, buf = "R1>", b""
    conn.sendall(b"\r\n" + mode.encode())
    while True:
        data = conn.recv(1024)
        if not data:
            return
        buf += data
        while b"\r" in buf:
            line, buf = buf.split(b"\r", 1)
            cmd = line.decode().strip()
            out = ""
            if cmd == "enable":
                mode = "R1#"
            elif cmd == "configure terminal":
                mode = "R1(config)#"
            elif cmd == "end":
                mode = "R1#"
            elif cmd.startswith("bogus"):
                out = "                 ^\r\n% Invalid input detected at '^' marker.\r\n"
            elif cmd == "show clock":
                out = "*12:00:00.000 UTC Mon Jan 1 2026\r\n"
            elif cmd == "clear thing":
                conn.sendall(b"clear thing\r\nReset? [confirm]")
                conn.recv(16)
                out = "done\r\n"
                cmd = ""
            conn.sendall((cmd + "\r\n" + out + mode).encode())


def main():
    srv = socket.socket()
    srv.bind(("127.0.0.1", 0))
    srv.listen(1)
    threading.Thread(target=lambda: console(srv.accept()[0]), daemon=True).start()
    t = live_test.Telnet("127.0.0.1", {"R1": srv.getsockname()[1]}, timeout=5)
    assert "UTC" in t.run("R1", "show clock")
    out = t.config("R1", ["interface Loopback0", "bogus line"])
    assert live_test.parser_errors(out) == [("bogus line", "% Invalid input detected at '^' marker.")], live_test.parser_errors(out)
    assert not live_test.parser_errors(t.config("R1", ["interface Loopback0"]))
    assert "done" in t.run("R1", "clear thing")
    t.close()
    print("Telnet-Zugang: in Ordnung")


if __name__ == "__main__":
    main()
