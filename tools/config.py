"""Local paths for the L4D2 binaries being analysed.

The game install is read-only and is never modified.

Two bin directories are involved and they are NOT the same directory:

  <game>/bin/engine.dll              <- engine
  <game>/left4dead2/bin/server.dll   <- game dlls
  <game>/left4dead2/bin/client.dll

Set either the specific overrides, or L4D2_BIN when both live in one place:

  L4D2_ENGINE_BIN=/path/to/Left 4 Dead 2/bin
  L4D2_GAMEDLL_BIN=/path/to/Left 4 Dead 2/left4dead2/bin

Repository-local output roots are defined here too, so every tool agrees on
where artifacts and reports go.
"""
import os

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# fallback used when the split variables are not set
_ONE_BIN = os.environ.get("L4D2_BIN", "")

ENGINE_BIN = os.environ.get("L4D2_ENGINE_BIN") or _ONE_BIN
GAMEDLL_BIN = os.environ.get("L4D2_GAMEDLL_BIN") or _ONE_BIN

# backwards-compatible alias (some scripts still say BIN)
BIN = GAMEDLL_BIN

ENGINE_DLL = os.path.join(ENGINE_BIN, "engine.dll")
SERVER_DLL = os.path.join(GAMEDLL_BIN, "server.dll")
CLIENT_DLL = os.path.join(GAMEDLL_BIN, "client.dll")

OUTDIR = os.path.join(_REPO, "out")
MANIFESTS = os.path.join(_REPO, "manifests")
REPORTS = os.path.join(_REPO, "reports")
DATA = os.path.join(_REPO, "data")

OUT = DATA  # legacy name used by the early scanners


def require(path):
    if not os.path.isfile(path):
        raise SystemExit(
            "missing input: %s\n"
            "set the directory that holds this file:\n"
            "  engine.dll  -> L4D2_ENGINE_BIN  (e.g. .../Left 4 Dead 2/bin)\n"
            "  server.dll / client.dll -> L4D2_GAMEDLL_BIN (e.g. .../left4dead2/bin)\n"
            "or set L4D2_BIN when both DLL kinds are in one directory" % path
        )
    return path
