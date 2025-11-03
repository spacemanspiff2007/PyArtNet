from __future__ import annotations

import socket
from asyncio import get_running_loop
from ipaddress import AddressValueError, IPv4Address, IPv6Address
from socket import AF_INET, AF_INET6, AF_UNSPEC, SOCK_DGRAM
from typing import Final, Literal

from typing_extensions import Self, TypeAlias, override


RESOLVE_TO_IP_TYPE: TypeAlias  = Literal['auto', 'v4', 'v6']


def validate_port(port: int, *, allow_0: bool = False) -> int:
    if not isinstance(port, int):
        msg = 'port must be an integer'
        raise TypeError(msg)

    lower = 0 if allow_0 else 1
    if not lower <= port <= 65535:
        msg = f'port must be between {lower:d} and 65535'
        raise ValueError(msg)

    return port


def validate_string(host: str) -> str:
    if not isinstance(host, str):
        msg = 'hostname must be a string'
        raise TypeError(msg)
    if not host:
        msg = 'hostname cannot be empty'
        raise ValueError(msg)
    return host


async def resolve_hostname(host: str, port: int | None = None,
                           mode: RESOLVE_TO_IP_TYPE = 'auto') -> list[IPv4Address | IPv6Address]:
    try:
        family = {'auto': AF_UNSPEC, 'v4': AF_INET, 'v6': AF_INET6}[mode]
    except KeyError:
        msg = f'Invalid mode: "{mode:s}"'
        raise ValueError(msg) from None

    try:
        addr_info = await get_running_loop().getaddrinfo(host, port, type=SOCK_DGRAM, family=family)
    except socket.gaierror as e:
        msg = f'Cannot resolve hostname "{host:s}"! {e.errno}: {e.strerror}'
        raise ValueError(msg) from None

    ret: list[IPv4Address | IPv6Address] = []
    for family, _, _, _, sockaddr in addr_info:
        if family == AF_INET:
            ret.append(IPv4Address(sockaddr[0]))
        elif family == AF_INET6:
            ret.append(IPv6Address(sockaddr[0]))

    return ret


def validate_ip_address(host: str) -> IPv4Address | IPv6Address:
    validate_string(host)

    try:
        return IPv4Address(host)
    except AddressValueError:
        pass
    return IPv6Address(host)


class NetworkTargetBase:
    def __init__(self, *, ip_v6: bool | None = None) -> None:
        self._ip_v6: bool | None = ip_v6

    def create_socket(self) -> socket.socket:
        # create nonblocking UDP socket
        sock: Final = socket.socket(AF_INET6 if self.ip_v6 else AF_INET, SOCK_DGRAM)
        sock.setblocking(False)

        return sock

    @property
    def ip_v6(self) -> bool:
        if self._ip_v6 is None:
            msg = 'Host not yet resolved!'
            raise RuntimeError(msg)
        return self._ip_v6

    async def resolve_hostname(self) -> None:
        raise NotImplementedError()


class UnicastNetworkTarget(NetworkTargetBase):
    def __init__(self, dst: tuple[str, int], src: tuple[str, int] | None = None, *, ip_v6: bool | None = None) -> None:
        super().__init__(ip_v6=ip_v6)
        self.dst: Final = dst
        self.src: Final = src

    def __repr__(self) -> str:
        ip, port = self.dst
        src = f'{self.src[0]:s}:{self.src[1]:d}' if self.src is not None else 'None'
        return f'{self.__class__.__name__:s}(dst={ip:s}:{port:d}, source={src:s})'

    @override
    def create_socket(self) -> socket.socket:
        sock: Final = super().create_socket()

        # option to set source port/ip
        if (src := self.src) is not None:
            # set source port/ip
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.bind(src)

        return sock

    @classmethod
    def create(cls, host: str, port: int, source_ip: str | None = None, source_port: int = 0) -> Self:
        validate_string(host)
        validate_port(port)

        source: tuple[str, int] | None = None
        if source_ip is not None:
            validate_ip_address(source_ip)
            validate_port(source_port, allow_0=True)
            source = (source_ip, source_port)

        # if host is an IP address, determine IP version now
        ip_v6: bool | None = None
        try:
            dst_ip = validate_ip_address(host)
        except AddressValueError:
            pass
        else:
            if source_ip is not None:
                # destination and source IP version must match
                try:
                    dst_ip.__class__(source_ip)
                except AddressValueError:
                    msg = f'Source IP "{source_ip}" is not a valid IPv{dst_ip.version}!'
                    raise ValueError(msg) from None

            ip_v6 = dst_ip.version == 6

        return cls(dst=(host, port), src=source, ip_v6=ip_v6)

    @override
    async def resolve_hostname(self) -> None:
        if self._ip_v6 is not None:
            return None

        # source ip can be used to set the mode for resolution
        mode: RESOLVE_TO_IP_TYPE = 'auto'
        if self.src is not None:
            mode = 'v6' if validate_ip_address(self.src[0]).version == 6 else 'v4'

        info = await resolve_hostname(self.dst[0], self.dst[1], mode=mode)
        self._ip_v6 = info[0].version == 6
        return None


class MulticastNetworkTarget(NetworkTargetBase):
    def __init__(self, src: tuple[str, int], *, ip_v6: bool | None = None) -> None:
        super().__init__(ip_v6=ip_v6)
        self.src: Final = src

    def __repr__(self) -> str:
        return f'{self.__class__.__name__:s}(source={self.src[0]:s})'

    @override
    def create_socket(self) -> socket.socket:
        sock: Final = super().create_socket()

        # set source port/ip
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(self.src)

        # setup socket for multicast
        sock.setsockopt(
            socket.IPPROTO_IP,
            socket.IPV6_MULTICAST_IF if self.ip_v6 else socket.IP_MULTICAST_IF,
            socket.inet_pton(AF_INET6 if self.ip_v6 else AF_INET, self.src[0])
        )

        return sock

    @classmethod
    def create(cls, source_ip: str, source_port: int = 0) -> Self:
        ip_obj = validate_ip_address(source_ip)
        validate_port(source_port, allow_0=True)
        return cls(src=(source_ip, source_port), ip_v6=ip_obj.version == 6)

    @override
    async def resolve_hostname(self) -> None:
        return None
