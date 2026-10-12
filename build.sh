#!/bin/sh
# Build Archimedes Elite from your own copy of the game:
#     ./build.sh elite.zip      (a zip of the elite/ directory, with RISC OS filetypes)
#     ./build.sh b5052420.zip   (or the "Archie-emulable" ELITE.ADF: 1.14 as released)
# then: cd recomp && ./elite
# The steps are recipe.json's "build", run by SuperSpider's tools/weave.py.
set -e
HERE="$(cd "$(dirname "$0")" && pwd)"
SUPERSPIDER="${SUPERSPIDER:-$HOME/stuff/superspider}"
[ $# -gt 0 ] || { echo "usage: $0 elite.zip | DIRECTORY" >&2; exit 2; }
(cd "$SUPERSPIDER" && dune build)
WEAVE_RECIPES="$HERE" exec python3 -I "$SUPERSPIDER/tools/weave.py" build "$@"
