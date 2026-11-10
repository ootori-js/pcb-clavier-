"""Build the unrouted board (footprints placed, nets assigned, planes, outline).

Run with the system interpreter that ships KiCad's pcbnew module:
    /usr/bin/python3 gen/make_pcb.py
"""
import json, os, sys
sys.path.insert(0, os.path.dirname(__file__))
import pcbnew
import design
from placement import PLACE, BOARD_W, BOARD_H, HOLES, ANTENNA_KEEPOUT

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NAME = 'carte-linux-f1c200s'
KICAD_FP = '/usr/share/kicad/footprints'
MM = pcbnew.FromMM
POWER_NETS = ['+5V', '+3V3', '+2V5', '+1V1', '+2V8A', 'USBA_VBUS', 'LX_3V3', 'LX_2V5',
              'LX_1V1', 'BL_SW', 'LED_A', 'LED_K', 'SPK_P', 'SPK_N']


def V(x, y):
    return pcbnew.VECTOR2I(MM(x), MM(y))


def fp_path(lib):
    return os.path.join(ROOT, 'lib', 'sbc.pretty') if lib == 'sbc' else os.path.join(KICAD_FP, lib + '.pretty')


def rect_zone(board, net, layer, x1, y1, x2, y2, name=''):
    z = pcbnew.ZONE(board)
    z.SetLayer(layer)
    if net is not None:
        z.SetNet(net)
    pts = z.Outline()
    pts.NewOutline()
    for x, y in ((x1, y1), (x2, y1), (x2, y2), (x1, y2)):
        pts.Append(MM(x), MM(y))
    z.SetZoneName(name)
    z.SetLocalClearance(MM(0.2))
    z.SetMinThickness(MM(0.2))
    z.SetPadConnection(pcbnew.ZONE_CONNECTION_FULL)
    z.SetAssignedPriority(0)
    board.Add(z)
    return z


def build():
    board = pcbnew.BOARD()
    board.SetCopperLayerCount(4)
    bds = board.GetDesignSettings()
    bds.m_TrackMinWidth = MM(0.127)
    bds.m_MinClearance = MM(0.127)
    bds.m_ViasMinSize = MM(0.45)
    bds.m_MinThroughDrill = MM(0.2)
    bds.m_ViasMinAnnularWidth = MM(0.075)
    bds.m_CopperEdgeClearance = MM(0.3)
    bds.m_HoleToHoleMin = MM(0.25)
    bds.m_HoleClearance = MM(0.2)
    bds.SetBoardThickness(MM(1.6))

    # ---- nets
    nets = {}
    for name in sorted(design.nets()):
        ni = pcbnew.NETINFO_ITEM(board, name)
        board.Add(ni)
        nets[name] = ni

    # ---- outline
    for a, b in (((0, 0), (BOARD_W, 0)), ((BOARD_W, 0), (BOARD_W, BOARD_H)),
                 ((BOARD_W, BOARD_H), (0, BOARD_H)), ((0, BOARD_H), (0, 0))):
        s = pcbnew.PCB_SHAPE(board)
        s.SetShape(pcbnew.SHAPE_T_SEGMENT)
        s.SetLayer(pcbnew.Edge_Cuts)
        s.SetStart(V(*a)); s.SetEnd(V(*b)); s.SetWidth(MM(0.1))
        board.Add(s)

    # ---- footprints
    missing = [r for r in design.PARTS if r not in PLACE]
    if missing:
        sys.exit('not placed: ' + ' '.join(missing))
    for ref, p in design.PARTS.items():
        fp = pcbnew.FootprintLoad(fp_path(p['fplib']), p['fp'])
        if fp is None:
            sys.exit(f'footprint not found: {p["fp"]}')
        fp.SetFPID(pcbnew.LIB_ID(p['fplib'], p['fp']))
        fp.SetReference(ref)
        fp.SetValue(p['value'])
        fp.Value().SetVisible(False)
        fp.Reference().SetTextSize(pcbnew.VECTOR2I(MM(0.6), MM(0.6)))
        fp.Reference().SetTextThickness(MM(0.1))
        if p['lcsc']:
            fp.SetProperty('LCSC', p['lcsc'])
        if p['dnp']:
            fp.SetAttributes(fp.GetAttributes() | pcbnew.FP_EXCLUDE_FROM_BOM | pcbnew.FP_EXCLUDE_FROM_POS_FILES)
        x, y, rot = PLACE[ref]
        fp.SetPosition(V(x, y))
        fp.SetOrientationDegrees(rot)
        for pad in fp.Pads():
            net = p['pins'].get(pad.GetNumber())
            if net:
                pad.SetNet(nets[net])
        board.Add(fp)
    for i, (x, y) in enumerate(HOLES):
        fp = pcbnew.FootprintLoad(fp_path('MountingHole'), 'MountingHole_2.7mm_M2.5')
        fp.SetFPID(pcbnew.LIB_ID('MountingHole', 'MountingHole_2.7mm_M2.5'))
        fp.SetReference(f'H{i + 1}')
        fp.Reference().SetVisible(False)
        fp.Value().SetVisible(False)
        fp.SetAttributes(fp.GetAttributes() | pcbnew.FP_EXCLUDE_FROM_BOM | pcbnew.FP_EXCLUDE_FROM_POS_FILES)
        fp.SetPosition(V(x, y))
        board.Add(fp)

    # ---- inner planes
    rect_zone(board, nets['GND'], pcbnew.In1_Cu, 0, 0, BOARD_W, BOARD_H, 'GND')
    rect_zone(board, nets['+3V3'], pcbnew.In2_Cu, 0, 0, BOARD_W, BOARD_H, '3V3')

    # ---- no copper under the ESP32 antenna
    x1, y1, x2, y2 = ANTENNA_KEEPOUT
    ko = pcbnew.ZONE(board)
    ko.SetIsRuleArea(True)
    ko.SetDoNotAllowCopperPour(True); ko.SetDoNotAllowTracks(True); ko.SetDoNotAllowVias(True)
    ko.SetDoNotAllowPads(False); ko.SetDoNotAllowFootprints(False)
    ls = pcbnew.LSET()
    for l in (pcbnew.F_Cu, pcbnew.In1_Cu, pcbnew.In2_Cu, pcbnew.B_Cu):
        ls.AddLayer(l)
    ko.SetLayerSet(ls)
    o = ko.Outline(); o.NewOutline()
    for x, y in ((x1, y1), (x2, y1), (x2, y2), (x1, y2)):
        o.Append(MM(x), MM(y))
    ko.SetZoneName('antenne')
    board.Add(ko)

    out = os.path.join(ROOT, NAME + '.kicad_pcb')
    pcbnew.SaveBoard(out, board)
    write_project()
    print('wrote', out)


def write_project():
    """Project file: net classes and design rules (JLCPCB 4-layer capabilities)."""
    def cls(name, w, clr, vd, vh):
        return {"name": name, "clearance": clr, "track_width": w, "via_diameter": vd, "via_drill": vh,
                "diff_pair_gap": 0.2, "diff_pair_width": 0.2, "diff_pair_via_gap": 0.25,
                "microvia_diameter": 0.3, "microvia_drill": 0.1, "bus_width": 12, "wire_width": 6,
                "line_style": 0, "pcb_color": "rgba(0, 0, 0, 0.000)", "schematic_color": "rgba(0, 0, 0, 0.000)"}
    pro = {
        "board": {"design_settings": {"rules": {
            "min_clearance": 0.127, "min_track_width": 0.127, "min_via_diameter": 0.45,
            "min_through_hole_diameter": 0.2, "min_via_annular_width": 0.075,
            "min_copper_edge_clearance": 0.3, "min_hole_clearance": 0.2, "min_hole_to_hole": 0.25,
            "solder_mask_to_copper_clearance": 0.0, "min_silk_clearance": 0.0,
            "min_text_height": 0.5, "min_text_thickness": 0.08},
            "rule_severities": {"silk_overlap": "ignore", "silk_over_copper": "ignore",
                                "silk_edge_clearance": "ignore", "lib_footprint_issues": "ignore",
                                "lib_footprint_mismatch": "ignore", "courtyards_overlap": "warning",
                                "text_height": "ignore", "text_thickness": "ignore",
                                "solder_mask_bridge": "ignore", "footprint_type_mismatch": "ignore",
                                "npth_inside_courtyard": "ignore", "pth_inside_courtyard": "ignore"},
            "track_widths": [0.0, 0.15, 0.3, 0.5], "via_dimensions": [{"diameter": 0.0, "drill": 0.0}, {"diameter": 0.5, "drill": 0.3}]}},
        "meta": {"filename": NAME + ".kicad_pro", "version": 1},
        "net_settings": {
            "classes": [cls("Default", 0.15, 0.15, 0.5, 0.3), cls("Power", 0.3, 0.15, 0.6, 0.3)],
            "meta": {"version": 3},
            "net_colors": None,
            "netclass_assignments": None,
            "netclass_patterns": [{"netclass": "Power", "pattern": n} for n in POWER_NETS]},
        "pcbnew": {"page_layout_descr_file": ""},
        "schematic": {"legacy_lib_dir": "", "legacy_lib_list": []},
        "sheets": [], "text_variables": {}}
    json.dump(pro, open(os.path.join(ROOT, NAME + '.kicad_pro'), 'w'), indent=2)


if __name__ == '__main__':
    build()
