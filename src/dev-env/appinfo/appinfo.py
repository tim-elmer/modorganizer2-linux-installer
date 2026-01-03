import sys
from collections import OrderedDict
from ctypes import c_uint32
from struct import pack, calcsize
from typing import Final

from vdf.vdict import VDFDict

from binaryvdf import BinaryVdf

HEADER: Final[bytes] = bytes(
    # Binary VDF version 29 magic number
    [0x29, 0x44, 0x56, 0x07] +
    # Universe
    [0x01, 0x00, 0x00, 0x00]
)


class AppInfo:
    def __init__(self) -> None:
        self.apps: list[BinaryVdf] = []
        # This is a dictionary for performance reasons. The value is the index
        # for the same.
        if sys.version_info >= (3, 7):
            self.keys: dict[str, int] = {}
        else:
            self.keys: OrderedDict[str, int] = OrderedDict()

    def as_bytes(self) -> bytes:
        apps = b''.join([app.as_bytes() for app in self.apps])
        body = (
                HEADER +
                # Key table offset
                pack('Q', len(HEADER) + calcsize('Q' + 'x' * 4) + len(apps)) +
                apps +
                # Padding
                pack('x' * 4) +
                # Key count
                pack('I', len(self.keys))
        )
        for key in self.keys:
            body += pack(f'{len(key) + 1}s', key.encode('utf-8'))

        return body


with open('/home/timelmer/Tmp/steamdev/appcache/appinfo.vdf_g', 'wb') as f:
    appinfo = AppInfo()
    appinfo.apps = [
        # Steamplay Manifests
        BinaryVdf(
            app_id=c_uint32(891390),
            keys=appinfo.keys,
            fields=VDFDict({
                'appinfo': VDFDict({
                    'appid': 891390,
                    'extended': VDFDict({
                        'app_mappings': VDFDict(),
                        'compat_tools': VDFDict()
                    })
                })
            })
        ),

        # Proton Experimental
        # TODO: Protontricks isn't finding this yet, seems to be looking in steam.py#873
        BinaryVdf(
            app_id=c_uint32(275850),
            keys=appinfo.keys,
            fields=VDFDict({
                'appinfo': VDFDict({
                    'appid': 275850,
                    'common': VDFDict({
                        'name': 'proton-experimental'
                    })
                })
            })
        ),

        # Skyrim Special Edition
        BinaryVdf(  # 0x1B0E5A
            app_id=c_uint32(489830),
            keys=appinfo.keys,
            fields=VDFDict({
                'appinfo': VDFDict({
                    'appid': 489830
                })
            })
        )
    ]

    f.write(appinfo.as_bytes())
