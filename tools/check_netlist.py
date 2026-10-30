"""So netlist kicad-cli (nguồn chân lý) với bảng net thiết kế design_nets.json.

Chạy: python tools/check_netlist.py  (cần kicad-cli trong PATH mặc định của KiCad 10)
Thoát mã 1 nếu có bất kỳ chân nào lệch.
"""
import json, re, subprocess, sys, tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CLI = r"C:\Program Files\KiCad\10.0\bin\kicad-cli.exe"


def kicad_nets(sch: Path) -> dict[str, set[str]]:
    out = Path(tempfile.mkdtemp()) / "n.net"
    subprocess.run([CLI, "sch", "export", "netlist", "-o", str(out), str(sch)], check=True,
                   capture_output=True)
    txt = re.sub(r"\s+", " ", out.read_text(encoding="utf-8"))
    nets = {}
    for chunk in txt.split("(net (code ")[1:]:
        name = re.search(r'\(name "([^"]*)"\)', chunk).group(1).lstrip("/")
        nets[name] = set(f"{r}.{p}" for r, p in
                         re.findall(r'\(node \(ref "([^"]+)"\) \(pin "([^"]+)"\)', chunk))
    return nets


def compare(want: dict[str, list[str]], got: dict[str, set[str]]) -> list[str]:
    errs = []
    pin_to_net = {p: n for n, ps in got.items() for p in ps}
    for net, pins in want.items():
        for p in pins:
            if p.startswith("#"):
                continue
            if pin_to_net.get(p) != net:
                errs.append(f"{p}: muon {net}, thuc te {pin_to_net.get(p)}")
        extra = got.get(net, set()) - set(pins)
        if extra:
            errs.append(f"{net}: thua chan {sorted(extra)}")
    return errs


if __name__ == "__main__":
    want = json.loads((ROOT / "tools" / "design_nets.json").read_text(encoding="utf-8"))
    got = kicad_nets(ROOT / "mic_preamp_2ch.kicad_sch")
    errs = compare(want, got)
    # phep pha: doi 1 chan sang net khac thi compare() PHAI bat duoc
    sabotage = {k: set(v) for k, v in got.items()}
    sabotage["IN1P"].discard("U1.5"); sabotage["IN1N"].add("U1.5")
    assert compare(want, sabotage), "phep kiem rong: khong bat duoc chan bi doi net"
    unconnected = sorted(n for n in got if n.startswith("unconnected"))
    print(f"{len(got)} net trong netlist, {len(want)} net thiet ke, net khong noi: {unconnected}")
    print("\n".join(errs) if errs else "KHOP 100% voi bang net thiet ke")
    sys.exit(1 if errs else 0)
