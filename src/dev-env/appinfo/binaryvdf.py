from collections import OrderedDict
from datetime import datetime
from struct import pack, calcsize
from typing import Final, Any

from .binaryfield import BinaryField
from .valuerange import UINT32, UINT64
from vdf import VDFDict

_HASH_LENGTH: Final[int] = 20


class BinaryVdf:
    _app_id: int
    _app_hash: bytes
    _change_number: int
    _info_state: int
    _last_updated: datetime

    def __init__(
        self,
        app_id: int,
        keys: dict[str, int] | OrderedDict[str, int],
        access_token: int = 0,
        app_hash: bytes | None = None,
        change_number: int = 0,
        fields: VDFDict = None,
        info_state: int = 0,
        last_updated: int | datetime = 0,
    ) -> None:
        """
        Represents a binary VDF to be stored in ``appinfo.vdf``.
        :param app_id: The app's ID.
        :param keys: Mutable list of keys present in VDFs.
        :param access_token: Meaning unknown, likely DRM-related.
        :param app_hash: Believed to be the hash of the application. *20B string*.
        :param change_number: Believed to be an index of the current iteration.
        :param fields: The body of the VDF.
        :param info_state: Meaning unknown.
        :param last_updated: The last time the app was updated.
        """

        self.app_id = app_id
        self.app_hash = app_hash
        self.access_token = access_token
        self.change_number = change_number
        self.info_state = info_state
        self.keys = keys
        self.last_updated = last_updated

        if fields is not None and not isinstance(fields, VDFDict):
            raise ValueError("fields must be a VDFDict or None")
        self.fields = (
            self._unwrap_vdf_dict(fields) if (isinstance(fields, VDFDict)) else []
        )

    @property
    def access_token(self) -> int:
        return self._access_token

    @access_token.setter
    def access_token(self, value: int) -> None:
        self._access_token = UINT64.assert_(value)

    @property
    def app_id(self) -> int:
        return self._app_id

    @app_id.setter
    def app_id(self, value: int) -> None:
        self._app_id = UINT32.assert_(value)

    @property
    def app_hash(self) -> bytes:
        """
        Believed to be the hash of the application.
        :return: 20B.
        """
        return self._app_hash

    @app_hash.setter
    def app_hash(self, value: bytes | None) -> None:
        if value is None:
            self._app_hash = b"\x00" * _HASH_LENGTH
        elif len(value) != _HASH_LENGTH:
            raise ValueError(f"app_hash must be {_HASH_LENGTH} bytes")
        else:
            self._app_hash = value

    @property
    def change_number(self) -> int:
        return self._change_number

    @change_number.setter
    def change_number(self, value: int) -> None:
        self._change_number = UINT32.assert_(value)

    @property
    def hash(self) -> bytes:
        """
        Believed to be the hash of the VDF's fields.

        TODO: Not yet implemented.

        :return: 20B.
        """
        return b"\x00" * _HASH_LENGTH

    @property
    def info_state(self) -> int:
        return self._info_state

    @info_state.setter
    def info_state(self, value: int):
        self._info_state = UINT32.assert_(value)

    @property
    def last_updated(self) -> datetime:
        """
        The time that the app was last updated.

        **WARNING:** The v2 binary VDF format uses a 32-bit timestamp. This is
        likely to change on or before 2038/01/19 as the 32-bit field will
        overflow.

        :return:
        """
        return self._last_updated

    @last_updated.setter
    def last_updated(self, value: int | datetime) -> None:
        self._last_updated = (
            value
            if isinstance(value, datetime)
            else datetime.fromtimestamp(float(value))
        )

    def _unwrap_vdf_dict(self, vdf_dict: VDFDict) -> list[BinaryField]:
        fields: list[BinaryField] = []

        def add_find_key(key: str) -> int:
            """
            Add a key to the list of known keys if not already present.
            :param key: The key to add/find.
            :return: Key index.
            """

            if key in self.keys:
                return self.keys[key]
            else:
                i = len(self.keys)
                self.keys[key] = i
                return i

        def unwrap(key: str, value: Any) -> list[BinaryField]:
            """
            Recursively unwrap value.
            :param key:
            :param value:
            :return:
            """

            _fields: list[BinaryField] = []

            key_index = add_find_key(key)

            if isinstance(value, VDFDict):
                _fields.append(BinaryField(BinaryField.Type.START, key_index=key_index))
                for _k, _v in value.items():
                    _fields += unwrap(_k, _v)
                _fields.append(BinaryField(BinaryField.Type.END))
            else:
                _fields.append(BinaryField(key_index=key_index, value=value))

            return _fields

        for k, v in vdf_dict.items():
            fields += unwrap(k, v)

        return fields

    def as_bytes(self) -> bytes:
        packed_fields = b"".join([f.as_bytes() for f in self.fields])

        header_data = pack(
            "IIQ20sI20s",
            self.info_state,
            int(self.last_updated.timestamp()),
            self.access_token,
            self.app_hash,
            self.change_number,
            self.hash,
        )
        header = pack("II", self.app_id, calcsize("IIQ20sI20s") + len(packed_fields))

        return header + header_data + packed_fields
