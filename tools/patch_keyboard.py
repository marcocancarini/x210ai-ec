#!/usr/bin/env python3
# Keyboard patches for the X210AI EC firmware V0.4.0 (no external deps)
# Usage: patch_keyboard.py <V0.4.0 dump> <output dir>
#        patch_keyboard.py --check <image> [<image> ...]
import hashlib
import os
import sys

SHA256 = '9b8334bd5d5986ce97dfc5d8503fa643a97d8abb6c6166ce181c0525ec722311'
MATRIX = 0x2EB9  # 8 sense lines x 16 drive lines, index (sense << 4) | drive
KEYCODES = 0x3060  # two bytes for each internal code from 0x80
SIZE = 0x20000
SIGNATURE = 0x40  # 16 bytes, excluded from the CRC
CRC_OFFSET = 0x4A  # big endian, inside the signature


def image_crc(data):
    # CRC-16/CMS over the image without the signature: matches all vendor builds
    crc = 0xFFFF
    for offset, byte in enumerate(data):
        if SIGNATURE <= offset < SIGNATURE + 16:
            continue
        crc ^= byte << 8
        for _ in range(8):
            crc = ((crc << 1) ^ 0x8005 if crc & 0x8000 else crc << 1) & 0xFFFF
    return crc


def check(data):
    errors = []
    stored = (data[CRC_OFFSET] << 8) | data[CRC_OFFSET + 1]
    if len(data) != SIZE:
        errors.append(f'size {len(data)}')
    if data[:3] != bytes([0x02, 0x00, 0x70]):
        errors.append('reset vector')
    if data[SIGNATURE:SIGNATURE + 10] != bytes.fromhex('a5a5a5a5a5a5a4958512'):
        errors.append('signature')
    if data[SIGNATURE + 12:SIGNATURE + 16] != bytes.fromhex('aa005555'):
        errors.append('signature tail')
    if image_crc(data) != stored:
        errors.append(f'CRC {stored:04X}, expected {image_crc(data):04X}')
    return errors


def cell(sense, drive):
    return MATRIX + (sense << 4) + drive


def keycode(code):
    return KEYCODES + (code - 0x80) * 2


# (offset, expected byte, new byte)
ISO_JIS = [
    (cell(5, 1), 0x00, 0x61),  # ISO <>
    (cell(6, 7), 0x00, 0x5D),  # ISO #
    (cell(2, 8), 0x00, 0x6A),  # JIS Yen
    (cell(7, 5), 0x00, 0x51),  # JIS Ro
    (cell(7, 0), 0x00, 0x67),  # JIS Muhenkan
    (cell(5, 6), 0x00, 0x64),  # JIS Henkan
    (cell(7, 6), 0x00, 0x13),  # JIS Katakana/Hiragana
]
FN_CTRL = [
    (cell(0, 15), 0x8C, 0x8E),  # LCtrl key sends the internal Fn code
    (0xC461, 0x8E, 0x8C),       # Fn pin press sends the internal LCtrl code
    (0xC468, 0x8E, 0x8C),       # Fn pin release
]
# Internal codes 0x87 and 0x8F are not used by the matrix, the overlays or the code
EXTRA_KEYS = [
    (keycode(0x87), 0x5E, 0x38),  # E0 38, Linux KEY_BACK
    (keycode(0x8F), 0x20, 0x30),  # E0 30, Linux KEY_FORWARD
    (keycode(0x8F) + 1, 0x05, 0x01),  # type: E0 prefixed key
    (cell(6, 11), 0x00, 0x87),  # Browser Back
    (cell(7, 11), 0x00, 0x8F),  # Browser Forward
    (cell(5, 10), 0x00, 0x08),  # ThinkVantage, set 2 F13, Linux KEY_F13
]
BUILDS = {
    'EC-V0.4.0-iso-jis.bin': ISO_JIS,
    'EC-V0.4.0-fn-ctrl-swap.bin': FN_CTRL,
    'EC-V0.4.0-iso-jis-fn-ctrl-swap.bin': ISO_JIS + FN_CTRL,
    'EC-V0.4.0-all-keys.bin': ISO_JIS + FN_CTRL + EXTRA_KEYS,
}


def main():
    if sys.argv[1] == '--check':
        failed = False
        for path in sys.argv[2:]:
            errors = check(open(path, 'rb').read())
            print(f"{'FAIL ' + ', '.join(errors) if errors else 'ok'}  {path}")
            failed = failed or bool(errors)
        sys.exit(failed)
    src, outdir = sys.argv[1], sys.argv[2]
    data = open(src, 'rb').read()
    if hashlib.sha256(data).hexdigest() != SHA256:
        sys.exit('input is not the V0.4.0 dump')
    for name, patches in BUILDS.items():
        out = bytearray(data)
        for offset, old, new in patches:
            if out[offset] != old:
                sys.exit(f'{name}: 0x{offset:04X} is 0x{out[offset]:02X}, expected 0x{old:02X}')
            out[offset] = new
        crc = image_crc(out)
        out[CRC_OFFSET], out[CRC_OFFSET + 1] = crc >> 8, crc & 0xFF
        errors = check(out)
        if errors:
            sys.exit(f"{name}: {', '.join(errors)}")
        path = os.path.join(outdir, name)
        open(path, 'wb').write(out)
        print(f'{hashlib.sha256(out).hexdigest()}  {name}')


if __name__ == '__main__':
    main()
