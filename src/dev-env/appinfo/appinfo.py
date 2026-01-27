import sys
from collections import OrderedDict
from struct import pack, calcsize
from typing import Final

from .binaryvdf import BinaryVdf

HEADER: Final[bytes] = bytes(
    # Binary VDF version 29 magic number
    [0x29, 0x44, 0x56, 0x07]
    +
    # Universe
    [0x01, 0x00, 0x00, 0x00]
)


class AppInfo:
    def __init__(self) -> None:
        # Note that apps is intentionally not set by argument, as the BinaryVdf
        #   key logger needs the AppInfo as a reference.
        self.apps: list[BinaryVdf] = []

        # This is a dictionary for performance reasons. The value is the index
        # for the same.
        if sys.version_info >= (3, 7):
            self.keys: dict[str, int] = {}
        else:
            self.keys: OrderedDict[str, int] = OrderedDict()

    def as_bytes(self) -> bytes:
        apps = b"".join([app.as_bytes() for app in self.apps])
        body = (
            HEADER
            +
            # Key table offset
            pack("Q", len(HEADER) + calcsize("Q" + "x" * 4) + len(apps))
            + apps
            +
            # Padding
            pack("x" * 4)
            +
            # Key count
            pack("I", len(self.keys))
        )
        for key in self.keys:
            body += pack(f"{len(key) + 1}s", key.encode("utf-8"))

        return body
