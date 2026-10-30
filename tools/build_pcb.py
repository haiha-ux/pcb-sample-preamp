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

HV_NETS = ["+48V", "PH1", "PH2", "XLR1_HOT", "XLR1_COLD", "XLR2_HOT", "XLR2_COLD", "P48OFF1", "P48OFF2",
           "P1H", "P1C", "P2H", "P2C"]
POWER_NETS = ["GND", "+15V", "-15V"]


CX = {1: 25.0, 2: 75.0}           # truc giua moi kenh
LEG = 5.75                         # nua khoang cach 2 chan hot/cold (2 tu 10 mm dat canh nhau)
W_HV, W_SIG = 0.4, 0.3
Y_CAP = 50.0                       # pad duoi cua tu chan DC (phia XLR)
Y_D, Y_BIAS, Y_RS = 40.5, 36.0, 31.9
Y_CONV = 22.5                      # het doan cheo, vao chan IC thang dung

# Linh kien KHONG nam tren duong tin hieu: dat theo toa do co dinh.
PLACE = {"JP1": (45.5, 38, 0), "R3": (47.5, 52, 90), "JP2": (54.5, 38, 0), "R13": (52.5, 52, 90),
         "J3": (39, 4, 90), "C21": (44, 9.5, 0), "C22": (44, 13, 0),
         "J5": (56, 4, 90), "D21": (51, 9, 0), "D22": (51, 14, 0),
         "J4": (68, 4, 90), "C23": (48.25, 30, 0), "C24": (66, 9.5, 0),
         "H1": (4, 4, 0), "H2": (96, 4, 0), "H3": (4, H - 4, 0), "H4": (96, H - 4, 0)}

# Vi tri chu tham chieu (toa do board) cho cho bi de.
REF_AT = {"U1": (CX[1] + 5.5, 17.6), "U2": (CX[2] + 5.5, 17.6), "J4": (69.3, 7.2), "D22": (51, 16.6)}


def chain_refs(n):
    o = 0 if n == 1 else 10
    return {"Ch": f"C{1 + o}", "Cc": f"C{2 + o}", "Rh1": f"R{1 + o}", "Rh2": f"R{9 + o}",
            "Rc1": f"R{2 + o}", "Rc2": f"R{10 + o}", "Dh": f"D{1 + o}", "Dc": f"D{2 + o}",
            "Rbh": f"R{4 + o}", "Rbc": f"R{5 + o}", "Rsh": f"R{6 + o}", "Rsc": f"R{7 + o}",
            "Rg": f"R{8 + o}", "U": f"U{n}", "Cp": f"C{3 + o}", "Cn": f"C{4 + o}", "J": f"J{n}"}


def V(x, y):
    return pcbnew.VECTOR2I(mm(x), mm(y))


def P(b, ref, num):
    for p in b.FindFootprintByReference(ref).Pads():
        if p.GetNumber() == num:
            q = p.GetPosition()
            return q.x / 1e6, q.y / 1e6
    raise KeyError(f"{ref}.{num}")


def at_pad(b, ref, num, x, y, rot):
    """Dat footprint sao cho pad `num` roi dung (x, y) sau khi quay `rot`."""
    fp = b.FindFootprintByReference(ref)
    fp.SetOrientationDegrees(rot)
    fp.SetPosition(V(0, 0))
    px, py = P(b, ref, num)
    fp.SetPosition(V(x - px, y - py))


def place_channel(b, n):
    k, cx = chain_refs(n), CX[n]
    xc, xh = cx - LEG, cx + LEG
    at_pad(b, k["Cc"], "1", xc, Y_CAP, 90)
    at_pad(b, k["Ch"], "1", xh, Y_CAP, 90)
    assert abs(P(b, k["Cc"], "2")[1] - (Y_CAP - 5)) < 1e-3, "tu phai dung doc, pad2 phia tren"
    # Phantom: 2 x 1206 noi tiep, toa ra ngoai tu hai pad duoi cua tu.
    at_pad(b, k["Rc1"], "2", xc - 6.2, Y_CAP, 0)
    at_pad(b, k["Rc2"], "2", P(b, k["Rc1"], "1")[0] - 2.0, Y_CAP, 0)
    at_pad(b, k["Rh1"], "2", xh + 6.2, Y_CAP, 180)
    at_pad(b, k["Rh2"], "2", P(b, k["Rh1"], "1")[0] + 2.0, Y_CAP, 180)
    # Kep diode va R bias: shunt ra ngoai, chan noi vao chan tin hieu huong vao trong.
    at_pad(b, k["Dc"], "3", xc - 1.7, Y_D, 0)
    at_pad(b, k["Dh"], "3", xh + 1.7, Y_D, 180)
    at_pad(b, k["Rbc"], "1", xc - 1.5, Y_BIAS, 180)
    at_pad(b, k["Rbh"], "1", xh + 1.5, Y_BIAS, 0)
    # R noi tiep nam THANG tren chan tin hieu.
    at_pad(b, k["Rsc"], "1", xc, Y_RS, 90)
    at_pad(b, k["Rsh"], "1", xh, Y_RS, 90)
    assert P(b, k["Rsc"], "2")[1] < Y_RS, "R noi tiep: pad2 phai o phia IC"
    # IC quay 90: hang chan duoi (1..7) huong ve XLR, ngo ra (8, 9) o hang tren.
    at_pad(b, k["U"], "4", cx - 0.635, 20.475, 90)
    (x5, y5), (x9, y9) = P(b, k["U"], "5"), P(b, k["U"], "9")
    assert abs(x5 - (cx + 0.635)) < 1e-3 and abs(y5 - 20.475) < 1e-3 and y9 < y5, (x5, y5, y9)
    at_pad(b, k["Rg"], "1", cx - 6.635, 18.95, 90)
    at_pad(b, k["Cp"], "1", P(b, k["U"], "11")[0], 12.75, 90)
    at_pad(b, k["Cn"], "2", P(b, k["U"], "6")[0] + 3.45, 21.9, 180)
    # Chu tham chieu: tu o tam than tu, con lai day ra phia ngoai kenh cho khoi de nhau.
    refpos = {k["Cc"]: (xc, Y_CAP - 2.5), k["Ch"]: (xh, Y_CAP - 2.5),
              k["Rc1"]: (P(b, k["Rc1"], "1")[0] + 1.46, Y_CAP + 1.9),
              k["Rc2"]: (P(b, k["Rc2"], "1")[0] + 1.46, Y_CAP + 1.9),
              k["Rh1"]: (P(b, k["Rh1"], "1")[0] - 1.46, Y_CAP + 1.9),
              k["Rh2"]: (P(b, k["Rh2"], "1")[0] - 1.46, Y_CAP + 1.9),
              k["Dc"]: (xc - 6.1, Y_D), k["Dh"]: (xh + 6.1, Y_D),
              k["Rbc"]: (xc - 5.6, Y_BIAS), k["Rbh"]: (xh + 5.6, Y_BIAS)}
    for ref, (x, y) in refpos.items():
        b.FindFootprintByReference(ref).Reference().SetPosition(V(x, y))


def track(b, pts, net, layer, w):
    ni = b.FindNet(net)
    assert ni is not None, net
    for (x1, y1), (x2, y2) in zip(pts, pts[1:]):
        if (x1, y1) == (x2, y2):
            continue
        t = pcbnew.PCB_TRACK(b)
        t.SetStart(V(x1, y1))
        t.SetEnd(V(x2, y2))
        t.SetWidth(mm(w))
        t.SetLayer(layer)
        t.SetNet(ni)
        t.SetLocked(True)
        b.Add(t)


def gnd_via(b, x, y):
    v = pcbnew.PCB_VIA(b)
    v.SetPosition(V(x, y))
    v.SetDrill(mm(0.3))
    v.SetWidth(pcbnew.F_Cu, mm(0.6))
    v.SetNet(b.FindNet("/GND"))
    v.SetLocked(True)
    b.Add(v)


def hand_route(b, n):
    """Di tay toan bo duong tin hieu vao cua kenh n: doi xung hot/cold, ngan, ngo ra tach khoi ngo vao."""
    k, cx = chain_refs(n), CX[n]
    xc, xh = cx - LEG, cx + LEG
    F, B = pcbnew.F_Cu, pcbnew.B_Cu
    s = lambda name: f"/{name}{n}" if name in ("PH",) else f"/{name}"
    hot, cold = f"/XLR{n}_HOT", f"/XLR{n}_COLD"
    (x2, y2), (x3, y3) = P(b, k["J"], "2"), P(b, k["J"], "3")
    # XLR -> tu: cold tren F.Cu, hot tren B.Cu (2 chan phai bat cheo 1 lan vi thu tu chan XLR nguoc thu tu IC).
    ya = y3 - 2.0
    assert ya - (x3 - xc) >= Y_CAP, "doan cheo cold khong du cho"
    track(b, [(x3, y3), (x3, ya), (xc, ya - (x3 - xc)), (xc, Y_CAP)], cold, F, W_HV)
    yb = y2 - 3.7
    assert yb - (xh - x2) >= Y_CAP, "doan cheo hot khong du cho"
    track(b, [(x2, y2), (x2, yb), (xh, yb - (xh - x2)), (xh, Y_CAP)], hot, B, W_HV)
    # Phantom: tu pad duoi tu ra cap dien tro.
    track(b, [P(b, k["Cc"], "1"), P(b, k["Rc1"], "2")], cold, F, W_HV)
    track(b, [P(b, k["Rc1"], "1"), P(b, k["Rc2"], "2")], f"/P{n}C", F, W_HV)
    track(b, [P(b, k["Ch"], "1"), P(b, k["Rh1"], "2")], hot, F, W_HV)
    track(b, [P(b, k["Rh1"], "1"), P(b, k["Rh2"], "2")], f"/P{n}H", F, W_HV)
    for side, x, sgn in (("N", xc, -1), ("P", xh, +1)):
        C, D, Rb, Rs = (k["Cc"], k["Dc"], k["Rbc"], k["Rsc"]) if side == "N" else (k["Ch"], k["Dh"], k["Rbh"], k["Rsh"])
        prot, inp = f"/IN{n}{side}_PROT", f"/IN{n}{side}"
        track(b, [P(b, C, "2"), P(b, Rs, "1")], prot, F, W_SIG)
        track(b, [P(b, D, "3"), (x, P(b, D, "3")[1])], prot, F, W_SIG)
        track(b, [P(b, Rb, "1"), (x, P(b, Rb, "1")[1])], prot, F, W_SIG)
        gx, gy = P(b, Rb, "2")
        track(b, [(gx, gy), (gx + sgn * 1.3, gy)], "/GND", F, W_SIG)
        gnd_via(b, gx + sgn * 1.3, gy)
        # Hoi tu doi xung vao chan IC.
        pin = P(b, k["U"], "4" if side == "N" else "5")
        dx = abs(x - pin[0])
        track(b, [P(b, Rs, "2"), (x, Y_CONV + dx), (pin[0], Y_CONV), pin], inp, F, W_SIG)
    # RG: vong quanh dau IC, ngan nhat co the.
    (x3u, y3u), (x12, y12) = P(b, k["U"], "3"), P(b, k["U"], "12")
    xr = P(b, k["Rg"], "1")[0]
    track(b, [(x3u, y3u), (x3u, 21.9), (xr, 21.9), P(b, k["Rg"], "1")], f"/RG{n}A", F, W_SIG)
    track(b, [(x12, y12), (x12, 14.1), (xr, 14.1), P(b, k["Rg"], "2")], f"/RG{n}B", F, W_SIG)
    # Decoupling + Ref + noi Sense/VO o hang tren.
    track(b, [P(b, k["U"], "11"), P(b, k["Cp"], "1")], "/+15V", F, W_SIG)
    cx2, cy2 = P(b, k["Cp"], "2")
    track(b, [(cx2, cy2), (cx2, cy2 - 1.3)], "/GND", F, W_SIG)
    gnd_via(b, cx2, cy2 - 1.3)
    x10, y10 = P(b, k["U"], "10")
    track(b, [(x10, y10), (x10, 13.6)], "/GND", F, W_SIG)
    gnd_via(b, x10, 13.6)
    (x9, y9), (x8, y8) = P(b, k["U"], "9"), P(b, k["U"], "8")
    out = f"/OUT{n}"
    track(b, [(x9, y9), (x9, 14.0), (x8, 14.0), (x8, y8)], out, F, W_SIG)
    # Ngo ra: via canh IC, chay B.Cu len vung connector phia tren — xa han ngo vao (datasheet tr.6).
    vx = x8 + 1.2
    track(b, [(x8, 14.0), (vx, 14.0)], out, F, W_SIG)
    v = pcbnew.PCB_VIA(b)
    v.SetPosition(V(vx, 14.0))
    v.SetDrill(mm(0.3))
    v.SetWidth(pcbnew.F_Cu, mm(0.6))
    v.SetNet(b.FindNet(out))
    v.SetLocked(True)
    b.Add(v)
    jx, jy = P(b, "J5", "1" if n == 1 else "3")
    y_bus = 7.5
    knee = jx - (y_bus - jy) if n == 1 else jx + (y_bus - jy)
    track(b, [(vx, 14.0), (vx, y_bus), (knee, y_bus), (jx, jy)], out, B, W_SIG)
    x6, y6 = P(b, k["U"], "6")
    track(b, [(x6, y6), (x6, 21.9), P(b, k["Cn"], "2")], "/-15V", F, W_SIG)
    nx, ny = P(b, k["Cn"], "1")
    track(b, [(nx, ny), (nx + 1.3, ny)], "/GND", F, W_SIG)
    gnd_via(b, nx + 1.3, ny)


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
        elif ref in PLACE:
            x, y, rot = PLACE[ref]
            fp.SetOrientationDegrees(rot)
            fp.SetPosition(pcbnew.VECTOR2I(mm(x), mm(y)))
    for n in (1, 2):
        place_channel(b, n)
    placed = set(PLACE) | {r for n in (1, 2) for r in chain_refs(n).values()}
    missing = [r for r in comps if r not in placed]
    assert not missing, f"chua co vi tri: {missing}"
    for ref, (x, y) in REF_AT.items():
        b.FindFootprintByReference(ref).Reference().SetPosition(V(x, y))
    for n in (1, 2):
        hand_route(b, n)
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
