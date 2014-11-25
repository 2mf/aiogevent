import aiogevent
import gevent
import sys
import tests
from tests import asyncio


SHORT_SLEEP = 0.001

def gevent_slow_append(result, value, delay):
    gevent.sleep(delay)
    result.append(value)
    return value * 10

def gevent_slow_error():
    gevent.sleep(SHORT_SLEEP)
    raise ValueError("error")

try:
    import asyncio

    exec('''if 1:
        @asyncio.coroutine
        def coro_wrap_greenlet():
            result = []

            gt = gevent.spawn(gevent_slow_append, result, 1, 0.020)
            value = yield from aiogevent.wrap_greenlet(gt)
            result.append(value)

            gt = gevent.spawn(gevent_slow_append, result, 2, 0.010)
            value = yield from aiogevent.wrap_greenlet(gt)
            result.append(value)

            gt = gevent.spawn(gevent_slow_error)
            try:
                yield from aiogevent.wrap_greenlet(gt)
            except ValueError as exc:
                result.append(str(exc))

            result.append(4)
            return result

        @asyncio.coroutine
        def coro_slow_append(result, value, delay=SHORT_SLEEP):
            yield from asyncio.sleep(delay)
            result.append(value)
            return value * 10

        @asyncio.coroutine
        def coro_slow_error():
            yield from asyncio.sleep(0.001)
            raise ValueError("error")
    ''')
except ImportError:
    import trollius as asyncio
    from trollius import From, Return

    @asyncio.coroutine
    def coro_wrap_greenlet():
        result = []

        gt = gevent.spawn(gevent_slow_append, result, 1, 0.020)
        value = yield From(aiogevent.wrap_greenlet(gt))
        result.append(value)

        gt = gevent.spawn(gevent_slow_append, result, 2, 0.010)
        value = yield From(aiogevent.wrap_greenlet(gt))
        result.append(value)

        gt = gevent.spawn(gevent_slow_error)
        try:
            yield From(aiogevent.wrap_greenlet(gt))
        except ValueError as exc:
            result.append(str(exc))

        result.append(4)
        raise Return(result)

    @asyncio.coroutine
    def coro_slow_append(result, value, delay=SHORT_SLEEP):
        yield From(asyncio.sleep(delay))
        result.append(value)
        raise Return(value * 10)

    @asyncio.coroutine
    def coro_slow_error():
        yield From(asyncio.sleep(0.001))
        raise ValueError("error")


def greenlet_link_future(result, loop):
    try:
        value = aiogevent.link_future(coro_slow_append(result, 1, 0.020))
        result.append(value)

        value = aiogevent.link_future(coro_slow_append(result, 2, 0.010))
        result.append(value)

        try:
            value = aiogevent.link_future(coro_slow_error())
        except ValueError as exc:
            result.append(str(exc))

        result.append(4)
        return result
    except Exception as exc:
        result.append(repr(exc))
    finally:
        loop.stop()


class GeventTests(tests.TestCase):
    def test_hello_world(self):
        result = []

        def hello_world(loop):
            result.append('Hello World')
            loop.stop()

        self.loop.call_soon(hello_world, self.loop)
        self.loop.run_forever()
        self.assertEqual(result, ['Hello World'])


class WrapGreenletTests(tests.TestCase):
    def test_wrap_greenlet(self):
        def func():
            gevent.sleep(0.010)
            return 'ok'

        gt = gevent.spawn(func)
        fut = aiogevent.wrap_greenlet(gt)
        result = self.loop.run_until_complete(fut)
        self.assertEqual(result, 'ok')

    def test_coro_wrap_greenlet(self):
        result = self.loop.run_until_complete(coro_wrap_greenlet())
        self.assertEqual(result, [1, 10, 2, 20, 'error', 4])

    def test_wrap_invalid_type(self):
        def func():
            pass
        self.assertRaises(TypeError, aiogevent.wrap_greenlet, func)

        @asyncio.coroutine
        def coro_func():
            pass
        coro_obj = coro_func()
        self.addCleanup(coro_obj.close)
        self.assertRaises(TypeError, aiogevent.wrap_greenlet, coro_obj)


class LinkFutureTests(tests.TestCase):
    def test_greenlet_link_future(self):
        result = []
        self.loop.call_soon(gevent.spawn,
                            greenlet_link_future, result, self.loop)
        self.loop.run_forever()
        self.assertEqual(result, [1, 10, 2, 20, 'error', 4])

    def test_link_coro(self):
        result = []

        def func(fut):
            value = aiogevent.link_future(coro_slow_append(result, 3))
            result.append(value)
            self.loop.stop()

        fut = asyncio.Future(loop=self.loop)
        gevent.spawn(func, fut)
        self.loop.run_forever()
        self.assertEqual(result, [3, 30])

    def test_link_future_not_running(self):
        result = []

        def func(event, fut):
            event.set()
            value = aiogevent.link_future(fut)
            result.append(value)
            self.loop.stop()

        event = gevent.event.Event()
        fut = asyncio.Future(loop=self.loop)
        gevent.spawn(func, event, fut)
        event.wait()

        self.loop.call_soon(fut.set_result, 21)
        self.loop.run_forever()
        self.assertEqual(result, [21])

    def test_link_future_from_loop(self):
        result = []

        def func(fut):
            try:
                value = aiogevent.link_future(fut)
            except Exception as exc:
                result.append('error')
            else:
                result.append(value)
            self.loop.stop()

        fut = asyncio.Future(loop=self.loop)
        self.loop.call_soon(func, fut)
        self.loop.call_soon(fut.set_result, 'unused')
        self.loop.run_forever()
        self.assertEqual(result, ['error'])

    def test_link_future_invalid_type(self):
        def func(obj):
            return aiogevent.link_future(obj)

        @asyncio.coroutine
        def coro_func():
            print("do something")

        def regular_func():
            return 3

        for obj in (coro_func, regular_func):
            gt = gevent.spawn(func, coro_func)
            # ignore logged traceback
            with tests.mock.patch.object(sys, 'stderr') as stderr:
                self.assertRaises(TypeError, gt.get)

    def test_link_future_wrong_loop(self):
        result = []
        loop2 = asyncio.new_event_loop()
        self.addCleanup(loop2.close)

        def func(fut):
            try:
                value = aiogevent.link_future(fut, loop=loop2)
            except Exception as exc:
                result.append(str(exc))
            else:
                result.append(value)
            self.loop.stop()

        fut = asyncio.Future(loop=self.loop)
        self.loop.call_soon(func, fut)
        self.loop.call_soon(fut.set_result, 'unused')
        self.loop.run_forever()
        self.assertEqual(result[0],
                         'loop argument must agree with Future')


if __name__ == '__main__':
    import unittest
    unittest.main()

