from binascii import a2b_hex

from pyartnet import SacnNode


async def test_sacn(patched_socket):
    sacn = SacnNode(
        'ip', 9999999,
        cid=b'\x41\x68\xf5\x2b\x1a\x7b\x2d\xe1\x17\x12\xe9\xee\x38\x3d\x22\x58',
        source_name="default source name")
    universe = sacn.add_universe(1)
    channel = universe.add_channel(1, 10)
    channel.set_values(range(1, 11))

    universe.send_data()

    data = '001000004153432d45312e31370000007078000000044168f52b1a7b2de11712e9ee383d225870620000000264656661756c7420' \
           '736f75726365206e616d650000000000000000000000000000000000000000000000000000000000000000000000000000000000' \
           '0000000064003200000001701502a100000001000b000102030405060708090a'

    m = sacn._socket
    m.sendto.assert_called_once_with(bytearray(a2b_hex(data)), ('ip', 9999999))


    await channel
