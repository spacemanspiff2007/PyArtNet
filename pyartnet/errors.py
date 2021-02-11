class ChannelExistsError(Exception):
    pass


class ChannelNotFoundError(Exception):
    pass


class OverlappingChannelError(Exception):
    pass


class ChannelOutOfUniverseError(Exception):
    pass


class ChannelWidthInvalid(Exception):
    pass
