class PyArtNetError(Exception):
    pass


# -----------------------------------------------------------------------------
# Implementation specific Errors
# -----------------------------------------------------------------------------
class InvalidCidError(PyArtNetError):
    pass


# -----------------------------------------------------------------------------
# Universe Errors
# -----------------------------------------------------------------------------
class InvalidUniverseAddressError(PyArtNetError):
    pass


class DuplicateUniverseError(PyArtNetError):
    pass


class UniverseNotFoundError(PyArtNetError):
    pass


# -----------------------------------------------------------------------------
# Channel Errors
# -----------------------------------------------------------------------------
class ChannelExistsError(PyArtNetError):
    pass


class ChannelNotFoundError(PyArtNetError):
    pass


class OverlappingChannelError(PyArtNetError):
    pass


class ChannelOutOfUniverseError(PyArtNetError):
    pass


class ChannelWidthError(PyArtNetError):
    pass


class ChannelValueOutOfBoundsError(PyArtNetError):
    pass


class ValueCountDoesNotMatchChannelWidthError(PyArtNetError):
    pass
