"""Gọi tool Konnect qua stdio JSON-RPC (cùng binary với MCP server) để chạy tuần tự nhiều lệnh."""
import json, subprocess, sys

EXE = r"C:\Users\USER\Documents\KiCad\10.0\3rdparty\plugins\com_github_mixelpixx_konnect\bin\konnect.exe"


class Konnect:
    def __init__(self):
        self.p = subprocess.Popen([EXE], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                  stderr=subprocess.DEVNULL, text=True, encoding="utf-8")
        self.i = 0
        self.rpc("initialize", {"protocolVersion": "2024-11-05", "capabilities": {},
                                "clientInfo": {"name": "kcall", "version": "1"}})
        self._send({"jsonrpc": "2.0", "method": "notifications/initialized"})

    def _send(self, m):
        self.p.stdin.write(json.dumps(m) + "\n")
        self.p.stdin.flush()

    def rpc(self, method, params):
        self.i += 1
        self._send({"jsonrpc": "2.0", "id": self.i, "method": method, "params": params})
        while True:
            m = json.loads(self.p.stdout.readline())
            if m.get("id") == self.i:
                if "error" in m:
                    raise RuntimeError(m["error"])
                return m["result"]

    def call(self, tool, args):
        r = self.rpc("tools/call", {"name": tool, "arguments": args})
        text = "".join(c.get("text", "") for c in r.get("content", []))
        if r.get("isError"):
            raise RuntimeError(f"{tool}: {text[:800]}")
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return text


if __name__ == "__main__":
    k = Konnect()
    k.call("load_toolset", {"name": ["sch_wiring", "sch_components", "sch_analysis", "sch_batch", "sch_export"]})
    sch = sys.argv[1]
    nets = json.load(open(sys.argv[2], encoding="utf-8"))
    for net, pins in nets.items():
        ps = [{"reference": p.rsplit(".", 1)[0], "pin_number": p.rsplit(".", 1)[1]} for p in pins]
        r = k.call("batch_connect_to_net", {"schematic": sch, "net_name": net, "pins": ps, "stub_length": 2.54})
        bad = {kk: v for kk, v in r.items() if kk in ("errors", "failures", "skipped") and v}
        print(net, len(pins), "OK" if not bad else bad)
