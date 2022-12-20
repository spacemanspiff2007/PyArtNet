import logging
from typing import Optional, Tuple, Union

from pyartnet.node import BaseNode

# -----------------------------------------------------------------------------
# Documentation for ArtNet Protocol:
# https://artisticlicence.com/support-and-resources/art-net-4/
# -----------------------------------------------------------------------------

log = logging.getLogger('pyartnet.ArtNetNode')


class ArtNetNode(BaseNode):
    def __init__(self, ip: str, port: int, *,
                 max_fps: int = 25,
                 refresh_every: Union[int, float] = 2,
                 sequence_counter=True,
                 source_address: Optional[Tuple[str, int]] = None):
        super().__init__(ip=ip, port=port,
                         max_fps=max_fps,
                         refresh_every=refresh_every,
                         sequence_counter=sequence_counter,
                         source_address=source_address)

        # build base packet
        packet = bytearray()
        packet.extend(map(ord, "Art-Net"))
        packet.append(0x00)          # Null terminate Art-Net
        packet.extend([0x00, 0x50])  # Opcode ArtDMX 0x5000 (Little endian)
        packet.extend([0x00, 0x0e])  # Protocol version 14
        self._packet_base = bytes(packet)

    def _send_universe(self, universe: int, byte_values: int, values: bytearray):
        packet = bytearray()
        packet.append(self._sequence_ctr)  # Sequence,
        packet.append(0x00)  # Physical
        packet.extend(universe.to_bytes(2, byteorder='little'))

        packet.extend(byte_values.to_bytes(2, 'big'))  # Pack the number of channels Big endian
        packet.extend(values)

        self._send_data(packet)

        if log.isEnabledFor(logging.DEBUG):
            self.__log_artnet_frame(self._packet_base + packet)

    def __log_artnet_frame(self, p: Union[bytearray, bytes]):
        """Log Artnet Frame"""
        assert isinstance(p, (bytearray, bytes))

        # runs the first time
        if not hasattr(self, '_log_ctr'):
            self._log_ctr = -1
            self._log_show = [False for k in range(103)]

        self._log_ctr += 1
        if self._log_ctr >= 10:
            self._log_ctr = 0
        show_description: bool = self._log_ctr == 0

        host_fmt = ' ' * (36 + len(self._ip))
        out_desc = '{:s} {:2s} {:2s} {:4s} {:4s}'.format(host_fmt, 'Sq', '', 'Univ', ' Len')

        _max_channel = p[16] << 8 | p[17]
        pre = bytearray(p[:12]).hex().upper()
        out = f'Packet to {self._ip:s}: {pre} {p[12]:02x} {p[13]:02x} {p[13]:02x}{p[14]:02x} {_max_channel:04x}'

        # check what to print
        for k in range(_max_channel):
            if p[18 + k]:
                # once we change something print channel index
                if self._log_show[k // 5] is False:
                    show_description = True
                self._log_show[k // 5] = True

        for k in range(0, _max_channel, 5):

            # if there was never anything active do not print, but print the last block
            if not self._log_show[k // 5] and not k + 5 > _max_channel:
                # do not print multiple shortings
                if out.endswith('...'):
                    continue

                out_desc += '  - '
                out += ' ...'
                continue

            # format block of channels
            _block_vals = []
            _block_desc = []
            for i in range(5):
                if k + i < _max_channel:
                    if show_description:
                        _block_desc.append(f'{k + i + 1:<3d}')
                    _block_vals.append(f'{p[18 + k + i]:03d}')

            # separator
            if out.endswith('...'):
                out_desc += ' '
                out += ' '
            else:
                out_desc += '   '
                out += '   '

            out += ' '.join(_block_vals)
            if show_description:
                out_desc += ' '.join(_block_desc)

        if show_description:
            log.debug(out_desc)
        log.debug(out)
