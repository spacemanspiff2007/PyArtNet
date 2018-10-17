import unittest, asyncio, time

from .context import ArtNetNode, DmxChannel, DmxUniverse, output_correction

class TestConfig(unittest.TestCase):

    def __init__(self, *args, **kwargs):
        super().__init__( *args, **kwargs)

        self.node : ArtNetNode = None
        self.univ : DmxUniverse = None

    def setUp(self):
        loop = asyncio.get_event_loop()
        loop.set_debug(True)

        self.node = ArtNetNode('192.168.0.111')
        self.node.start()
        self.univ = self.node.add_universe(0)

    def tearDown(self):
        asyncio.get_event_loop().create_task( self.node.stop())
        time.sleep(0.2)
        self.node = None
        self.univ = None

    def __run_fades(self):
        async def run_test():
            channel = self.univ.add_channel(129, 3)

            soll = [0, 255, 0]
            channel.add_fade(soll, 1000)
            await channel.wait_till_fade_complete()
            self.assertListEqual(channel.get_channel_values(), soll)
            for i in range(3):
                self.assertEqual(self.univ.data[128 + i], soll[i])

            soll = [255, 0, 255]
            channel.add_fade(soll, 2000)
            await channel.wait_till_fade_complete()
            self.assertListEqual(channel.get_channel_values(), soll)
            for i in range(3):
                self.assertEqual(self.univ.data[128 + i], soll[i])

            soll = [0, 0, 0]
            channel.add_fade(soll, 2000)
            await channel.wait_till_fade_complete()
            self.assertListEqual(channel.get_channel_values(), soll)
            for i in range(3):
                self.assertEqual(self.univ.data[128 + i], soll[i])

        asyncio.get_event_loop().run_until_complete(run_test())

    def test_linear(self):
        self.__run_fades()

    def test_quadratic(self):
        self.univ.output_correction = output_correction.quadratic
        self.__run_fades()

    def test_cubic(self):
        self.univ.output_correction = output_correction.cubic
        self.__run_fades()

    def test_quadrouple(self):
        self.univ.output_correction = output_correction.quadruple
        self.__run_fades()

    def test_wait(self):
        channel = self.univ.add_channel(129, 3)
        async def run_test():
            await asyncio.sleep(10)
        
        asyncio.get_event_loop().run_until_complete(run_test())
