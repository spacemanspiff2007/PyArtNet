import pytest

from pyartnet.base.network import resolve_hostname, validate_ip_address


async def test_hostname() -> None:
    with pytest.raises(ValueError) as e:  # noqa: PT011
        await resolve_hostname('does_not_exist', 0)

    assert str(e.value).startswith('Cannot resolve hostname "does_not_exist"! 11001: getaddrinfo failed')


async def test_get_ip() -> None:
    # ip address v4
    address = '127.0.0.1'
    obj = validate_ip_address(address)
    assert str(obj) == address
    assert obj.version == 4

    # ip address v6
    address = '::1'
    obj = validate_ip_address(address)
    assert str(obj) == address
    assert obj.version == 6

    # hostname gets resolved
    (obj, ) = await resolve_hostname('localhost', 0, mode='v4')
    assert str(obj) == '127.0.0.1'
    assert obj.version == 4

    (obj, ) = await resolve_hostname('localhost', 0, mode='v6')
    assert str(obj) == '::1'
    assert obj.version == 6

    obj = await resolve_hostname('localhost', 0, mode='auto')
    assert str(obj[0]) in ('::1', '127.0.0.1')
