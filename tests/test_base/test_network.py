import pytest

from pyartnet.base._network import get_ip, validate_source_ip


async def test_hostname() -> None:
    with pytest.raises(ValueError) as e:  # noqa: PT011
        await validate_source_ip('does_not_exist', 0)

    assert str(e.value).startswith('Source IP "does_not_exist" is not available on this system!')


async def test_get_ip() -> None:
    # ip address v4
    address = '127.0.0.1'
    obj = await get_ip(address, 0, ip_version='v6')
    assert str(obj) == address
    assert obj.version == 4

    # ip address v6
    address = '::1'
    obj = await get_ip(address, 0, ip_version='v4')
    assert str(obj) == address
    assert obj.version == 6

    # hostname gets resolved
    obj = await get_ip('localhost', 0, ip_version='v4')
    assert str(obj) == '127.0.0.1'
    assert obj.version == 4

    obj = await get_ip('localhost', 0, ip_version='v6')
    assert str(obj) == '::1'
    assert obj.version == 6

    obj = await get_ip('localhost', 0, ip_version='auto')
    assert str(obj) in ('::1', '127.0.0.1')
