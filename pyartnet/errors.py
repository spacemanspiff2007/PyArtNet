class PyArtNetError(Exception):
    pass


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
