import tests

class CallbackTests(tests.TestCase):
    def test_hello_world(self):
        result = []

        def hello_world(loop):
            result.append('Hello World')
            loop.stop()

        self.loop.call_soon(hello_world, self.loop)
        self.loop.run_forever()
        self.assertEqual(result, ['Hello World'])

    def test_soon_stop_soon(self):
        result = []

        def hello():
            result.append("Hello")

        def world():
            result.append("World")
            self.loop.stop()

        self.loop.call_soon(hello)
        self.loop.stop()
        self.loop.call_soon(world)

        self.loop.run_forever()
        self.assertEqual(result, ["Hello"])

        self.loop.run_forever()
        self.assertEqual(result, ["Hello", "World"])

    def test_close_soon(self):
        def func():
            pass

        self.loop.close()
        # FIXME: calling call_soon() on a closed event loop should raise an
        # exception:
        # http://bugs.python.org/issue22922
        self.loop.call_soon(func)


if __name__ == '__main__':
    import unittest
    unittest.main()
