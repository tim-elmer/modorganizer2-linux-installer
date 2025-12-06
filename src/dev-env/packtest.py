from struct import pack
import vdf

from protontricks.steam import APPINFO_V29_STRUCT_SECTION

"""
appinfo looks like:
uint32   - MAGIC: "'DV\x07"
uint32   - UNIVERSE: 1
---- repeated app sections ----
uint32   - AppID
uint32   - size
uint32   - infoState 
uint32   - lastUpdated
uint64   - accessToken
20bytes  - SHA1
uint32   - changeNumber
variable - binary_vdf
---- end of section ---------
uint32   - EOF: 0

<https://github.com/ValvePython/vdf/issues/13#issuecomment-321700244>
"""

APPINFO_V29_MAGIC_UNIVERSE = b')DV\x07\x01\x00'
TWENTY_BYTES = b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'

dummy = vdf.binary_dumps({})

with open('/home/tim/Temp/test/appcache/appinfo.vdf', 'wb') as f:
    f.write(APPINFO_V29_MAGIC_UNIVERSE + pack(
        '<4IL20sI',
        0, 1, 0, 0, 0, TWENTY_BYTES, 0
    ) + dummy)
