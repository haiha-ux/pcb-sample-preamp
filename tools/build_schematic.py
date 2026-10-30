"""Dựng lại toàn bộ schematic qua Konnect (stdio JSON-RPC) — không sửa tay file .kicad_sch.

Chạy: python tools/build_schematic.py   (file schematic cũ phải được dời đi trước)
Bố cục: khổ A3, kênh 1 ở trên (y0=60), kênh 2 ở dưới (y0=150), khối nguồn bên phải.
"""
import json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))
from kcall import Konnect  # noqa: E402

SCH = str(ROOT / "mic_preamp_2ch.kicad_sch")
FP_R0805 = "Resistor_SMD:R_0805_2012Metric"
FP_R1206 = "Resistor_SMD:R_1206_3216Metric"
FP_C0805 = "Capacitor_SMD:C_0805_2012Metric"
FP_HDR = "Connector_PinHeader_2.54mm:PinHeader_1x0{}_P2.54mm_Vertical"


def channel(n: int, y0: float) -> list[dict]:
    o = 0 if n == 1 else 10          # ch1: R1.., ch2: R11..
    r = lambda i: f"R{i + o}"
    c = lambda i: f"C{i + o}"
    d = lambda i: f"D{i + o}"
    return [
        {"lib_id": "Connector_Audio:XLR3", "reference": f"J{n}", "value": "NC3FAH1", "x": 33.02, "y": y0,
         "footprint": "Connector_Audio:Jack_XLR_Neutrik_NC3FAH1_Horizontal"},
        {"lib_id": "Device:R", "reference": r(1), "value": "3.40k", "x": 50.8, "y": y0 - 17.78,
         "footprint": FP_R1206},
        {"lib_id": "Device:R", "reference": r(9), "value": "3.40k", "x": 50.8, "y": y0 - 27.94,
         "footprint": FP_R1206},
        {"lib_id": "Device:R", "reference": r(2), "value": "3.40k", "x": 68.58, "y": y0 - 17.78,
         "footprint": FP_R1206},
        {"lib_id": "Device:R", "reference": r(10), "value": "3.40k", "x": 68.58, "y": y0 - 27.94,
         "footprint": FP_R1206},
        {"lib_id": "Jumper:Jumper_3_Open", "reference": f"JP{n}", "value": "P48 ON=1-2 OFF=2-3",
         "x": 59.69, "y": y0 - 38.1, "footprint": FP_HDR.format(3)},
        {"lib_id": "Device:R", "reference": r(3), "value": "47k", "x": 86.36, "y": y0 - 36.83, "footprint": FP_R0805},
        {"lib_id": "Device:C", "reference": c(1), "value": "47u 63V NP", "x": 99.06, "y": y0, "rotation": 90,
         "footprint": "Capacitor_THT:C_Radial_D10.0mm_H20.0mm_P5.00mm"},
        {"lib_id": "Device:C", "reference": c(2), "value": "47u 63V NP", "x": 99.06, "y": y0 + 15.24, "rotation": 90,
         "footprint": "Capacitor_THT:C_Radial_D10.0mm_H20.0mm_P5.00mm"},
        {"lib_id": "Diode:BAV99", "reference": d(1), "value": "BAV99", "x": 124.46, "y": y0 - 12.7},
        {"lib_id": "Diode:BAV99", "reference": d(2), "value": "BAV99", "x": 124.46, "y": y0 + 30.48},
        {"lib_id": "Device:R", "reference": r(4), "value": "2.2k", "x": 144.78, "y": y0 + 7.62,
         "footprint": FP_R0805},
        {"lib_id": "Device:R", "reference": r(5), "value": "2.2k", "x": 165.1, "y": y0 + 7.62,
         "footprint": FP_R0805},
        {"lib_id": "Device:R", "reference": r(6), "value": "10R", "x": 195.58, "y": y0, "rotation": 90,
         "footprint": FP_R0805},
        {"lib_id": "Device:R", "reference": r(7), "value": "10R", "x": 195.58, "y": y0 + 15.24, "rotation": 90,
         "footprint": FP_R0805},
        {"lib_id": "Device:R", "reference": r(8), "value": "60.4R", "x": 215.9, "y": y0 + 7.62, "footprint": FP_R0805},
        {"lib_id": "preamp:INA163UA", "reference": f"U{n}", "value": "INA163UA", "x": 241.3, "y": y0 + 7.62,
         "footprint": "Package_SO:SOIC-14_3.9x8.7mm_P1.27mm"},
        {"lib_id": "Device:C", "reference": c(3), "value": "100n", "x": 271.78, "y": y0 - 6.35, "footprint": FP_C0805},
        {"lib_id": "Device:C", "reference": c(4), "value": "100n", "x": 271.78, "y": y0 + 21.59, "footprint": FP_C0805},
    ]


POWER = [
    {"lib_id": "Connector_Generic:Conn_01x03", "reference": "J3", "value": "PWR +15/GND/-15", "x": 312.42, "y": 50.8,
     "footprint": FP_HDR.format(3)},
    {"lib_id": "Connector_Generic:Conn_01x02", "reference": "J4", "value": "P48 +48/GND", "x": 312.42, "y": 106.68,
     "footprint": FP_HDR.format(2)},
    {"lib_id": "Connector_Generic:Conn_01x04", "reference": "J5", "value": "OUT1/GND/OUT2/GND", "x": 312.42, "y": 160.02,
     "footprint": FP_HDR.format(4)},
    {"lib_id": "Device:C", "reference": "C21", "value": "10u 25V", "x": 347.98, "y": 43.18,
     "footprint": "Capacitor_SMD:C_1206_3216Metric"},
    {"lib_id": "Device:C", "reference": "C22", "value": "10u 25V", "x": 347.98, "y": 66.04,
     "footprint": "Capacitor_SMD:C_1206_3216Metric"},
    {"lib_id": "Diode:SMAJ16A", "reference": "D21", "value": "SMAJ16A", "x": 368.3, "y": 43.18, "rotation": 90,
     "footprint": "Diode_SMD:D_SMA"},
    {"lib_id": "Diode:SMAJ16A", "reference": "D22", "value": "SMAJ16A", "x": 368.3, "y": 66.04, "rotation": 90,
     "footprint": "Diode_SMD:D_SMA"},
    {"lib_id": "Device:C_Polarized", "reference": "C23", "value": "47u 100V", "x": 347.98, "y": 106.68,
     "footprint": "Capacitor_THT:CP_Radial_D8.0mm_P3.50mm"},
    {"lib_id": "Device:C", "reference": "C24", "value": "100n 100V", "x": 365.76, "y": 106.68, "footprint": FP_C0805},
    {"lib_id": "power:PWR_FLAG", "reference": "#FLG1", "x": 378.46, "y": 38.1},
    {"lib_id": "power:PWR_FLAG", "reference": "#FLG2", "x": 378.46, "y": 63.5},
    {"lib_id": "power:PWR_FLAG", "reference": "#FLG3", "x": 393.7, "y": 38.1},
    {"lib_id": "power:PWR_FLAG", "reference": "#FLG4", "x": 393.7, "y": 101.6},
] + [{"lib_id": "Mechanical:MountingHole", "reference": f"H{i}", "value": "M3", "x": 312.42 + 15.24 * (i - 1),
      "y": 205.74, "footprint": "MountingHole:MountingHole_3.2mm_M3"} for i in range(1, 5)]

NOTES = [
    (20.32, 236.22, "THIET KE THEO TI INA163 (SBOS177D) Figure 5 trang 8 - Phantom-Powered Microphone Preamplifier."),
    (20.32, 241.3, "Gain G = 1 + 6000/RG; RG = 60.4R -> G = 100.3 (40.0 dB). Doi R8/R18 de doi gain (bang RG trang 6)."),
    (20.32, 246.38, "Moi chan phantom = 2 x 3.40k 0.1% 1206 noi tiep (6.80k, khop 0.1% cho CMRR). Khi chan mic chap GND: 0.34W chia 2 = 0.17W/con (dinh muc 0.25W)."),
    (20.32, 251.46, "C1/C2 khong phan cuc: datasheet note (1) - bat buoc khi co the tat phantom."),
    (20.32, 256.54, "D1/D2 BAV99 kep ve +/-15V (datasheet goi y 4x 1N4148). R6/R7 10R thin film: chia dong voi diode kep noi cua INA163 (abs max 10mA); nhieu them 0.57 nV/rtHz (2x10R) so voi 1 nV/rtHz cua IC."),
    (20.32, 261.62, "JP1/JP2: ON = noi 1-2 (+48V), OFF = noi 2-3 (xa tu qua 47k xuong GND, nhu R3 trong Fig.5). Header 2.54mm cung dung de noi cong tac mat may."),
    (20.32, 266.7, "XLR NC3FAH1: chan 1 = GND, vo connector noi chan 1 ben trong (theo mo ta Neutrik). Chan 2 = nong (+), chan 3 = nguoi (-)."),
    (20.32, 271.78, "D21/D22 SMAJ16A: kep rail +/-15V khi cam/rut mic luc dang bat P48 (tu 47u nap 48V xa qua BAV99 vao rail). Khong co trong datasheet - them theo kinh nghiem thiet ke."),
    (20.32, 276.86, "Ngo ra DC-coupled (khong lap servo OPA134 cua Fig.5): offset xau nhat ~0.25V o G=100 -> tang sau phai AC-couple."),
]


def apply_mpn(k):
    table = json.loads((ROOT / "tools" / "bom_mpn.json").read_text(encoding="utf-8"))
    updates = [{"reference": ref, "fields": props} for refs, props in table.items() for ref in refs.split(",")]
    r = k.call("batch_edit_schematic_components", {"schematic": SCH, "edits": updates, "create_missing": True})
    assert not r.get("errors") and not r.get("failures"), r
    return len(updates)


def main():
    if sys.argv[1:] == ["--mpn-only"]:
        k = Konnect()
        k.call("load_toolset", {"name": ["sch_batch"]})
        print("mpn:", apply_mpn(k), "linh kien")
        return
    k = Konnect()
    k.call("load_toolset", {"name": ["sch_wiring", "sch_components", "sch_batch", "sch_hierarchy", "sch_export"]})
    if Path(SCH).exists():
        sys.exit(f"{SCH} da ton tai — doi ten/doi di truoc khi dung lai")
    k.call("create_schematic", {"path": SCH, "size": "A3"})
    placed = k.call("batch_place_components", {"schematic": SCH,
                                               "components": channel(1, 60.96) + channel(2, 152.4) + POWER})
    assert placed["placed_count"] == 2 * 19 + 17, placed.get("errors")
    nets = json.loads((ROOT / "tools" / "design_nets.json").read_text(encoding="utf-8"))
    # Diem giua 2 dien tro phantom noi tiep: noi bang day thang + 1 nhan, khong dung 2 nhan chong nhau.
    wired = {n: ps for n, ps in nets.items() if n in ("P1H", "P1C", "P2H", "P2C")}
    for net, (a, b) in wired.items():
        (ra, pa), (rb, pb) = a.rsplit(".", 1), b.rsplit(".", 1)
        k.call("batch_connect_pins", {"schematic": SCH, "connections": [{"ref1": ra, "pin1": pa, "ref2": rb, "pin2": pb}]})
        locs = k.call("batch_get_schematic_pin_locations", {"schematic": SCH, "references": [ra]})
        p = next(p for p in locs["components"][0]["pins"] if p["number"] == pa)
        k.call("add_schematic_net_label", {"schematic": SCH, "net": net, "x": round(p["x"], 2),
                                           "y": round(p["y"] - 1.27, 2)})
    for net, pins in nets.items():
        if net in wired:
            continue
        ps = [{"reference": p.rsplit(".", 1)[0], "pin_number": p.rsplit(".", 1)[1]} for p in pins]
        r = k.call("batch_connect_to_net", {"schematic": SCH, "net_name": net, "pins": ps, "stub_length": 2.54})
        assert not r.get("errors"), (net, r["errors"])
    locs = k.call("batch_get_schematic_pin_locations", {"schematic": SCH, "references": ["U1", "U2"]})
    nc = [{"x": round(p["x"], 2), "y": round(p["y"], 2)} for c in locs["components"] for p in c["pins"]
          if p["number"] in ("1", "14")]
    k.call("batch_add_no_connect", {"schematic": SCH, "positions": nc})
    for x, y, t in NOTES:
        k.call("add_schematic_text", {"schematic": SCH, "text": t, "x": x, "y": y, "size": 1.8})
    print("mpn:", apply_mpn(k), "linh kien")
    print("xong:", placed["placed_count"], "symbol,", len(nets), "net,", len(nc), "no-connect")


if __name__ == "__main__":
    main()
