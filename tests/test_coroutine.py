import tests

try:
    import asyncio

    exec('''if 1:
        def hello_world(result, delay):
            result.append("Hello")
            # retrieve the event loop from the policy
            yield from asyncio.sleep(delay)
            result.append('World')
            return "."

        def waiter(result):
            loop = asyncio.get_event_loop()
            fut = asyncio.Future(loop=loop)
            loop.call_soon(fut.set_result, "Future")

            value = yield from fut
            result.append(value)

            value = yield from hello_world(result, 0.001)
            result.append(value)
    ''')
except ImportError:
    import trollius as asyncio
    from trollius import From, Return

    def hello_world(result, delay):
        result.append("Hello")
        # retrieve the event loop from the policy
        yield From(asyncio.sleep(delay))
        result.append('World')
        raise Return(".")

    def waiter(result):
        loop = asyncio.get_event_loop()
        fut = asyncio.Future(loop=loop)
        loop.call_soon(fut.set_result, "Future")

        value = yield From(fut)
        result.append(value)

        value = yield From(hello_world(result, 0.001))
        result.append(value)


class CallbackTests(tests.TestCase):
    def test_hello_world(self):
        result = []
        self.loop.run_until_complete(hello_world(result, 0.001))
        self.assertEqual(result, ['Hello', 'World'])

    def test_waiter(self):
        result = []
        self.loop.run_until_complete(waiter(result))
        self.assertEqual(result, ['Future', 'Hello', 'World', '.'])


if __name__ == '__main__':
    import unittest
    unittest.main()
