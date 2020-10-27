# pyartnet
pyartnet is a python implementation of the ArtNet protocol using [asyncio](https://docs.python.org/3/library/asyncio.html).

# Usage

````python
from pyartnet import ArtNetNode

node = ArtNetNode('IP')
await node.start()

universe = node.add_universe(0)
channel  = universe.add_channel(start=1, width=3)

# Fade channel to 255,0,0 in 5s
# The fade will automatically run in the background
channel.add_fade([255,0,0], 5000)   

# this can be used to wait till the fade is complete
await channel.wait_till_fade_complete()
````



# Output correction
It is possible to use an output correction to create different fade curves.
Output correction can be set on the universe or on the individual channel.

````python
from pyartnet import ArtNetNode, output_correction

node = ArtNetNode('IP')

universe = node.add_universe(0)
universe.output_correction = output_correction.quadratic()  # quadratic will be used for all channels

channel  = universe.add_channel(start=1, width=3)
channel.output_correction = output_correction.cubic()       # this channel will use cubic
````

The graph shows different output depending on the output correction.

From left to right:
linear (default when nothing is set), quadratic, cubic then quadruple
<img src='https://github.com/spacemanspiff2007/pyartnet/blob/master/curves.svg'>

Quadratic or cubic results in much smoother and more pleasant fades when using LED Strips.

# Changelog
#### 0.6.0 (27.10.2020)
- ``ArtnetNode.start`` is now an async function
- ``ArtnetNode.step_time_ms`` renamed to ``ArtnetNode.step_time`` (shouldn't be used manually anyway)
- removed support for python 3.6
- added more and better type hints
- switched to pytest
- small fixes
