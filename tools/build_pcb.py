"""Dựng PCB 2 lớp từ netlist kicad-cli bằng API pcbnew của KiCad (không sửa text file).

Chạy bằng Python của KiCad, khi KiCad ĐÓNG:
  "C:/Program Files/KiCad/10.0/bin/python.exe" tools/build_pcb.py place     -> đặt linh kiện + viền + DSN
  "C:/Program Files/KiCad/10.0/bin/python.exe" tools/build_pcb.py finish    -> nạp SES, đổ đồng, lưu
Toạ độ mm, gốc góc trên-trái board, mép TRƯỚC (mặt XLR) là y = H.
"""
import re, subprocess, sys
from pathlib import Path

import pcbnew

ROOT = Path(__file__).resolve().parent.parent
PCB = ROOT / "mic_preamp_2ch.kicad_pcb"
SCH = ROOT / "mic_preamp_2ch.kicad_sch"
CLI = r"C:\Program Files\KiCad\10.0\bin\kicad-cli.exe"
FPLIB = Path(r"C:\Program Files\KiCad\10.0\share\kicad\footprints")
W, H = 100.0, 78.0
JAVA = r"C:\Users\USER\tools\jre25\jdk-25.0.5+8-jre\bin\java.exe"
FR_JAR = r"C:\Users\USER\Documents\KiCad\10.0\3rdparty\plugins\app_freerouting_kicad-plugin\jar\freerouting-2.4.1.jar"
mm = pcbnew.FromMM

HV_NETS = ["+48V", "PH1", "PH2", "XLR1_HOT", "XLR1_COLD", "XLR2_HOT", "XLR2_COLD", "P48OFF1", "P48OFF2"]
POWER_NETS = ["GND", "+15V", "-15V"]


def channel(n, cx):
    o = 0 if n == 1 else 10
    r = lambda i: f"R{i + o}"
    c = lambda i: f"C{i + o}"
    d = lambda i: f"D{i + o}"
    return {
        r(1): (cx - 7, 51.5, 90), r(2): (cx + 1, 51.5, 90),
        f"JP{n}": (cx + 8.5, 47.5, 0), r(3): (cx + 12.5, 51, 90),
        c(1): (cx - 13.5, 39, 0), c(2): (cx + 2.5, 39, 0),
        d(1): (cx - 9, 29.5, 0), d(2): (cx + 1, 29.5, 0),
        r(4): (cx - 9, 25, 0), r(5): (cx + 1, 25, 0),
        r(6): (cx - 6, 20.5, 0), r(7): (cx - 2, 20.5, 0),
        f"U{n}": (cx, 13, 0), r(8): (cx, 6.5, 0),
        c(3): (cx + 6.5, 11, 90), c(4): (cx - 6.5, 16.5, 90),
    }


PLACE = {**channel(1, 25), **channel(2, 75),
         "J3": (39, 4, 90), "C21": (44, 9.5, 0), "C22": (44, 13, 0),
         "J5": (56, 4, 90), "D21": (51, 9, 0), "D22": (51, 14, 0),
         "J4": (68, 4, 90), "C23": (48.5, 44, 90), "C24": (66, 9.5, 0),
         "H1": (4, 4, 0), "H2": (96, 4, 0), "H3": (4, H - 4, 0), "H4": (96, H - 4, 0)}


# Vi tri chu tham chieu (toa do board) cho cho bi de.
REF_AT = {"U1": (28, 19.6), "U2": (78, 19.6), "J4": (69.3, 7.2), "D22": (51, 16.6)}


def netlist():
    out = ROOT / "reports" / "mic_preamp_2ch.net"
    subprocess.run([CLI, "sch", "export", "netlist", "-o", str(out), str(SCH)], check=True, capture_output=True)
    t = re.sub(r"\s+", " ", out.read_text(encoding="utf-8"))
    comps = {}
    for ch in t.split("(libparts")[0].split("(comp (ref ")[1:]:
        ref = re.match(r'"([^"]+)"', ch).group(1)
        fields = dict(re.findall(r'\(field \(name "([^"]+)"\)(?: "([^"]*)")?\)', ch))
        comps[ref] = {"value": re.search(r'\(value "([^"]*)"\)', ch).group(1),
                      "fp": re.search(r'\(footprint "([^"]*)"\)', ch).group(1),
                      "fields": {k: v for k, v in fields.items() if k not in ("Footprint", "Value", "Reference")},
                      "datasheet": fields.get("Datasheet", ""), "description": fields.get("Description", ""),
                      "uuid": re.search(r'\(tstamps "([^"]+)"\)', ch).group(1),
                      "no_bom": '(name "exclude_from_bom")' in ch}
    pins = {}
    for ch in t.split("(net (code ")[1:]:
        name = re.search(r'\(name "([^"]*)"\)', ch).group(1)
        for r_, p in re.findall(r'\(node \(ref "([^"]+)"\) \(pin "([^"]+)"\)', ch):
            pins[(r_, p)] = name
    return comps, pins


def place():
    comps, pins = netlist()
    b = pcbnew.NewBoard(str(PCB))
    nets = {}
    for name in sorted(set(pins.values())):
        ni = pcbnew.NETINFO_ITEM(b, name)
        b.Add(ni)
        nets[name] = ni
    for ref, c in comps.items():
        lib, name = c["fp"].split(":")
        fp = pcbnew.FootprintLoad(str(FPLIB / f"{lib}.pretty"), name)
        fp.SetReference(ref)
        fp.SetValue(c["value"])
        fp.SetFPIDAsString(c["fp"])
        fp.SetField("Datasheet", c["datasheet"])
        fp.SetField("Description", c["description"])
        for k_, v_ in c["fields"].items():
            fp.SetField(k_, v_)
            fp.GetField(k_).SetVisible(False)
        fp.SetPath(pcbnew.KIID_PATH("/" + c["uuid"]))
        fp.SetSheetname("mic_preamp_2ch")
        fp.SetSheetfile("mic_preamp_2ch.kicad_sch")
        fp.SetExcludedFromBOM(c["no_bom"])
        if ref.startswith("H"):
            fp.Reference().SetVisible(False)
        b.Add(fp)
        for pad in fp.Pads():
            key = (ref, pad.GetNumber())
            if key in pins:
                pad.SetNet(nets[pins[key]])
            # INA163 Ref (pin 10) phai tro khang thap (datasheet tr.6) -> noi dac vao vung GND, khong thermal.
            # Pad GND cua header nguon/ra cung noi dac: vet OUT/+-15V chan spoke thermal lam starved_thermal.
            if (ref.startswith("U") and pad.GetNumber() == "10") or (ref in ("J3", "J4", "J5") and
                                                                      pins.get(key) == "/GND"):
                pad.SetLocalZoneConnection(pcbnew.ZONE_CONNECTION_FULL)
        if ref.startswith("J") and lib == "Connector_Audio":
            place_xlr(fp, 25 if ref == "J1" else 75)
        else:
            x, y, rot = PLACE[ref]
            fp.SetOrientationDegrees(rot)
            fp.SetPosition(pcbnew.VECTOR2I(mm(x), mm(y)))
        if ref in REF_AT:
            fp.Reference().SetPosition(pcbnew.VECTOR2I(mm(REF_AT[ref][0]), mm(REF_AT[ref][1])))
    outline(b)
    ds = b.GetDesignSettings()
    ds.m_TrackMinWidth = mm(0.15)   # neck-down vao chan SOIC 1.27 mm; JLC/PCBWay lam duoc 0.1 mm
    pcbnew.SaveBoard(str(PCB), b)
    print("placed", len(comps), "footprints,", len(nets), "nets")


def place_xlr(fp, cx):
    """Quay để mặt cắm (đường panel x=12.7 của footprint) hướng ra mép trước, rồi kéo panel trùng y=H."""
    fp.SetOrientationDegrees(270)
    fp.SetPosition(pcbnew.VECTOR2I(0, 0))
    panel = [g for g in fp.GraphicalItems() if g.GetLayer() == pcbnew.Dwgs_User][0]
    py = panel.GetStart().y
    assert panel.GetStart().y == panel.GetEnd().y, "panel line phai nam ngang sau khi quay"
    bb = fp.GetCourtyard(pcbnew.F_CrtYd).BBox()
    fp.SetPosition(pcbnew.VECTOR2I(mm(cx) - bb.Centre().x, mm(H) - py))


def outline(b):
    pts = [(0, 0), (W, 0), (W, H), (0, H)]
    for (x1, y1), (x2, y2) in zip(pts, pts[1:] + pts[:1]):
        s = pcbnew.PCB_SHAPE(b)
        s.SetShape(pcbnew.SHAPE_T_SEGMENT)
        s.SetLayer(pcbnew.Edge_Cuts)
        s.SetWidth(mm(0.1))
        s.SetStart(pcbnew.VECTOR2I(mm(x1), mm(y1)))
        s.SetEnd(pcbnew.VECTOR2I(mm(x2), mm(y2)))
        b.Add(s)


def export_dsn():
    b = pcbnew.LoadBoard(str(PCB))
    dsn = ROOT / "reports" / "route.dsn"
    assert pcbnew.ExportSpecctraDSN(b, str(dsn)), "export DSN that bai"
    t = dsn.read_text(encoding="utf-8")
    # Them class HV (khe 0.6 mm, IPC-2221B B2 cho 31-150 V) va PWR (vet 0.5 mm) cho Freerouting.
    s = t.index("(class kicad_default")
    e = t.index("(circuit", s)
    names = re.findall(r'"[^"]*"|[^\s()]+', t[s + len("(class kicad_default"):e])
    bare = lambda n: n.strip('"')
    hv = [n for n in names if bare(n)[1:] in HV_NETS ]
    pw = [n for n in names if bare(n)[1:] in POWER_NETS]
    rest = [n for n in names if n not in hv and n not in pw]
    assert len(hv) == len(HV_NETS) and len(pw) == len(POWER_NETS), (hv, pw)
    via = '(circuit (use_via "Via[0-1]_600:300_um"))'
    new = (f"(class HV {' '.join(hv)} {via} (rule (width 400) (clearance 600)))\n    "
           f"(class PWR {' '.join(pw)} {via} (rule (width 500) (clearance 250)))\n    "
           f"(class kicad_default {' '.join(rest)}\n      ")
    t = t[:s] + new + t[e:]
    t = t.replace("(width 200)\n        (clearance 200)", "(width 250)\n        (clearance 200)")
    dsn.write_text(t, encoding="utf-8")
    print("DSN:", dsn)


def route():
    """Freerouting 2.4.1 (jar cua plugin KiCad) tren JRE 25; ban CLI native 2.5.0 loi serialization GraalVM."""
    rep = ROOT / "reports"
    (rep / "route.ses").unlink(missing_ok=True)
    with open(rep / "freerouting.log", "w") as log:
        subprocess.run([JAVA, "-jar", FR_JAR, "-de", str(rep / "route.dsn"), "-do", str(rep / "route.ses"),
                        "-mp", "30", "--gui.enabled=false"], check=True, timeout=600, stdout=log,
                       stderr=subprocess.STDOUT)
    assert (rep / "route.ses").exists(), "Freerouting khong ghi SES"


def _seg_dist(px, py, ax, ay, bx, by):
    dx, dy = bx - ax, by - ay
    L = dx * dx + dy * dy
    t = 0.0 if L == 0 else max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / L))
    return ((px - ax - t * dx) ** 2 + (py - ay - t * dy) ** 2) ** 0.5


def stitch(b, pitch=6.0, keep=1.0):
    """Via khau GND tren luoi `pitch` mm; bo diem nao cach dong khac net < keep mm (tinh tu MEP) hoac nam trong courtyard."""
    gnd = b.FindNet("/GND")
    obst = []   # (kind, geom, half_width) toan bo don vi mm
    for t in b.GetTracks():
        if t.GetNetCode() == gnd.GetNetCode():
            continue
        s, e = t.GetStart(), t.GetEnd()
        hw = t.GetWidth(pcbnew.F_Cu) / 2e6 if t.GetClass() == "PCB_VIA" else t.GetWidth() / 2e6
        obst.append((s.x / 1e6, s.y / 1e6, e.x / 1e6, e.y / 1e6, hw))
    boxes = []
    for fp in b.GetFootprints():
        bb = fp.GetCourtyard(pcbnew.F_CrtYd).BBox()
        boxes.append((bb.GetLeft() / 1e6, bb.GetTop() / 1e6, bb.GetRight() / 1e6, bb.GetBottom() / 1e6))
        for p in fp.Pads():
            if p.GetNetCode() != gnd.GetNetCode():
                pb = p.GetBoundingBox()
                boxes.append((pb.GetLeft() / 1e6 - keep, pb.GetTop() / 1e6 - keep,
                              pb.GetRight() / 1e6 + keep, pb.GetBottom() / 1e6 + keep))
    r_via = 0.3
    n = 0
    y = 3.0
    while y < H - 2:
        x = 3.0
        while x < W - 2:
            ok = all(not (l <= x <= r and t_ <= y <= bt) for l, t_, r, bt in boxes)
            ok = ok and all(_seg_dist(x, y, ax, ay, bx, by) - hw - r_via >= keep for ax, ay, bx, by, hw in obst)
            if ok:
                v = pcbnew.PCB_VIA(b)
                v.SetPosition(pcbnew.VECTOR2I(mm(x), mm(y)))
                v.SetDrill(mm(0.3))
                v.SetWidth(pcbnew.F_Cu, mm(0.6))
                v.SetNet(gnd)
                b.Add(v)
                n += 1
            x += pitch
        y += pitch
    return n


def fix_starved():
    """Pad GND nao DRC bao starved_thermal (vet net khac chan spoke) -> noi dac, do dong lai. Chi pad GND."""
    import json
    rep = ROOT / "reports" / "_starved.json"
    subprocess.run([CLI, "pcb", "drc", "--format", "json", "-o", str(rep), str(PCB)], capture_output=True)
    hits = set()
    for v in json.loads(rep.read_text(encoding="utf-8"))["violations"]:
        if v["type"] == "starved_thermal":
            for it in v["items"]:
                m = re.match(r"(?:PTH )?[Pp]ad (\S+) \[/GND\] of (\S+)", it["description"])
                if m:
                    hits.add((m.group(2), m.group(1)))
    rep.unlink()
    if not hits:
        return
    b = pcbnew.LoadBoard(str(PCB))
    for ref, num in hits:
        for p in b.FindFootprintByReference(ref).Pads():
            if p.GetNumber() == num:
                p.SetLocalZoneConnection(pcbnew.ZONE_CONNECTION_FULL)
    b.BuildConnectivity()
    pcbnew.ZONE_FILLER(b).Fill(b.Zones())
    pcbnew.SaveBoard(str(PCB), b)
    print("starved -> full:", sorted(hits))


def finish():
    b = pcbnew.LoadBoard(str(PCB))
    ses = ROOT / "reports" / "route.ses"
    assert pcbnew.ImportSpecctraSES(b, str(ses)), "import SES that bai"
    print("stitch vias:", stitch(b))
    for layer in (pcbnew.F_Cu, pcbnew.B_Cu):
        z = pcbnew.ZONE(b)
        z.SetLayer(layer)
        z.SetNetCode(b.FindNet("/GND").GetNetCode())
        z.SetLocalClearance(mm(0.6))
        z.SetMinThickness(mm(0.25))
        z.SetIslandRemovalMode(pcbnew.ISLAND_REMOVAL_MODE_ALWAYS)
        o = z.Outline()
        o.NewOutline()
        for x, y in [(0.6, 0.6), (W - 0.6, 0.6), (W - 0.6, H - 0.6), (0.6, H - 0.6)]:
            o.Append(mm(x), mm(y))
        z.thisown = 0
        b.Add(z)
    b.BuildConnectivity()
    pcbnew.ZONE_FILLER(b).Fill(b.Zones())
    pcbnew.SaveBoard(str(PCB), b)
    fix_starved()
    b = pcbnew.LoadBoard(str(PCB))
    b.BuildConnectivity()
    print("unconnected:", b.GetConnectivity().GetUnconnectedCount(True),
          "tracks:", len(b.GetTracks()), "zones:", len(list(b.Zones())))


if __name__ == "__main__":
    {"place": lambda: (place(), export_dsn()), "dsn": export_dsn, "route": route, "finish": finish,
     "all": lambda: (place(), export_dsn(), route(), finish())}[sys.argv[1]]()
