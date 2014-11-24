import gevent
import tests


class GeventTests(tests.TestCase):
    def test_hello_world(self):
        result = []

        def hello_world(loop):
            result.append('Hello World')
            loop.stop()

        self.loop.call_soon(hello_world, self.loop)
        self.loop.run_forever()
        self.assertEqual(result, ['Hello World'])

    def test_wrap_greenthread(self):
        def func():
            gevent.sleep(0.010)
            return 'ok'

        gt = gevent.spawn(func)
        fut = self.loop.wrap_greenthread(gt)
        result = self.loop.run_until_complete(fut)
        self.assertEqual(result, 'ok')


if __name__ == '__main__':
    import unittest
    unittest.main()

