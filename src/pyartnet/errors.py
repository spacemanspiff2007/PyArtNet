class PyArtNetError(Exception):
    pass


# -----------------------------------------------------------------------------
# Universe Errors
# -----------------------------------------------------------------------------
class InvalidUniverseAddress(PyArtNetError):
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


class ChannelWidthInvalid(PyArtNetError):
    pass


class ChannelValueOutOfBounds(PyArtNetError):
    pass


class ValueCountDoesNotMatchChannelWidthError(PyArtNetError):
    pass
