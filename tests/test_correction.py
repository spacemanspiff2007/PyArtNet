import unittest

from .context import ArtNetNode, DmxChannel, DmxUniverse, output_correction

class TestConfig(unittest.TestCase):

    def __test_correction(self, correction):
        
        self.assertEqual(0, correction(0))
        self.assertEqual(255, correction(255))
        
        for i in range(0, 255, 1):
            res = correction(i)
            self.assertGreaterEqual(res, 0)
            self.assertLessEqual(res, 255)
            
        i = 0
        while i <= 255:
            res = correction(i)
            self.assertGreaterEqual(res, 0)
            self.assertLessEqual(res, 255)
            i += 0.001
    
    def test_quadratic(self):
        self.__test_correction( output_correction.quadratic)

    def test_cubic(self):
        self.__test_correction( output_correction.cubic)

    def test_quadruple(self):
        self.__test_correction( output_correction.quadruple)

