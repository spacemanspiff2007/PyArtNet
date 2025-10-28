import pytest

from pyartnet.base.network import resolve_hostname, validate_ip_address, validate_port


async def test_hostname() -> None:
    with pytest.raises(ValueError) as e:  # noqa: PT011
        await resolve_hostname('does_not_exist', 0)

    assert str(e.value) in (
        'Cannot resolve hostname "does_not_exist"! 11001: getaddrinfo failed'
        'Cannot resolve hostname "does_not_exist"! -3: Temporary failure in name resolution'
    )


def test_validate_port() -> None:
    with pytest.raises(ValueError) as e:
        validate_port(0)
    assert str(e.value) == 'port must be between 1 and 65535'

    with pytest.raises(ValueError) as e:
        validate_port(65536)
    assert str(e.value) == 'port must be between 1 and 65535'

    validate_port(0, allow_0=True)
    validate_port(65535)


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
    objs = await resolve_hostname('localhost', 0, mode='v4')
    assert str(objs[0]) == '127.0.0.1'
    assert objs[0].version == 4

    objs = await resolve_hostname('localhost', 0, mode='v6')
    assert str(objs[0]) == '::1'
    assert objs[0].version == 6

    objs = await resolve_hostname('localhost', 0, mode='auto')
    assert str(objs[0]) in ('::1', '127.0.0.1')
