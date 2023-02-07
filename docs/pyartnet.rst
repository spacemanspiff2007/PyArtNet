.. py:currentmodule:: pyartnet

######################################
PyArtNet
######################################
pyartnet is a python implementation of the ArtNet protocol using
`asyncio <https://docs.python.org/3/library/asyncio.html>`_.


Getting Started
==================================

.. exec_code::

    # hide: start
    from helper import MockedSocket
    MockedSocket().mock()
    # hide: stop

    import asyncio
    from pyartnet import ArtNetNode

    async def main():
        # Run this code in your async function
        node = ArtNetNode('IP', 6454)

        # Create universe 0
        universe = node.add_universe(0)

        # Add a channel to the universe which consists of 3 values
        # Default size of a value is 8Bit (0..255) so this would fill
        # the DMX values 1..3 of the universe
        channel = universe.add_channel(start=1, width=3)

        # Fade channel to 255,0,0 in 5s
        # The fade will automatically run in the background
        channel.add_fade([255,0,0], 1000)

        # this can be used to wait till the fade is complete
        await channel

        # hide: start
        node.stop_refresh()
        # hide: stop

    asyncio.run(main())


Channels
==================================


Accessing channels
----------------------------------

Created channels can be requested from the universe through the ``[]`` syntax or through :meth:`BaseUniverse.get_channel`.
If no channel name is specified during creation the default name will be built with ``{START}/{WIDTH}``.

.. exec_code::

    # hide: start
    from helper import MockedSocket
    MockedSocket().mock()

    import asyncio
    from pyartnet import ArtNetNode

    async def main():
    # hide: stop

        # create node/universe
        node = ArtNetNode('IP', 6454)
        universe = node.add_universe(0)

        # create the channel
        channel = universe.add_channel(start=1, width=3)

        # after creation this would also work (default name)
        channel = universe['1/3']
        channel = universe.get_channel('1/3')


        # it's possible to name the channel during creation
        universe.add_channel(start=4, width=3, channel_name='Dimmer1')

        # access is then by name
        channel = universe['Dimmer1']
        channel = universe.get_channel('Dimmer1')

    # hide: start
    asyncio.run(main())
    # hide: stop


Wider channels
----------------------------------
Currently there is support for 8Bit, 16Bit, 24Bit and 32Bit channels.
Channel properties can be set when creating the channel through :meth:`BaseUniverse.add_channel`.

.. exec_code::

    # hide: start
    from helper import MockedSocket
    MockedSocket().mock()

    import asyncio
    from pyartnet import ArtNetNode

    async def main():
    # hide: stop

        # create node/universe
        node = ArtNetNode('IP', 6454)
        universe = node.add_universe(0)

        # create a 16bit channel
        channel = universe.add_channel(start=1, width=3, byte_size=2)

    # hide: start
    asyncio.run(main())
    # hide: stop



Class Reference
==================================


Universe
----------------------------------

.. autoclass:: BaseUniverse
   :members:
   :inherited-members:
   :member-order: groupwise

Channel
----------------------------------

.. autoclass:: Channel
   :members:
   :inherited-members:
   :member-order: groupwise


ArtNetNode
----------------------------------

.. autoclass:: ArtNetNode
   :members:
   :inherited-members:
   :member-order: groupwise

KiNetNode
----------------------------------

.. autoclass:: KiNetNode
   :members:
   :inherited-members:
   :member-order: groupwise

SacnNode
----------------------------------

.. autoclass:: SacnNode
   :members:
   :inherited-members:
   :member-order: groupwise
