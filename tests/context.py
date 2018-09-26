import logging
import logging.handlers
import os
import sys

#module path
path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
assert os.path.isdir(path), 'Folder not found: {:s}'.format(path)
if not path in sys.path:
    sys.path.insert(0, path)

from pyartnet import ArtNetNode, DmxChannel, DmxUniverse, fades

if __name__ == "__main__":
    # create formatter
    _log_format = logging.Formatter("[%(asctime)s] [%(name)25s] %(levelname)8s | %(message)s")

    log = logging.getLogger('')
    log.setLevel(logging.DEBUG)
    log.propagate = True

    logfile = os.path.join(os.path.dirname(__file__), '..', 'log.log')
    if os.path.isfile(logfile):
        os.remove(logfile)

    __logfilehandler = logging.handlers.RotatingFileHandler(filename=logfile,
                                                            maxBytes=10 * 1024 * 1024,
                                                            backupCount=1, encoding='utf-8')
    __logfilehandler.setFormatter(_log_format)
    __logfilehandler.setLevel(logging.DEBUG)

    log = logging.getLogger()
    log.addHandler(__logfilehandler)

    import unittest

    testSuite = unittest.defaultTestLoader.discover(
        start_dir=os.path.abspath(os.path.join(os.path.dirname(__file__))),
        top_level_dir=os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

    text_runner = unittest.TextTestRunner().run(testSuite)