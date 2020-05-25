# pyartnet
pyartnet is a python implementation of the ArtNet protocol using [asyncio](https://docs.python.org/3/library/asyncio.html).

# Usage


        node = ArtNetNode('IP')
        node.start()

        universe = node.add_universe(0)
        channel  = universe.add_channel(start=1, width=3)

        channel.add_fade([255,0,0], 5000)
        await channel.wait_till_fade_complete()
