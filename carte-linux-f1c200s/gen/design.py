"""Single source of truth for the board: every part and every connection.

The schematic, the PCB, the BOM and the placement file are all generated
from the PARTS list built here.  Run `python3 gen/design.py` to print a
summary and sanity checks.
"""
from collections import OrderedDict, defaultdict

PARTS = OrderedDict()      # ref -> dict
GROUPS = OrderedDict()     # group title -> [refs]
_group = [None]


def group(title):
    _group[0] = title
    GROUPS.setdefault(title, [])


def part(ref, value, lcsc, sym, fp, pins, dnp=False, lib='sbc', fplib='sbc'):
    """pins: {pin_number(str): net name}.  Net None/'' = not connected."""
    assert ref not in PARTS, ref
    PARTS[ref] = dict(ref=ref, value=value, lcsc=lcsc, sym=sym, fp=fp, lib=lib,
                      fplib=fplib, pins={str(k): v for k, v in pins.items() if v},
                      dnp=dnp, group=_group[0])
    GROUPS[_group[0]].append(ref)


# ---------------------------------------------------------------- passives
R_SYM, C_SYM = '0402WGF1002TCE', 'CL05B104KO5NNNC'
RES = {  # value -> (lcsc, footprint)   all JLCPCB "basic" parts
    '0R': ('C17168', 'R0402'), '100R': ('C25076', 'R0402'),
    '1k': ('C11702', 'R0402'), '2.2k': ('C25879', 'R0402'),
    '4.7k': ('C25900', 'R0402'), '5.1k': ('C25905', 'R0402'),
    '10k': ('C25744', 'R0402'), '12k': ('C25752', 'R0402'),
    '15k': ('C25756', 'R0402'), '22k': ('C25768', 'R0402'),
    '47k': ('C25792', 'R0402'), '100k': ('C25741', 'R0402'),
    '5.1R': ('C25197', 'R0603'),
}
CAP = {
    '18pF': ('C1549', 'C0402'), '100nF': ('C1525', 'C0402'),
    '1uF': ('C52923', 'C0402'), '4.7uF': ('C23733', 'C0402'),
    '10uF': ('C19702', 'C0603'), '22uF': ('C45783', 'C0805'),
    '1uF/50V': ('C15849', 'C0603'),
}
_n = defaultdict(int)


def _auto(prefix):
    _n[prefix] += 1
    return f'{prefix}{_n[prefix]}'


def R(value, a, b):
    lcsc, fp = RES[value]
    part(_auto('R'), value, lcsc, R_SYM, fp, {1: a, 2: b})


def C(value, a, b='GND'):
    lcsc, fp = CAP[value]
    part(_auto('C'), value, lcsc, C_SYM, fp, {1: a, 2: b})


GND = 'GND'
V5, V33, V25, V11, V28 = '+5V', '+3V3', '+2V5', '+1V1', '+2V8A'

# ================================================================ POWER IN
group('Alimentation USB-C + console serie')
part('J1', 'USB-C (alim + console)', 'C165948', 'TYPE-C-31-M-12',
     'USB-C_SMD-TYPE-C-31-M-12_1',
     {'A4B9': V5, 'B4A9': V5, 'A1B12': GND, 'B1A12': GND,
      '1': GND, '2': GND, '3': GND, '4': GND,
      'A5': 'USBC_CC1', 'B5': 'USBC_CC2',
      'A6': 'USBC_DP', 'B6': 'USBC_DP', 'A7': 'USBC_DM', 'B7': 'USBC_DM'})
R('5.1k', 'USBC_CC1', GND)
R('5.1k', 'USBC_CC2', GND)
C('10uF', V5)
C('22uF', V5)
part('U6', 'CH340N', 'C2977777', 'CH340N_C2977777',
     'SOP-8_L4.9-W3.9-P1.27-LS6.0-BL',
     {1: 'USBC_DP', 2: 'USBC_DM', 3: GND, 5: V33, 8: V33,
      6: 'CH340_TXD', 7: 'UART0_TX'})
R('1k', 'CH340_TXD', 'UART0_RX')      # lets an external UART override the console
C('100nF', V33)

# ============================================================== REGULATORS
group('Regulateurs 3V3 / 2V5 / 1V1 / 2V8')
part('U2', 'EA3036C', 'C570857', 'EA3036C', 'WQFN-20_L3.0-W3.0-P0.40-BL-EP',
     {10: V5, 7: V5, 19: V5, 16: V5, 9: V5, 8: V5, 18: V5,
      11: 'LX_3V3', 6: 'LX_2V5', 20: 'LX_1V1',
      14: 'FB_3V3', 3: 'FB_2V5', 2: 'FB_1V1',
      1: GND, 4: GND, 5: GND, 12: GND, 13: GND, 15: GND, 17: GND, 21: GND})
for lx, vout, fb, rtop, rbot in (('LX_3V3', V33, 'FB_3V3', '100k', '22k'),   # 3.33 V
                                 ('LX_2V5', V25, 'FB_2V5', '47k', '15k'),    # 2.48 V
                                 ('LX_1V1', V11, 'FB_1V1', '10k', '12k')):   # 1.10 V
    part(_auto('L'), '2.2uH 3.4A', 'C135262', 'SMNR4020-2.2UH',
         'IND-SMD_L4.0-W4.0_LQH44PN2R2MP0L', {1: lx, 2: vout})
    R(rtop, vout, fb)
    R(rbot, fb, GND)
    C('10uF', V5)
    C('22uF', vout)
C('100nF', V5)
part('U3', 'ME6211C28 (2.8V)', 'C53099', 'ME6211C28M5G',
     'SOT-23-5_L3.0-W1.7-P0.95-LS2.8-BR', {1: V5, 2: GND, 3: V5, 5: V28})
C('1uF', V5)
C('1uF', V28)
part('LED1', 'LED rouge (alim)', 'C2286', 'KT-0603R', 'LED-SMD_L1.6-W0.8-R-RD',
     {'1': 'LED_PWR_A', '2': GND})
R('1k', V33, 'LED_PWR_A')

# ===================================================================== SOC
group('Processeur Allwinner F1C200S')
soc = {
    # power
    5: V33, 20: V33, 50: V33, 22: V11, 35: V11, 71: V11,
    30: V25, 31: V25, 32: V25, 34: V25, 36: V25, 33: 'SVREF',
    67: V33, 73: V33, 74: GND, 82: GND, 89: GND, 80: V28, 4: V28,
    # clock / reset
    51: 'HOSCI', 52: 'HOSCO', 70: 'RESET_N',
    # audio codec
    1: 'HPL', 88: 'HPR', 2: 'HPCOM', 3: 'HPCOM', 87: 'MICIN',
    81: 'VRA1', 83: 'VRA2', 79: 'LRADC0',
    # TV
    72: 'TVOUT', 76: 'TV_VRP', 75: GND,
    # USB host
    69: 'USB_DP', 68: 'USB_DM',
    # touch panel / PA port
    66: 'PA0_TPX1', 65: 'PA1_TPX2', 64: 'PA2_TPY1', 63: 'PA3_TPY2',
    # SPI flash (PC)
    59: 'SPI0_CLK', 60: 'SPI0_CS', 61: 'SPI0_MISO', 62: 'SPI0_MOSI',
    # microSD (PF)
    58: 'SD_D1', 57: 'SD_D0', 56: 'SD_CLK', 55: 'SD_CMD', 54: 'SD_D3', 53: 'SD_D2',
    # PE port
    49: 'UART0_RX', 48: 'UART0_TX', 47: 'ESP_EN', 46: 'ESP_DRDY', 45: 'ESP_HS',
    44: 'PE5_AMP_EN', 43: 'LCD_BL_PWM', 42: 'ESP_CS', 41: 'ESP_MOSI',
    40: 'ESP_CLK', 39: 'ESP_MISO', 38: 'I2C_SCL', 37: 'I2C_SDA',
}
# RGB LCD on PD0..PD21: B2..B7, G2..G7, R2..R7, CLK, DE, HSYNC, VSYNC
pd_pins = [6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 21, 23, 24, 25, 26, 27, 28, 29]
pd_nets = ([f'LCD_B{i}' for i in range(2, 8)] + [f'LCD_G{i}' for i in range(2, 8)] +
           [f'LCD_R{i}' for i in range(2, 8)] + ['LCD_CLK', 'LCD_DE', 'LCD_HSYNC', 'LCD_VSYNC'])
soc.update(dict(zip(pd_pins, pd_nets)))
part('U1', 'F1C200S', 'C2879851', 'F1C200S', 'QFN-88_L10.0-W10.0-P0.40-BL-EP6.75', soc)

for _ in range(3):
    C('100nF', V33)        # VCC-IO
for _ in range(3):
    C('100nF', V11)        # VDD-CORE
for _ in range(4):
    C('100nF', V25)        # VCC-DRAM
C('100nF', V33)            # UVCC
C('100nF', V33)            # TV_VCC
C('10uF', V33)
C('10uF', V11)
C('10uF', V25)
C('100nF', V28)            # AVCC
C('4.7uF', V28)
C('100nF', V28)            # HPVCC
C('4.7uF', V28)
C('4.7uF', 'VRA1')
C('4.7uF', 'VRA2')
C('100nF', 'TV_VRP')
R('1k', V25, 'SVREF')      # DDR reference = VCC-DRAM / 2
R('1k', 'SVREF', GND)
C('100nF', 'SVREF')
part('Y1', '24MHz 12pF', 'C70590', 'X322524MOB4SI', 'CRYSTAL-SMD_4P-L3.2-W2.5-BL',
     {1: 'HOSCI', 3: 'HOSCO', 2: GND, 4: GND})
C('18pF', 'HOSCI')
C('18pF', 'HOSCO')
R('10k', V33, 'RESET_N')
C('1uF', 'RESET_N')
part('SW1', 'RESET', 'C318884', 'TS-1187A-B-A-B', 'SW-SMD_4P-L5.1-W5.1-P3.70-LS6.5-TL_H1.5',
     {1: 'RESET_N', 4: GND})

# ================================================================= STORAGE
group('Stockage : microSD + flash SPI')
part('J2', 'microSD', 'C91145', 'TF-01A', 'TF-SMD_TF-01A',
     {1: 'SD_D2', 2: 'SD_D3', 3: 'SD_CMD', 4: V33, 5: 'SD_CLK', 6: GND,
      7: 'SD_D0', 8: 'SD_D1', 10: GND, 11: GND, 12: GND, 13: GND})
for n in ('SD_CMD', 'SD_D0', 'SD_D1', 'SD_D2', 'SD_D3'):
    R('10k', V33, n)
C('100nF', V33)
C('10uF', V33)
part('U4', 'W25Q128JVSIQ 16Mo', 'C97521', 'W25Q128JVSIQTR', 'SOIC-8_L5.3-W5.3-P1.27-LS8.0-BL',
     {1: 'SPI0_CS', 2: 'SPI0_MISO', 3: 'FLASH_IO2', 4: GND, 5: 'SPI0_MOSI',
      6: 'SPI0_CLK', 7: 'FLASH_IO3', 8: V33})
R('10k', V33, 'SPI0_CS')
R('10k', V33, 'FLASH_IO2')
R('10k', V33, 'FLASH_IO3')
C('100nF', V33)

# ================================================================ USB HOST
group('Port USB-A hote')
part('J3', 'USB-A', 'C456018', 'AF90°WJDG', 'USB-A-TH_AF-WJDG',
     {1: 'USBA_VBUS', 2: 'USBA_DM', 3: 'USBA_DP', 4: GND, 5: GND})
part('U5', 'USBLC6-2SC6', 'C2687116', 'USBLC6-2SC6_C2687116',
     'SOT-23-6_L2.9-W1.6-P0.95-LS2.8-BL',
     {1: 'USB_DP', 6: 'USBA_DP', 3: 'USB_DM', 4: 'USBA_DM', 2: GND, 5: 'USBA_VBUS'})
part('F1', 'Fusible rearmable 1A', 'C70082', 'nSMD100-16V', 'F1206', {1: V5, 2: 'USBA_VBUS'})
C('22uF', 'USBA_VBUS')
C('100nF', 'USBA_VBUS')

# ===================================================================== LCD
group('Ecran RGB 40 broches + retroeclairage')
lcd = {1: 'LED_K', 2: 'LED_A', 3: GND, 4: V33, 5: GND, 6: GND, 13: GND, 14: GND,
       21: GND, 22: GND, 29: GND, 30: 'LCD_CLK', 31: 'LCD_DISP', 32: 'LCD_HSYNC',
       33: 'LCD_VSYNC', 34: 'LCD_DE', 36: GND, 37: 'PA0_TPX1', 38: 'PA3_TPY2',
       39: 'PA1_TPX2', 40: 'PA2_TPY1', 41: GND, 42: GND}
for i in range(2, 8):
    lcd[5 + i] = f'LCD_R{i}'     # pins 7..12
    lcd[13 + i] = f'LCD_G{i}'    # pins 15..20
    lcd[21 + i] = f'LCD_B{i}'    # pins 23..28
part('J4', 'FPC 40p 0.5mm (LCD RGB)', 'C5362161', '05A20L40P', 'FPC-SMD_40P-P0.50_05A20L40P', lcd)
R('10k', V33, 'LCD_DISP')
C('100nF', V33)
C('10uF', V33)
part('U7', 'MT9284-28J', 'C181780', 'MT9284-28J', 'SOT-23-6_L2.9-W1.6-P0.95-LS2.8-BR',
     {1: 'BL_SW', 2: GND, 3: 'LED_K', 4: 'LCD_BL_PWM', 5: 'LED_A', 6: V5})
part(_auto('L'), '10uH', 'C45403', 'SWPA3015S100MT', 'IND-SMD_L3.0-W3.0_SWPA3010S',
     {1: V5, 2: 'BL_SW'})
part('D1', 'SS14', 'C2480', 'SS14', 'SMA_L4.2-W2.6-LS5.0-RD_1', {2: 'BL_SW', 1: 'LED_A'})
C('10uF', V5)
C('1uF/50V', 'LED_A')
R('5.1R', 'LED_K', GND)            # 104 mV / 5.1 ohm = 20 mA
R('100k', 'LCD_BL_PWM', GND)

# =================================================================== AUDIO
group('Audio : casque, micro, ampli haut-parleur')
part('J5', 'Jack 3.5mm 4 poles', 'C431535', 'PJ-320D', 'AUDIO-SMD_PJ-320D-1',
     {1: 'HP_L_OUT', 4: 'HP_R_OUT', 3: GND, 2: 'MIC_J'})
part(_auto('C'), '100uF tantale', 'C16133', 'TAJB107K006RNJ', 'CASE-B_3528', {1: 'HPL', 2: 'HP_L_OUT'})
part(_auto('C'), '100uF tantale', 'C16133', 'TAJB107K006RNJ', 'CASE-B_3528', {1: 'HPR', 2: 'HP_R_OUT'})
R('22k', 'HP_L_OUT', GND)          # discharge path, avoids plug-in pop
R('22k', 'HP_R_OUT', GND)
R('2.2k', V28, 'MIC_J')            # electret bias
C('1uF', 'MIC_J', 'MICIN')
part('U9', 'NS4150B', 'C189961', 'NS4150', 'MSOP-8_L3.0-W3.0-P0.65-LS5.0-BL',
     {1: 'PE5_AMP_EN', 2: 'AMP_BYP', 3: 'AMP_INP', 4: 'AMP_INN', 5: 'SPK_N', 6: V5,
      7: GND, 8: 'SPK_P'})
C('1uF', 'AMP_BYP')
C('100nF', 'HPL', 'AMP_L_AC')
C('100nF', 'HPR', 'AMP_R_AC')
R('100k', 'AMP_L_AC', 'AMP_INN')   # gain = 240k / 100k per channel
R('100k', 'AMP_R_AC', 'AMP_INN')
C('100nF', 'AMP_INP_AC')
R('47k', 'AMP_INP_AC', 'AMP_INP')
R('100k', 'PE5_AMP_EN', GND)       # amplifier off by default
C('10uF', V5)
C('100nF', V5)
part('J6', 'Haut-parleur (JST PH 2p)', 'C295747', 'S2B-PH-SM4-TB',
     'CONN-SMD_P2.00_S2B-PH-SM4-TB-LF-SN', {1: 'SPK_P', 2: 'SPK_N', 3: GND, 4: GND})

# ==================================================================== WIFI
group('Wi-Fi / Bluetooth : ESP32-C3')
esp = {3: V33, 8: 'ESP_EN', 5: 'ESP_MISO', 6: 'ESP_HS', 18: 'ESP_DRDY', 20: 'ESP_CLK',
       21: 'ESP_MOSI', 16: 'ESP_CS', 22: 'ESP_IO8', 23: 'ESP_IO9', 12: 'ESP_IO0',
       13: 'ESP_IO1', 19: 'ESP_IO5', 26: 'ESP_IO18', 27: 'ESP_IO19',
       30: 'ESP_RXD', 31: 'ESP_TXD'}
for p in [1, 2, 11, 14] + list(range(36, 54)):
    esp[p] = GND
part('U8', 'ESP32-C3-MINI-1-N4', 'C2838502', 'ESP32-C3-MINI-1-N4', 'WIFIM-SMD_ESP32-C3-MINI-1', esp)
R('10k', V33, 'ESP_EN')
C('1uF', 'ESP_EN')
R('10k', V33, 'ESP_IO8')
R('10k', V33, 'ESP_MISO')          # GPIO2 strapping pin must be high at boot
C('10uF', V33)
C('100nF', V33)

# ============================================================ GPIO / MISC
group('Connecteurs GPIO, I2C, boutons')
hdr = {1: V33, 2: V5, 3: 'I2C_SDA', 4: V5, 5: 'I2C_SCL', 6: GND, 7: 'PE5_AMP_EN',
       8: 'UART0_TX', 9: GND, 10: 'UART0_RX', 11: 'ESP_IO0', 12: 'ESP_IO1',
       13: 'ESP_IO5', 14: GND, 15: 'ESP_IO18', 16: 'ESP_IO19', 17: V33,
       19: 'PA1_TPX2', 20: GND, 21: 'PA3_TPY2', 22: 'LRADC0', 23: 'PA2_TPY1',
       24: 'PA0_TPX1', 25: GND, 28: 'TVOUT', 29: 'RESET_N', 30: GND, 34: GND,
       36: 'ESP_RXD', 37: 'ESP_EN', 38: 'ESP_TXD', 39: GND, 40: 'ESP_IO9'}
part('J8', 'GPIO 2x20 (non monte)', '', 'Conn_02x20_Odd_Even',
     'PinHeader_2x20_P2.54mm_Vertical', hdr, dnp=True,
     lib='Connector_Generic', fplib='Connector_PinHeader_2.54mm')
part('J7', 'I2C Qwiic (JST SH 4p)', 'C160404', 'SM04B-SRSS-TB',
     'CONN-SMD_4P-P1.00_SM04B-SRSS-TB-LF-SN',
     {1: GND, 2: V33, 3: 'I2C_SDA', 4: 'I2C_SCL', 5: GND, 6: GND})
R('4.7k', V33, 'I2C_SDA')
R('4.7k', V33, 'I2C_SCL')
R('100k', V28, 'LRADC0')
part('SW2', 'KEY1', 'C318884', 'TS-1187A-B-A-B', 'SW-SMD_4P-L5.1-W5.1-P3.70-LS6.5-TL_H1.5',
     {1: 'KEY1_R', 4: GND})
part('SW3', 'KEY2', 'C318884', 'TS-1187A-B-A-B', 'SW-SMD_4P-L5.1-W5.1-P3.70-LS6.5-TL_H1.5',
     {1: 'KEY2_R', 4: GND})
R('10k', 'LRADC0', 'KEY1_R')       # 0.25 V
R('22k', 'LRADC0', 'KEY2_R')       # 0.50 V


# ------------------------------------------------------------------ helpers
def nets():
    d = defaultdict(list)
    for p in PARTS.values():
        for pin, net in p['pins'].items():
            d[net].append((p['ref'], pin))
    return d


if __name__ == '__main__':
    n = nets()
    print(len(PARTS), 'parts,', len(n), 'nets')
    single = {k: v for k, v in n.items() if len(v) < 2}
    print('single-pin nets:', single)
    from collections import Counter
    print(Counter(p['lcsc'] for p in PARTS.values()).most_common(8))
