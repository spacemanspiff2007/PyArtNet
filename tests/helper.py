import socket
from unittest.mock import Mock

from pytest import MonkeyPatch  # noqa: PT013

import pyartnet


class MockedSocket:
    def __init__(self):
        self.mp = MonkeyPatch()

    def mock(self):
        m_socket_obj = Mock(['sendto', 'setblocking'], name='socket_obj')
        m_socket_obj.sendto = m_sendto = Mock(name='socket_obj.sendto')

        m = Mock(['socket', 'AF_INET', 'SOCK_DGRAM'], name='Mock socket package')
        m.socket = Mock([], return_value=m_socket_obj, name='Mock socket obj')
        m.AF_INET = socket.AF_INET
        m.SOCK_DGRAM = socket.AF_INET

        self.mp.setattr(pyartnet.base.base_node, 'socket', m)
        return m_sendto

    def undo(self):
        self.mp.undo()

    def __enter__(self):
        return self.mock()

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.undo()
