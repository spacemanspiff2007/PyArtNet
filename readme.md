# pyartnet
![Tests](https://github.com/spacemanspiff2007/PyArtNet/workflows/Tests/badge.svg)
[![Documentation Status](https://readthedocs.org/projects/pyartnet/badge/?version=latest)](https://pyartnet.readthedocs.io/en/latest/?badge=latest)
![PyPI - Python Version](https://img.shields.io/pypi/pyversions/pyartnet)
[![Downloads](https://static.pepy.tech/badge/pyartnet/month)](https://pepy.tech/project/pyartnet)


PyArtNet is a python implementation of the ArtNet protocol using [asyncio](https://docs.python.org/3/library/asyncio.html).
Supported protocols are ArtNet, sACN and KiNet.

# Docs

Docs and examples can be found [here](https://pyartnet.readthedocs.io/en/latest/pyartnet.html)


# Changelog
#### 2.0 (2025-11-04)
- **Breaking change**:
  Nodes now need to be run through an async context manager, e.g.:
    ```python
    async with ArtNetNode.create('IP') as node:
        ...
    ```
- Added support for transmitting multiple universes in sync
- Added support for transmitting SACN through the broadcast address
- ruff and typing fixes
- used UV

#### 1.0.1 (2023-02-20)
- Fixed an issue where consecutive fades would not start from the correct value
- renamed `channel.add_fade` to `channel.set_fade` (`channel.add_fade` will issue a `DeprecationWarning`)

#### 1.0.0 (2023-02-08)
- Complete rework of library (breaking change)
- Add support for sACN and KiNet

#### 0.8.4 (2022-07-13)
- Added linear fade (closes #14)
- Updated max FPS (closes #17)
- All raised Errors inherit now from PyArtNetError
- Some refactoring and cleanup
- Activated tests for Python 3.10

#### 0.8.3 (2021-07-23)
- No more jumping fades when using output correction with bigger channels
- Reformatted files

#### 0.8.2 (2021-03-14)
- Using nonblocking sockets
- Added option to send frames to a broadcast address

#### 0.8.1 (2021-02-26)
- Fixed an issue with the max value for channels with 16bits and more

#### 0.8.0 (2021-02-11)
- Added support for channels with 16, 24 and 32bits

#### 0.7.0 (2020-10-28)
- renamed logger to ``pyartnet`` to make it consistent with the module name
- callbacks on the channel now get the channel passed in as an argument
- Adding the same channel multiple times or adding overlapping channels raises an exception
- Added ``pyartnet.errors``
- optimized logging of sent frames

#### 0.6.0 (2020-10-27)
- ``ArtnetNode.start`` is now an async function
- ``ArtnetNode.step_time_ms`` renamed to ``ArtnetNode.step_time`` (shouldn't be used manually anyway)
- removed support for python 3.6
- added more and better type hints
- switched to pytest
- small fixes

---

`Art-Net™ Designed by and Copyright Artistic Licence Engineering Ltd`
