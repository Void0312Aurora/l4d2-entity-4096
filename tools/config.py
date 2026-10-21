"""Local paths for the L4D2 binaries being analysed.

The game install is read-only and is never modified. Override with
  L4D2_BIN=/path/to/left4dead2/bin
"""
import os

BIN = os.environ.get(
    "L4D2_BIN",
    "/run/media/void0312/566EBEB06EBE87EF/SteamLibrary/steamapps/common/"
    "Left 4 Dead 2/left4dead2/bin",
)

SERVER_DLL = os.path.join(BIN, "server.dll")
CLIENT_DLL = os.path.join(BIN, "client.dll")
ENGINE_DLL = os.path.join(BIN, "engine.dll")


def require(path):
    if not os.path.isfile(path):
        raise SystemExit(
            "missing input: %s\n"
            "set L4D2_BIN to the directory that holds server.dll/client.dll" % path
        )
    return path
