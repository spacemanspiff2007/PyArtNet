# pyartnet
pyartnet is a python implementation of the ArtNet protocol using asyncio.

# Usage


        node = ArtNetNode('IP')
        node.start()

        universe = node.add_universe(0)
        channel  = universe.add_channel(129,3)

        channel.add_fade([255,0,0], 5000)