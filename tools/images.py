#!/usr/bin/env python3
"""The translated images of Archimedes Elite and the steps that build them.

    images.py assemble  the zip's elite/ (extracted/zip, from SuperSpider's
                        weave.py: recipe.json) -> game/, libroger's appdir:
                        !élite as !Elite, !System, and the commanders in
                        Commanders; filetypes as ,xxx suffixes. Or the ADF
                        (extracted/adf), the same files at its top, its
                        !élite.élite unpacked and patched (tools/unpack.py)
                        as the zip's !élite.Elite
    images.py analyse   SuperSpider (superspider analyse --full) on every image:
                        analysis/<name>.json; analysis/<name>.roots, if there,
                        adds entry points
    images.py roots LOG...
                        merges the gap entries of --trace-gaps runs (libroger's
                        untranslated.log) into analysis/<name>.roots
    images.py gen       superspider gen for every image -> recomp/gen/<name>/,
                        plus recomp/gen/modules.inc (game.c's module list)

Images (game/: the original elite/ with filetypes, see ../README.md):
  elite      !Elite.Elite: the game, an AIF image (C, Shared C Library)
             at &8000.
  s_<name>   the five sound modules Sounds.LoadSounds RMLoads.
Modules are translated at fixed RMA addresses, a 64K slot each from &1840000
(below that, libroger's OS_Module claims).
Not translated: !System.Modules.CLib (the Shared C Library: libroger
provides it, on the host's), !Elite.CLockUtils (joystick to keyboard on
ByteV; there is no joystick).
"""
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TOP = os.path.dirname(HERE)
EXT = os.path.join(TOP, 'game')
ZIP = os.path.join(TOP, 'extracted', 'zip', 'elite')    # weave.py's extraction
ADF = os.path.join(TOP, 'extracted', 'adf')             # or the ADF's
SS = os.environ.get('SUPERSPIDER', os.path.expanduser('~/stuff/superspider'))
SSBIN = os.path.join(SS, '_build/default/bin/main.exe')

ELITE = '!Elite/Elite,ff8'
MODULES = [('s_' + n.lower(), '!Elite/Sounds/%s,ffa' % n)
           for n in ['ELexplode', 'ELsiren', 'ELlaser', 'ELwoosh', 'ELmystic']]
RMA_SLOTS = 0x1840000


def images():
    """(name, path relative to game/, base, is module)"""
    return [('elite', ELITE, 0x8000, False)] + [
        (name, path, RMA_SLOTS + k * 0x10000, True) for k, (name, path) in enumerate(MODULES)]


def assemble():
    """game/ from the zip's elite/ (or the ADF): each file used, its filetype as ,xxx"""
    import shutil
    shutil.rmtree(EXT, ignore_errors=True)
    adf = not os.path.isdir(ZIP)
    for src, dst in [('!\xe9lite', '!Elite'), ('!System/Modules', '!System/Modules'),
                     ('Gisburne', 'Commanders/Gisburne'), ('Jameson', 'Commanders/Jameson')]:
        top = ADF if adf else ZIP
        for part in src.split('/'):                     # the zip's names carry ,load-exec
            top = os.path.join(top, next(f for f in os.listdir(top) if f.split(',')[0] == part))
        files = [(top, dst)] if not os.path.isdir(top) else \
            [(os.path.join(d, f), os.path.join(dst, os.path.relpath(os.path.join(d, f), top)))
             for d, _, fs in os.walk(top) for f in fs]
        for a, b in files:
            b = b.split(',')[0] if os.path.isdir(top) else b
            load = int(a.rsplit(',', 1)[1].split('-')[0], 16)
            assert load >> 20 == 0xFFF, a               # all typed
            out = os.path.join(EXT, '%s,%03x' % (b.split(',')[0], (load >> 8) & 0xFFF))
            os.makedirs(os.path.dirname(out), exist_ok=True)
            shutil.copyfile(a, out)
    if adf:                                             # the program as the zip has it
        packed = os.path.join(EXT, '!Elite', '\xe9lite,ff8')
        run([sys.executable, '-I', os.path.join(HERE, 'unpack.py'), packed, os.path.join(EXT, ELITE)])
        os.remove(packed)


def run(cmd):
    print('+', ' '.join(cmd), flush=True)
    subprocess.run(cmd, check=True)


def analyse():
    subprocess.run(['dune', 'build'], cwd=SS, check=True)
    an = os.path.join(TOP, 'analysis')
    for name, path, base, module in images():
        cmd = [SSBIN, 'analyse', os.path.join(EXT, path), '%x' % base, '--full',
               '-o', os.path.join(an, name + '.json')]
        rf = os.path.join(an, name + '.roots')
        if os.path.exists(rf):
            cmd += ['--roots', rf]
        if module:
            cmd += ['--module']
        run(cmd)


def roots(logs):
    for name, path, base, _ in images():
        run([sys.executable, os.path.join(SS, 'tools/gap_roots.py'), os.path.join(EXT, path), '%x' % base,
             os.path.join(TOP, 'analysis', name + '.roots')] + logs)


def gen():
    rc = os.path.join(TOP, 'recomp')
    for k, (name, path, base, module) in enumerate(images()):
        extra = [] if not module else ['--prefix', 'M%d' % k, '--tabprefix', 'recomp_' + name,
                                       '--covtag', chr(ord('a') + k)]
        run([SSBIN, 'gen', os.path.join(EXT, path), '%x' % base, os.path.join(TOP, 'analysis', name + '.json'),
             '--c', os.path.join(rc, 'gen', name)] + extra)
    with open(os.path.join(rc, 'gen', 'modules.inc'), 'w') as f:
        f.write('/* generated by ../tools/images.py - the modules, for game.c */\n')
        for name, _, _, module in images():
            if module:
                f.write('extern const struct roger_image recomp_%s_image;\n' % name)
        f.write('static const struct roger_module modules[] = {\n')
        for name, path, _, module in images():
            if module:
                f.write('    {"../game/%s", &recomp_%s_image, %d},\n' % (path, name, name.startswith('s_')))
        f.write('    {NULL, NULL, 0}};\n')


if __name__ == '__main__':
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    if sys.argv[1] == 'roots':
        roots(sys.argv[2:])
    else:
        for step in sys.argv[1:]:
            {'assemble': assemble, 'analyse': analyse, 'gen': gen}[step]()
