#!/usr/bin/env python3
"""Build a small dynamically bound ARM64 Mach-O without an Apple SDK."""
import hashlib
from pathlib import Path
import struct
import sys
import mkinit

BASE, PAGE, CODE_OFF = 0x100000000, 0x4000, 0x800
LIBRARIES = ['/System/Library/Frameworks/IOKit.framework/Versions/A/IOKit',
             '/System/Library/Frameworks/IOSurface.framework/IOSurface', '/usr/lib/libSystem.B.dylib']
IMPORTS = [(1, '_IOServiceMatching'), (1, '_IOServiceGetMatchingService'),
           (3, '_mach_task_self_'), (1, '_IOServiceOpen'), (1, '_IOConnectCallScalarMethod'),
           (2, '_IOSurfaceLookupFromMachPort'), (2, '_IOSurfaceLock'),
           (2, '_IOSurfaceGetBaseAddress'), (2, '_IOSurfaceGetWidth'),
           (2, '_IOSurfaceGetHeight'), (2, '_IOSurfaceGetBytesPerRow'), (2, '_IOSurfaceUnlock')]


def uleb(value):
    out = bytearray()
    while value >= 128:
        out.append((value & 127) | 128)
        value >>= 7
    return bytes(out) + bytes([value])


def string_command(cmd, text, dylib=False):
    offset = 24 if dylib else 12
    raw = text.encode() + b'\0'
    size = (offset + len(raw) + 7) & ~7
    header = struct.pack('<6I', cmd, size, offset, 0, 0, 0) if dylib else struct.pack('<3I', cmd, size, offset)
    return (header + raw).ljust(size, b'\0')


def build(code):
    assert 0 < len(code) <= PAGE - CODE_OFF
    binds = bytearray()
    for slot, (ordinal, name) in enumerate(IMPORTS):
        binds += bytes([0x10 | ordinal, 0x40]) + name.encode() + b'\0'
        binds += b'\x51\x72' + uleb(slot * 8) + b'\x90'
    binds += b'\0'
    sym_off = (2 * PAGE + len(binds) + 7) & ~7
    strings, symbols = bytearray(b'\0'), bytearray()
    for ordinal, name in IMPORTS:
        index = len(strings)
        strings += name.encode() + b'\0'
        symbols += struct.pack('<IBBHQ', index, 1, 0, ordinal << 8, 0)
    str_off = sym_off + len(symbols)
    sig_off = (str_off + len(strings) + 15) & ~15
    mkinit.IDENT = b'org.munch.graphics\0'
    sig_size = len(mkinit.code_signature(bytes(sig_off), sig_off, PAGE))
    section = struct.pack('<16s16sQQIIIIIIII', b'__text', b'__TEXT', BASE + CODE_OFF,
                          len(code), CODE_OFF, 2, 0, 0, mkinit.S_ATTR_CODE, 0, 0, 0)
    state = [0] * 33
    state[32] = BASE + CODE_OFF
    thread = struct.pack('<4I', 5, 288, 6, 68) + struct.pack('<33QII', *state, 0, 0)
    commands = [mkinit.segment('__PAGEZERO', 0, BASE, 0, 0, 0),
                mkinit.segment('__TEXT', BASE, PAGE, 0, PAGE, 5, [section]),
                mkinit.segment('__DATA', BASE + PAGE, PAGE, PAGE, PAGE, 3),
                mkinit.segment('__LINKEDIT', BASE + 2 * PAGE, PAGE, 2 * PAGE,
                               sig_off + sig_size - 2 * PAGE, 1),
                thread, string_command(0xe, '/usr/lib/dyld'),
                *[string_command(0xc, name, True) for name in LIBRARIES],
                struct.pack('<6I', 0x32, 24, 2, 0x100000, 0x100000, 0),
                struct.pack('<12I', 0x80000022, 48, 0, 0, 2 * PAGE, len(binds), 0, 0, 0, 0, 0, 0),
                struct.pack('<6I', 2, 24, sym_off, len(IMPORTS), str_off, len(strings)),
                struct.pack('<20I', 0xb, 80, 0, 0, 0, 0, 0, len(IMPORTS), *([0] * 12)),
                struct.pack('<4I', 0x1d, 16, sig_off, sig_size)]
    load = b''.join(commands)
    assert len(load) + 32 <= CODE_OFF
    image = bytearray(sig_off)
    image[:32] = struct.pack('<8I', 0xfeedfacf, 0x100000c, 0, 2, len(commands), len(load), 0x200085, 0)
    image[32:32 + len(load)] = load
    image[CODE_OFF:CODE_OFF + len(code)] = code
    image[2 * PAGE:2 * PAGE + len(binds)] = binds
    image[sym_off:sym_off + len(symbols)] = symbols
    image[str_off:str_off + len(strings)] = strings
    return bytes(image) + mkinit.code_signature(image, sig_off, PAGE)


if __name__ == '__main__':
    result = build(Path(sys.argv[1]).read_bytes())
    Path(sys.argv[2]).write_bytes(result)
    print(f'{sys.argv[2]}: {len(result)} bytes, dyld binds {len(IMPORTS)} imports')
