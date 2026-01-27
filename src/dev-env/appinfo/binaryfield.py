from enum import Enum
from struct import pack

from .valuerange import SINT32, SINT64, UINT32, UINT64


class BinaryField:
    class Type(bytes, Enum):
        """
        Represents the specific type of the field.

        Host is assumed to be little-endian.
        """

        START = b"\x00"
        STRING = b"\x01"
        SINT32 = b"\x02"
        FLOAT = b"\x03"
        POINTER = b"\x04"
        WIDE_STRING = b"\x05"
        COLOR = b"\x06"  # Not implemented.
        UINT64 = b"\x07"
        END = b"\x08"
        SINT64 = b"\x0a"

        @classmethod
        def pack(cls, type_: "BinaryField.Type", value) -> bytes:
            """
            Pack a field based on its type.
            :param type_:
            :param value:
            :return: Byte-wise representation of the field.
            """

            if type_ in [BinaryField.Type.STRING, BinaryField.Type.WIDE_STRING]:
                try:
                    return (
                        bytes(
                            value,
                            encoding=(
                                "utf-8"
                                if type_ == BinaryField.Type.STRING
                                else (
                                    "utf-16"
                                    if type_ == BinaryField.Type.WIDE_STRING
                                    else None
                                )
                            ),
                        )
                        + b"\x00"
                    )
                except TypeError:
                    raise ValueError("Value must be coercible to string.")

            elif type_ in [
                BinaryField.Type.POINTER,
                BinaryField.Type.SINT32,
                BinaryField.Type.SINT64,
                BinaryField.Type.UINT64,
            ]:
                try:
                    return pack(
                        (
                            "P"
                            if type_ == BinaryField.Type.POINTER
                            else (
                                "i"
                                if type_ == BinaryField.Type.SINT32
                                else (
                                    "q"
                                    if type_ == BinaryField.Type.SINT64
                                    else (
                                        "Q"
                                        if type_ == BinaryField.Type.UINT64
                                        else None
                                    )
                                )
                            )
                        ),
                        int(value),
                    )
                except ValueError:
                    raise ValueError("Value must be coercible to integer.")

            elif type_ == BinaryField.Type.FLOAT:
                try:
                    return pack("f", float(value))
                except ValueError:
                    raise ValueError("Value must be coercible to float.")

            elif type_ == BinaryField.Type.COLOR:
                raise NotImplementedError("Field type not implemented.")

            elif type_ in [BinaryField.Type.START, BinaryField.Type.END]:
                raise ValueError("Start and end field may not be packed.")

            else:
                raise ValueError("Invalid field type")

    def __init__(
        self,
        type_: "BinaryField.Type | None" = None,
        key_index: int | None = None,
        value=None,
    ) -> None:
        """
        Represents a field in a binary VDF.

        Note the following special cases for ``type_``:

        ``START``: ``value`` must be ``None``.

        ``END``: ``key_index`` and ``value`` must be ``None``.

        :param type_: The type of the field. If a type is not provided, an
        attempt will be made to deduce the best fitting type. Signed integers
        are preferred, and 32-bit integers are preferred. Pointers, wide
        strings, and colors will NOT be selected.
        :param key_index: The index of the field's key.
        :param value: The value of the field.
        """

        if type_ is None:
            if value is None:
                raise ValueError("Value must be provided to infer type.")

            elif isinstance(value, str):
                self.type = BinaryField.Type.STRING

            elif isinstance(value, int):
                if value not in SINT64.extend(UINT64):
                    raise ValueError("Unable to deduce type.")

                if value in SINT32:
                    self.type = BinaryField.Type.SINT32
                if value in SINT64:
                    self.type = BinaryField.Type.SINT64
                else:
                    self.type = BinaryField.Type.UINT64

            elif isinstance(value, float):
                self.type = BinaryField.Type.FLOAT
            else:
                raise ValueError(f"Unable to deduce type for {type(value)}.")

        else:
            if type_ not in BinaryField.Type:
                raise ValueError("Invalid field type")
            self.type = type_

        if type_ == BinaryField.Type.START and value is not None:
            raise ValueError("value must be None for start field.")

        if type_ == BinaryField.Type.END and (
            key_index is not None or value is not None
        ):
            raise ValueError("key_index and value may not be set for end field.")
        self.key_index = key_index
        self.value = value

    def as_bytes(self) -> bytes:
        """
        Get a byte representation of the field.
        :return:
        """

        package = bytes(self.type)

        if self.type == BinaryField.Type.END:
            return package

        package += pack("i", self.key_index)

        if self.type == BinaryField.Type.START:
            return package

        package += BinaryField.Type.pack(self.type, self.value)
        return package

    def __str__(self) -> str:
        return f"{self.type.name} Key: {self.key_index} Value: {self.value}"
