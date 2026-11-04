#!/usr/bin/env python3
# Keyboard patches for the X210AI EC firmware V0.4.0 (no external deps)
# Usage: patch_keyboard.py <V0.4.0 dump> <output dir>
import hashlib
import os
import sys

SHA256 = '9b8334bd5d5986ce97dfc5d8503fa643a97d8abb6c6166ce181c0525ec722311'
MATRIX = 0x2EB9  # 8 sense lines x 16 drive lines, index (sense << 4) | drive


def cell(sense, drive):
    return MATRIX + (sense << 4) + drive


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
BUILDS = {
    'EC-V0.4.0-iso-jis.bin': ISO_JIS,
    'EC-V0.4.0-fn-ctrl-swap.bin': FN_CTRL,
    'EC-V0.4.0-iso-jis-fn-ctrl-swap.bin': ISO_JIS + FN_CTRL,
}


def main():
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
        path = os.path.join(outdir, name)
        open(path, 'wb').write(out)
        print(f'{hashlib.sha256(out).hexdigest()}  {name}')


if __name__ == '__main__':
    main()
