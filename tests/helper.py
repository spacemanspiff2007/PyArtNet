from __future__ import annotations

import socket
from typing import TYPE_CHECKING
from unittest.mock import Mock

from pytest import MonkeyPatch
from typing_extensions import override

import pyartnet.base.network as network_module
from pyartnet.base.network import MulticastNetworkTarget, UnicastNetworkTarget


if TYPE_CHECKING:
    from types import TracebackType



class MockedSocket:
    def __init__(self) -> None:
        self.mp = MonkeyPatch()

    def mock(self):
        m_socket_obj = Mock(['sendto', 'setblocking', 'setsockopt', 'bind', 'close', 'family'], name='socket_obj')
        m_socket_obj.sendto = m_sendto = Mock(name='socket_obj.sendto')
        m_socket_obj.family = socket.AF_INET

        constant_names = [
            name for name in dir(socket)
            if name.startswith(('AF_', 'SOCK_', 'SOL_', 'IPPROTO_', 'IP_', 'SO_',)) or
               name in ('herror', 'gaierror')
        ]

        m = Mock(['socket', 'gethostname', 'inet_pton', *constant_names], name='Mock socket package')
        m.gethostname = socket.gethostname
        m.socket = Mock([], return_value=m_socket_obj, name='Mock socket obj')

        # Copy constants
        for name in constant_names:
            setattr(m, name, getattr(socket, name))

        self.mp.setattr(network_module, 'socket', m)
        return m_sendto

    def undo(self) -> None:
        self.mp.undo()

    def __enter__(self):
        return self.mock()

    def __exit__(self, exc_type: type[BaseException] | None,
                 exc_val: BaseException | None, exc_tb: TracebackType | None) -> None:
        self.undo()


class TestingUnicastNetworkTarget(UnicastNetworkTarget):
    @override
    async def is_ip_v6(self) -> bool:
        return False


class TestingMulticastNetworkTarget(MulticastNetworkTarget):
    @override
    async def is_ip_v6(self) -> bool:
        return False
