import gevent
import tests
import threading
try:
    import asyncio
except ImportError:
    import trollius as asyncio

try:
    get_ident = threading.get_ident   # Python 3
except AttributeError:
    get_ident = threading._get_ident   # Python 2

class ThreadTests(tests.TestCase):
    def test_ident(self):
        result = {'ident': None}

        def work():
            result['ident'] = get_ident()

        fut = self.loop.run_in_executor(None, work)
        self.loop.run_until_complete(fut)

        # ensure that work() was executed in a different thread
        work_ident = result['ident']
        self.assertIsNotNone(work_ident)
        self.assertNotEqual(work_ident, get_ident())

    def test_run_twice(self):
        result = []

        def work():
            result.append("run")

        fut = self.loop.run_in_executor(None, work)
        self.loop.run_until_complete(fut)
        self.assertEqual(result, ["run"])

        # ensure that run_in_executor() can be called twice
        fut = self.loop.run_in_executor(None, work)
        self.loop.run_until_complete(fut)
        self.assertEqual(result, ["run", "run"])

    def test_policy(self):
        result = {'loop': 'not set'}   # sentinel, different than None

        def work():
            try:
                result['loop'] = asyncio.get_event_loop()
            except Exception as exc:
                result['loop'] = exc

        # get_event_loop() must return None in a different thread
        fut = self.loop.run_in_executor(None, work)
        self.loop.run_until_complete(fut)
        self.assertIsInstance(result['loop'], RuntimeError)


if __name__ == '__main__':
    import unittest
    unittest.main()
