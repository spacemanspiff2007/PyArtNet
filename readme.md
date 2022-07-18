# pyartnet
![Tests](https://github.com/spacemanspiff2007/PyArtNet/workflows/Tests/badge.svg)
![PyPI - Python Version](https://img.shields.io/pypi/pyversions/pyartnet)
[![Downloads](https://pepy.tech/badge/pyartnet/month)](https://pepy.tech/project/pyartnet/month)


pyartnet is a python implementation of the ArtNet protocol using [asyncio](https://docs.python.org/3/library/asyncio.html).

# Usage

## Fades

````python
from pyartnet import AnimationNode, ArtNetClient

# Run this code in your async function
client = ArtNetClient('IP')
node = AnimationNode(client)

# Create universe 0
universe = node.add_universe(0)

# Add a channel to the universe which consists of 3 values
# Default size of a value is 8Bit (0..255) so this would fill
# the DMX values 1..3 of the universe
channel = universe.add_channel(start=1, width=3)

# Fade channel to 255,0,0 in 5s
# The fade will automatically run in the background
channel.add_fade([255, 0, 0], 5000)

# this can be used to wait till the fade is complete
await channel.wait_till_fade_complete()
````

## Channel handling
Created channels can be requested from the universe through the dict syntax or through ``universe.get_channel()``.
If no channel name is specified during creation the default name will be ``{START}/{WIDTH}``.

````python
channel = universe['1/3']
channel = universe.get_channel('1/3')
````

## Callbacks
There are two possible callbacks on the channel which make it easy to implement additional logic.
The callback takes the channel as an argument.
This example shows how to automatically fade the channel up and down.

````python
from pyartnet import AnimationNode, ArtNetClient, DmxChannel

client = ArtNetClient('IP')
node = AnimationNode(client)
universe = node.add_universe(0)

channel = universe.add_channel(start=1, width=3)


def cb(ch: DmxChannel):
    ch.add_fade([0, 0, 0] if ch.get_channel_values() == [255, 255, 255] else [255, 255, 255], 1000)


channel.callback_fade_finished = cb
channel.callback_value_changed = my_func2
````


## Output correction
It is possible to use an output correction to create different fade curves.
Output correction can be set on the universe or on the individual channel.

````python
from pyartnet import AnimationNode, ArtNetClient, output_correction

client = ArtNetClient('IP')
node = AnimationNode(client)

universe = node.add_universe(0)
universe.output_correction = output_correction.quadratic  # quadratic will be used for all channels

channel = universe.add_channel(start=1, width=3)
channel.output_correction = output_correction.cubic  # this channel will use cubic
````

The graph shows different output depending on the output correction.

From left to right:
linear (default when nothing is set), quadratic, cubic then quadruple
<img src='https://github.com/spacemanspiff2007/pyartnet/blob/master/curves.svg'>

Quadratic or cubic results in much smoother and more pleasant fades when using LED Strips.

## Wider DMX Channels
The library supports wider dmx channels for advanced control.

````python
from pyartnet import AnimationNode, ArtNetClient, DmxChannel16Bit

client = ArtNetClient('IP')
node = AnimationNode(client)

# Create universe 0
universe = node.add_universe(1)

# Add a channel to the universe which consists of 3 values where each value is 16Bits
# This would fill the DMX values 1..6 of the universe
channel = universe.add_channel(start=1, width=3, channel_type=DmxChannel16Bit)

# Notice the higher maximum value for the fade
channel.add_fade([0xFFFF, 0, 0], 5000)
````

## Alternative DMX Clients

KiNet and sACN DMX clients are also supported.

````python
from pyartnet import AnimationNode, KiNetClient, SacnClient

kinet_client = KiNetClient('IP')
kinet_node = AnimationNode(kinet_client)

sacn_client = SacnClient('IP')
sacn_node = AnimationNode(sacn_client)
````


# Changelog

#### 0.9.0 (2022-07-13)
- Separate animation logic from protocol logic
- Change date format to ISO 8601
- Implement KiNet (thanks @jjhuff)
- Implement e1.31 sACN (thanks @RichUncleCody)
- Thread is started automatically, no need to manually `.start()`


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
