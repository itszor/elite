#!/usr/bin/env python3
"""The program as the ADF has it -> the program as the zip has it.

The "Archie-emulable" ADF (b5052420.zip's ELITE.ADF) holds 1.14 as it was
released: !élite.élite, an AIF image that is encrypted and squeezed, and
without Jeffrey Lee's 2003 patch. This unpacks it by running its own loader
in SuperSpider's arm2.py and applies the patch, giving the image the
recipe's analysis (analysis/elite.roots) and game.c were made from.

The loader: the header's second word branches to a stub at the end of the
image, which decrypts everything below it (an XOR whose key steps by a
constant each word), turns the header's branch into a no-op and jumps to
the next stub down; one stub per layer, then Acorn's unsqueeze, which
copies itself above the image, expands the image in place and jumps to
&8004. Each stub, before jumping, rewrites its own jump instruction
("str r4,[pc,#-4]"), which a real ARM has already fetched - so the old
one runs: the emulation here does the same (an emulator without the
pipeline jumps off the end of the image).

Lee's patch: the pixel plotter's unrolled loop at &2809C-&281CF checks
each point against the 320x256 screen before storing it (cmp r8,#&140;
cmpcc r9,#&100; strbcc) - drawing outside screen memory otherwise.
PATCH below is the 69 words it changes, each with the word it replaces.
The zip's file is a dump of the whole 450K WimpSlot, taken after the
image's zero-initialisation (so the header's zero-init branch is a no-op);
the result here is the same, with zeros past the zero-init area where the
dump has what the program left in its heap.

Usage: unpack.py ADF_ELITE OUT      (OUT: the image, as the zip's !élite.Elite)
"""
import hashlib
import os
import struct
import sys

SS = os.environ.get('SUPERSPIDER', os.path.expanduser('~/stuff/superspider'))
sys.path.insert(0, os.path.join(SS, 'tools'))
from arm2 import ARM, Stop   # noqa: E402

BASE = 0x8000
SLOT = 450 * 1024                               # !Run's WimpSlot: the dump's size
PACKED = '2302fca96f21f2e1593d90c60d56f885d66aaceb6cd4f244591e8c719103da20'
UNPACKED = '0563fa9752ddc3846de9aebe6e7c17025361e71e2b93fc1f701ddc29cdc3be15'  # RO+RW, unpatched
RESULT = '581996c0cc03b78560c8af04928de99baf4c28c425a06cfd69eb41ddb388594a'

# (address, word in 1.14 as released, word in Lee's patch)
PATCH = [
    (0x2809c, 0xe4c61000, 0xe3580d05), (0x280a0, 0xe0866004, 0x33590c01), (0x280a4, 0xe0888004, 0x34c61000),
    (0x280a8, 0xe1570000, 0xe0866004), (0x280ac, 0xca00004c, 0xe0888004), (0x280b0, 0xe2877001, 0xe1570000),
    (0x280b4, 0xe083300a, 0xca00004a), (0x280b8, 0xe1530000, 0xe2877001), (0x280bc, 0xa0433000, 0xe083300a),
    (0x280c0, 0xa0899005, 0xe1530000), (0x280c4, 0xa086600c, 0xa0433000), (0x280c8, 0xe4c61000, 0xa0899005),
    (0x280cc, 0xe0866004, 0xa086600c), (0x280d0, 0xe0888004, 0xe3580d05), (0x280d4, 0xe1570000, 0x33590c01),
    (0x280d8, 0xca000041, 0x34c61000), (0x280dc, 0xe2877001, 0xe0866004), (0x280e0, 0xe083300a, 0xe0888004),
    (0x280e4, 0xe1530000, 0xe1570000), (0x280e8, 0xa0433000, 0xca00003d), (0x280ec, 0xa0899005, 0xe2877001),
    (0x280f0, 0xa086600c, 0xe083300a), (0x280f4, 0xe4c61000, 0xe1530000), (0x280f8, 0xe0866004, 0xa0433000),
    (0x280fc, 0xe0888004, 0xa0899005), (0x28100, 0xe1570000, 0xa086600c), (0x28104, 0xca000036, 0xe3580d05),
    (0x28108, 0xe2877001, 0x33590c01), (0x2810c, 0xe083300a, 0x34c61000), (0x28110, 0xe1530000, 0xe0866004),
    (0x28114, 0xa0433000, 0xe0888004), (0x28118, 0xa0899005, 0xeaffffd7), (0x2811c, 0xa086600c, 0x74696c45),
    (0x28120, 0xe4c61000, 0x61702065), (0x28124, 0xe0866004, 0x20686374), (0x28128, 0xe0888004, 0x4a207962),
    (0x2812c, 0xeaffffd2, 0x293a204c), (0x28150, 0xe4c61000, 0xe3580d05), (0x28154, 0xe086600c, 0x33590c01),
    (0x28158, 0xe0899005, 0x34c61000), (0x2815c, 0xe157000a, 0xe086600c), (0x28160, 0xca00001f, 0xe0899005),
    (0x28164, 0xe2877001, 0xe157000a), (0x28168, 0xe0822000, 0xca00001d), (0x2816c, 0xe152000a, 0xe2877001),
    (0x28170, 0xa042200a, 0xe0822000), (0x28174, 0xa0888004, 0xe152000a), (0x28178, 0xa0866004, 0xa042200a),
    (0x2817c, 0xe4c61000, 0xa0888004), (0x28180, 0xe086600c, 0xa0866004), (0x28184, 0xe0899005, 0xe3580d05),
    (0x28188, 0xe157000a, 0x33590c01), (0x2818c, 0xca000014, 0x34c61000), (0x28190, 0xe2877001, 0xe086600c),
    (0x28194, 0xe0822000, 0xe0899005), (0x28198, 0xe152000a, 0xe157000a), (0x2819c, 0xa042200a, 0xca000010),
    (0x281a0, 0xa0888004, 0xe2877001), (0x281a4, 0xa0866004, 0xe0822000), (0x281a8, 0xe4c61000, 0xe152000a),
    (0x281ac, 0xe086600c, 0xa042200a), (0x281b0, 0xe0899005, 0xa0888004), (0x281b4, 0xe157000a, 0xa0866004),
    (0x281b8, 0xca000009, 0xe3580d05), (0x281bc, 0xe2877001, 0x33590c01), (0x281c0, 0xe0822000, 0x34c61000),
    (0x281c4, 0xe152000a, 0xe086600c), (0x281c8, 0xa042200a, 0xe0899005), (0x281cc, 0xa0888004, 0xeaffffd7),
]


def run_loader(data):
    """the image after its loader: the memory from BASE, once it jumps back to the header"""
    m = ARM()
    end = BASE + len(data)
    m.mem[BASE:end] = data
    m.r[13] = 0x100000
    m.r[15] = BASE

    def swi(m, n, pc):
        raise Stop('SWI &%x at &%x' % (n, pc))
    m.swi_handler = swi
    above = False
    while m.steps < 20_000_000:
        pc = m.r[15]
        if pc >= end:
            above = True
        elif above and pc < BASE + 0x10:        # unsqueezed: back to the AIF header
            return m
        nxt = m.rw(pc + 4)
        m.step()
        if m.r[15] == pc + 4 and m.rw(pc + 4) != nxt:
            # the instruction just stored over was already fetched: it runs as it was
            new = m.rw(pc + 4)
            m.ww(pc + 4, nxt)
            m.step()
            if m.rw(pc + 4) == nxt:
                m.ww(pc + 4, new)
    raise Stop('the loader did not finish')


def unpack(src, dst):
    data = open(src, 'rb').read()
    if hashlib.sha256(data).hexdigest() != PACKED:
        sys.exit('unpack: %s is not the ADF\'s !élite.élite' % src)
    m = run_loader(data)
    img = bytearray(m.mem[BASE:BASE + SLOT])
    ro, rw, _, zi = struct.unpack_from('<IIII', img, 0x14)
    img[ro + rw:] = bytes(SLOT - ro - rw)        # beyond the image: the loader's leftovers
    if hashlib.sha256(img[:ro + rw]).hexdigest() != UNPACKED:
        sys.exit('unpack: the loader did not give 1.14')
    w = struct.unpack_from('<I', img, 8)[0]
    struct.pack_into('<I', img, 8, w | 0xF0000000)       # zero-init done (BLNV)
    for a, old, new in PATCH:
        assert struct.unpack_from('<I', img, a - BASE)[0] == old, '%x' % a
        struct.pack_into('<I', img, a - BASE, new)
    if hashlib.sha256(img).hexdigest() != RESULT:
        sys.exit('unpack: the patched image is not the expected one')
    with open(dst, 'wb') as f:
        f.write(img)


if __name__ == '__main__':
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    unpack(sys.argv[1], sys.argv[2])
