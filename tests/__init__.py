import aiogevent
import sys
try:
    import asyncio
except ImportError:
    import trollius as asyncio
try:
    # On Python 2.6, unittest2 is needed to get new features like addCleanup()
    import unittest2
    unittest = unittest2
except ImportError:
    import unittest
    unittest2 = None
try:
    from unittest import mock
except ImportError:
    import mock

class TestCase(unittest.TestCase):
    def setUp(self):
        policy = aiogevent.EventLoopPolicy()
        asyncio.set_event_loop_policy(policy)
        self.addCleanup(asyncio.set_event_loop_policy, None)

        self.loop = policy.get_event_loop()
        self.addCleanup(self.loop.close)
        self.addCleanup(asyncio.set_event_loop, None)

    if sys.version_info < (3,) and unittest2 is None:
        def assertRaisesRegex(self, *args):
            return self.assertRaisesRegexp(*args)
