#!/usr/bin/env bash
# Xuat toan bo dau ra tu project hien tai. Chay tu thu muc goc project (Git Bash).
set -euo pipefail
K="/c/Program Files/KiCad/10.0/bin/kicad-cli.exe"
P=mic_preamp_2ch

mkdir -p reports fab/gerber renders
"$K" sch erc --severity-all --format report -o reports/erc_report.rpt $P.kicad_sch
"$K" sch erc --severity-all --format json   -o reports/erc_report.json $P.kicad_sch
"$K" pcb drc --severity-all --schematic-parity --format report -o reports/drc_report.rpt $P.kicad_pcb
"$K" pcb drc --severity-all --schematic-parity --format json   -o reports/drc_report.json $P.kicad_pcb

"$K" sch export pdf -o ${P}_schematic.pdf $P.kicad_sch
"$K" pcb export gerbers --layers F.Cu,B.Cu,F.Paste,B.Paste,F.SilkS,B.SilkS,F.Mask,B.Mask,Edge.Cuts \
     --subtract-soldermask -o fab/gerber/ $P.kicad_pcb
"$K" pcb export drill --format excellon --excellon-separate-th --generate-map --map-format gerberx2 \
     -o fab/gerber/ $P.kicad_pcb
"$K" pcb export pos --format csv --units mm --side both --exclude-fp-th -o fab/$P-CPL.csv $P.kicad_pcb
"$K" sch export bom --fields 'Reference,Value,Footprint,Manufacturer,MPN,LCSC,Spec,${QUANTITY}' \
     --labels 'Designator,Value,Footprint,Manufacturer,MPN,LCSC,Spec,Qty' \
     --group-by 'Value,Footprint,MPN' -o fab/$P-BOM.csv $P.kicad_sch

"$K" pcb render --side top    -w 1600 -h 1300 --quality high -o renders/pcb_3d_top.png $P.kicad_pcb
"$K" pcb render --side bottom -w 1600 -h 1300 --quality high -o renders/pcb_3d_bottom.png $P.kicad_pcb
"$K" pcb render --rotate "-45,0,30" --perspective -w 1600 -h 1200 --quality high --zoom 0.9 \
     -o renders/pcb_3d_iso.png $P.kicad_pcb
"$K" pcb export svg --layers F.Cu,F.SilkS,Edge.Cuts --exclude-drawing-sheet --fit-page-to-board --mode-single \
     -o renders/layout_top.svg $P.kicad_pcb
"$K" pcb export svg --layers B.Cu,Edge.Cuts --exclude-drawing-sheet --fit-page-to-board --mode-single --mirror \
     -o renders/layout_bottom.svg $P.kicad_pcb
"/c/Program Files/Python311/python.exe" -c "
import cairosvg
for n in ['layout_top', 'layout_bottom']:
    cairosvg.svg2png(url=f'renders/{n}.svg', write_to=f'renders/{n}.png', output_width=1800, background_color='white')"
rm renders/layout_top.svg renders/layout_bottom.svg
(cd fab && rm -f ${P}-gerber.zip && "/c/Program Files/Python311/python.exe" -c "
import zipfile, pathlib
with zipfile.ZipFile('${P}-gerber.zip', 'w', zipfile.ZIP_DEFLATED) as z:
    for f in sorted(pathlib.Path('gerber').iterdir()):
        z.write(f, f.name)")
