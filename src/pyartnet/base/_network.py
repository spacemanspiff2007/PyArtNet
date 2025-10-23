from __future__ import annotations

import socket
from asyncio import get_running_loop
from ipaddress import AddressValueError, IPv4Address, IPv6Address
from socket import AF_INET, AF_INET6, AF_UNSPEC, SOCK_DGRAM
from typing import Final, Literal

from typing_extensions import Self


USE_IP_VERSION: Final = Literal['auto', 'v4', 'v6']


def validate_port(port: int, *, allow_0: bool = False) -> int:
    if not isinstance(port, int):
        msg = 'port must be an integer'
        raise TypeError(msg)

    lower = 0 if allow_0 else 1
    if not lower < port < 65536:
        msg = f'port must be between {lower:d} and 65536'
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
                           mode: USE_IP_VERSION = 'auto') -> tuple[tuple[socket.AddressFamily, str], ...]:
    try:
        family = {'auto': AF_UNSPEC, 'v4': AF_INET, 'v6': AF_INET6}[mode]
    except KeyError:
        msg = f'Invalid mode: "{mode:s}"'
        raise ValueError(msg) from None

    try:
        info = await get_running_loop().getaddrinfo(host, port, type=SOCK_DGRAM, family=family)
    except socket.gaierror as e:
        msg = f'Cannot resolve hostname "{host:s}"! {e.errno}: {e.strerror}'
        raise ValueError(msg) from None

    return tuple(
        (v[0], v[4][0]) for v in info if v[0] in (AF_INET, AF_INET6)
    )


async def validate_source_ip(source_ip: str, source_port: int) -> IPv4Address | IPv6Address:
    available = await resolve_hostname(socket.gethostname(), source_port)

    for family, ip in available:
        if ip == source_ip:
            if family == AF_INET:
                return IPv4Address(source_ip)
            return IPv6Address(source_ip)

    available_ips = [k[1] for k in sorted(available)]
    msg = f'Source IP "{source_ip}" is not available on this system! Available: {", ".join(available_ips)}'
    raise ValueError(msg)


async def get_ip(host: str, port: int, ip_version: USE_IP_VERSION) -> IPv4Address | IPv6Address:
    # check if it's a valid ip
    for cls in (IPv4Address, IPv6Address):
        try:
            return cls(host)
        except AddressValueError:  # noqa: PERF203
            pass

    # must be hostname - try to resolve it
    info = await resolve_hostname(host, port, mode=ip_version)
    family, resolved_ip = info[0]

    if family == AF_INET:
        return IPv4Address(resolved_ip)
    return IPv6Address(resolved_ip)


class NetworkInfoBase:
    def __init__(self, *, ip_v6: bool = False) -> None:
        self.ip_v6: Final = ip_v6

    def create_socket(self) -> socket.socket:
        # create nonblocking UDP socket
        sock: Final = socket.socket(AF_INET6 if self.ip_v6 else AF_INET, SOCK_DGRAM)
        sock.setblocking(False)

        return sock

    def validate_ip(self, ip: str) -> str:
        if self.ip_v6:
            IPv6Address(ip)
        else:
            IPv4Address(ip)
        return ip


class UnicastNetworkInfo(NetworkInfoBase):
    def __init__(self, dst: tuple[str, int], src: tuple[str, int] | None = None, *, ip_v6: bool = False) -> None:
        super().__init__(ip_v6=ip_v6)
        self.dst: Final = dst
        self.src: Final = src

    def __repr__(self) -> str:
        ip, port = self.dst
        src = f'{self.src[0]:s}:{self.src[1]:d}' if self.src is not None else 'None'
        return f'{self.__class__.__name__:s}(dst={ip:s}:{port:d}, source={src:s})'

    def create_socket(self) -> socket.socket:
        sock: Final = super().create_socket()

        # option to set source port/ip
        if (src := self.src) is not None:
            # set source port/ip
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.bind(src)

        return sock

    @classmethod
    async def create(cls, hostname: str, port: int, source_ip: str | None = None, source_port: int = 0, *,
                     ip_version: USE_IP_VERSION = 'auto') -> Self:

        validate_string(hostname)
        validate_port(port)

        dst_ip = await get_ip(hostname, port, ip_version)

        source: tuple[str, int] | None = None
        if source_ip is not None:
            validate_string(source_ip)
            validate_port(source_port, allow_0=True)

            await validate_source_ip(source_ip, source_port)
            source = (source_ip, source_port)

            # destination and source IP version must match
            try:
                dst_ip.__class__(source_ip)
            except AddressValueError:
                msg = f'Source IP "{source_ip}" is not a valid IPv{dst_ip.version}!'
                raise ValueError(msg) from None

        return cls(dst=(hostname, port), src=source, ip_v6=dst_ip.version == 6)


class MulticastNetworkInfo(NetworkInfoBase):
    def __init__(self, src: tuple[str, int], *, ip_v6: bool = False) -> None:
        super().__init__(ip_v6=ip_v6)
        self.src: Final = src

    def __repr__(self) -> str:
        return f'{self.__class__.__name__:s}(source={self.src[0]:s} ipv6={self.ip_v6})'

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
    async def create(cls, interface_ip: str, interface_port: int = 0) -> Self:
        validate_string(interface_ip)
        validate_port(interface_port, allow_0=True)

        dst_ip = await validate_source_ip(interface_ip, interface_port)
        return cls(src=(interface_ip, interface_port), ip_v6=dst_ip.version == 6)
