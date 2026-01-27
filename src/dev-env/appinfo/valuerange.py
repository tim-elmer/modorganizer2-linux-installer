from typing import TypeVar, Final

T = TypeVar("T")


class _ValueRange:
    """
    Like a C type, but not really.
    """

    def __init__(self, maximum: T, minimum: T | None = None) -> None:
        """
        Initialize a value range
        :param maximum: The largest allowable value
        :param minimum: The smallest allowable value. Defaults to the maximum
            inverted less one.
        """

        if minimum < maximum:
            raise ValueError("Minimum must be less than maximum")

        self.maximum = maximum
        self.minimum = minimum or maximum * -1 - 1

    def __contains__(self, value: T) -> bool:
        return self.maximum >= value >= self.minimum

    def assert_(self, value: T) -> T:
        """
        Assert that the given value is within this range.
        :param value: Value to test
        :return: Value
        :exception ValueError: Value is not within this range
        """
        if value not in self:
            raise ValueError(
                f"Value {value} is out of range; must be >= {self.minimum} <= {self.maximum}"
            )
        return value

    def extend(self, other: "_ValueRange") -> "_ValueRange":
        """
        Gets the cumulative range of two ranges
        :param other:
        :return: A range with the lowest possible minimum and highest possible
        maximum of the given ranges.
        """
        return _ValueRange(
            max(self.maximum, other.maximum), min(self.minimum, other.minimum)
        )


SINT32: Final[_ValueRange] = _ValueRange(2**31 - 1)
SINT64: Final[_ValueRange] = _ValueRange(2**63 - 1)
UINT32: Final[_ValueRange] = _ValueRange(2**32 - 1, 0)
UINT64: Final[_ValueRange] = _ValueRange(2**64 - 1, 0)
