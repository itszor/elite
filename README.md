Archimedes Elite (Hybrid Technology, 1991) - static recompilation
================================================================

Warren Burch and Clive Gringras's Archimedes Elite, version 1.14 as
patched by Jeffrey Lee (2003: StrongARM without turning the cache off, and
a fix for drawing outside screen memory) - `elite/`, a copy of the
application directory with its !System and commanders. That is the latest
release: Ian Bell's site has 1.14 too (Richard Goodwin's earlier patch).

A recipe: this repository holds no game data. It rebuilds the game from
your own copy, recognised by content (recipe.json):

    ./build.sh elite.zip       (a zip of elite/ with its RISC OS filetypes, or the directory)
    cd recomp && ./elite

build.sh runs recipe.json's steps with SuperSpider's tools/weave.py
(~/stuff/superspider, or $SUPERSPIDER): it unpacks the zip to extracted/zip
(the filetypes, from the zip's RISC OS extra fields, as ,load-exec
suffixes), then the steps below. Needs python3, OCaml/dune, gcc and SDL3.

    game/               libroger's appdir (tools/images.py assemble): from the
                        zip's elite/, !Elite (the application, renamed from
                        !élite), !System's modules and Commanders (Jameson,
                        Gisburne), filetypes as ,xxx suffixes
    tools/images.py     analyse / gen / roots: the program and the five sound modules
    analysis/           SuperSpider's results; elite.roots: one gap entry
    recomp/             make regen, make, ./elite

The program is C, on the Shared C Library: an AIF image linked with the
library's stubs. libroger provides the library itself (src/clib.c, on the
host's C library), so !System's CLib isn't used; SuperSpider's `clib`
mechanism follows the stubs' start-up. CLockUtils (a joystick turned into
key presses) isn't loaded: there's no joystick. The sound modules
(Sounds.EL*) are loaded by the program itself, the first time it runs
(Elite$Instances).

Running
-------

    cd recomp && make && ./elite [--scale=N] [--fullscreen] [--crt] [--no-sound]
    ./elite --mouse=off                 fly by keyboard (sets and saves the Preferences)
    ./elite --commander=Commanders.Jameson    (or a host file: --commander=path/Name,c87)
    ./elite --help                      every option

The program is a desktop application: a Wimp front end (icon bar icon,
Info, Preferences, Commander, Save, Quit) that starts the full-screen game.
libroger shows no desktop, so game.c stands in for the user:

- the game starts straight away (Select on the icon bar icon);
- going back to the desktop in the game (its DESK bar, or F12) saves the
  commander through the front end's save box, as Commanders.<name> - in
  the save directory (--save=, default savedata/), from where
  --commander=Commanders.<name> loads it - and the game carries on;
  closing the window quits;
- --mouse=on|off, --right-handed=on|off, --tune=on|off and --sensitivity=1-9
  set the Preferences in the front end's dialogue and Save them (Choices,
  in the save directory: they last).

Flying: the shipped Choices has Mouse on, and then the game steers by mouse
only - --mouse=off flies by keyboard (< > roll, S X dive/climb, Space ?
faster/slower, as the manual has them). F1 launches; for the rest see the
manual and the key strip in elite/Docs (or the SelectaBar at the bottom of
the screen). The game uses F10-F12, so libroger's own keys are
Ctrl+F10 (display shader), Ctrl+F11 (fullscreen), Ctrl+F12 (screenshot).
Caps Lock is read as the host keyboard has it (OS_Byte 202).

What the runtime needed (libroger, generally)
---------------------------------------------

The Shared C Library; OS_Byte 122 and 202; *IconSprites, the Wimp's sprite
pool and Wimp_SpriteOp, Wimp_ReadSysInfo; dialogue boxes opened as menus,
option icons toggled by clicks, and a Filer stand-in for the save
protocol; typed saves (,xxx) and HostFS:; circles and ellipses; SetEval
with arithmetic; *ChannelVoice, the sound scheduler (Sound_QSchedule: every
sound effect) and WaveSynth-Beep.

Not checked yet
---------------

The mouse flying (with Mouse on) and Caps Lock's effect on it, interactive
play beyond the first systems, combat, hyperspace in all its forms, the
other Preferences, and whether WaveSynth-Beep sounds like the ROM's.
Floating point instructions in the client would stop the run (no FP
emulator): none seen so far.
