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


def greenlet_yield_future(result, loop):
    try:
        value = aiogevent.yield_future(coro_slow_append(result, 1, 0.020))
        result.append(value)

        value = aiogevent.yield_future(coro_slow_append(result, 2, 0.010))
        result.append(value)

        try:
            value = aiogevent.yield_future(coro_slow_error())
        except ValueError as exc:
            result.append(str(exc))

        result.append(4)
        return result
    except Exception as exc:
        result.append(repr(exc))
    finally:
        loop.stop()


def ignore_stderr():
    return tests.mock.patch.object(sys, 'stderr')


class GeventTests(tests.TestCase):
    def test_stop(self):
        def func():
            self.loop.stop()

        gevent.spawn(func)
        self.loop.run_forever()

    def test_soon(self):
        result = []

        def func():
            result.append("spawn")
            self.loop.stop()

        gevent.spawn(func)
        self.loop.run_forever()
        self.assertEqual(result, ["spawn"])

    def test_soon_spawn(self):
        result = []

        def func1():
            result.append("spawn")

        def func2():
            result.append("spawn_later")
            self.loop.stop()

        def schedule_greenlet():
            gevent.spawn(func1)
            gevent.spawn_later(0.010, func2)

        self.loop.call_soon(schedule_greenlet)
        self.loop.run_forever()
        self.assertEqual(result, ["spawn", "spawn_later"])


class LinkFutureTests(tests.TestCase):
    def test_greenlet_yield_future(self):
        result = []
        self.loop.call_soon(gevent.spawn,
                            greenlet_yield_future, result, self.loop)
        self.loop.run_forever()
        self.assertEqual(result, [1, 10, 2, 20, 'error', 4])

    def test_link_coro(self):
        result = []

        def func(fut):
            value = aiogevent.yield_future(coro_slow_append(result, 3))
            result.append(value)
            self.loop.stop()

        fut = asyncio.Future(loop=self.loop)
        gevent.spawn(func, fut)
        self.loop.run_forever()
        self.assertEqual(result, [3, 30])

    def test_yield_future_not_running(self):
        result = []

        def func(event, fut):
            event.set()
            value = aiogevent.yield_future(fut)
            result.append(value)
            self.loop.stop()

        event = gevent.event.Event()
        fut = asyncio.Future(loop=self.loop)
        gevent.spawn(func, event, fut)
        event.wait()

        self.loop.call_soon(fut.set_result, 21)
        self.loop.run_forever()
        self.assertEqual(result, [21])

    def test_yield_future_from_loop(self):
        result = []

        def func(fut):
            try:
                value = aiogevent.yield_future(fut)
            except Exception:
                result.append('error')
            else:
                result.append(value)
            self.loop.stop()

        fut = asyncio.Future(loop=self.loop)
        self.loop.call_soon(func, fut)
        self.loop.call_soon(fut.set_result, 'unused')
        self.loop.run_forever()
        self.assertEqual(result, ['error'])

    def test_yield_future_invalid_type(self):
        def func(obj):
            return aiogevent.yield_future(obj)

        @asyncio.coroutine
        def coro_func():
            print("do something")

        def regular_func():
            return 3

        for obj in (coro_func, regular_func):
            gt = gevent.spawn(func, coro_func)
            # ignore logged traceback
            with ignore_stderr():
                self.assertRaises(TypeError, gt.get)

    def test_yield_future_wrong_loop(self):
        result = []
        loop2 = asyncio.new_event_loop()
        self.addCleanup(loop2.close)

        def func(fut):
            try:
                value = aiogevent.yield_future(fut, loop=loop2)
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


class WrapGreenletTests(tests.TestCase):
    def test_wrap_greenlet(self):
        def func():
            gevent.sleep(0.010)
            return 'ok'

        gt = gevent.spawn(func)
        fut = aiogevent.wrap_greenlet(gt)
        result = self.loop.run_until_complete(fut)
        self.assertEqual(result, 'ok')

    def test_wrap_greenlet_exc(self):
        self.loop.set_debug(True)

        def func():
            raise ValueError(7)

        # FIXME: the unit test must fail!?
        with tests.mock.patch('traceback.print_exception') as print_exception:
            gt = gevent.spawn(func)
            fut = aiogevent.wrap_greenlet(gt)
            self.assertRaises(ValueError, self.loop.run_until_complete, fut)

        # the exception must not be logger by traceback: the caller must
        # consume the exception from the future object
        self.assertFalse(print_exception.called)

    def test_wrap_greenlet_running(self):
        def func():
            return aiogevent.wrap_greenlet(gt)

        self.loop.set_debug(False)
        gt = gevent.spawn(func)
        msg = "wrap_greenlet: the greenlet is running"
        with ignore_stderr():
            self.assertRaisesRegex(RuntimeError, msg, gt.get)

    def test_wrap_greenlet_dead(self):
        def func():
            return 'ok'

        gt = gevent.spawn(func)
        result = gt.get()
        self.assertEqual(result, 'ok')

        msg = "wrap_greenlet: the greenlet already finished"
        self.assertRaisesRegex(RuntimeError, msg,
                               aiogevent.wrap_greenlet, gt)

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

    def test_wrap_greenlet_no_run_attr(self):
        gl = gevent.spawn()
        msg = "wrap_greenlet: the _run attribute of the greenlet is not set"
        self.assertRaisesRegex(RuntimeError, msg,
                               aiogevent.wrap_greenlet, gl)

        # execute the greenlet to consume the error
        with ignore_stderr():
            self.assertRaises(AttributeError, gl.get)


class WrapGreenletRawTests(tests.TestCase):
    def test_wrap_greenlet(self):
        def func():
            gevent.sleep(0.010)
            return "ok"

        gt = gevent.spawn_raw(func)
        fut = aiogevent.wrap_greenlet(gt)
        result = self.loop.run_until_complete(fut)
        self.assertEqual(result, "ok")

    def test_wrap_greenlet_exc(self):
        self.loop.set_debug(True)

        def func():
            raise ValueError(7)

        gt = gevent.spawn_raw(func)
        fut = aiogevent.wrap_greenlet(gt)
        self.assertRaises(ValueError, self.loop.run_until_complete, fut)

    def test_wrap_greenlet_running(self):
        event = gevent.event.Event()
        result = []

        def func():
            try:
                gt = gevent.getcurrent()
                fut = aiogevent.wrap_greenlet(gt)
            except Exception as exc:
                result.append((True, exc))
            else:
                result.append((False, fut))
            event.set()

        gevent.spawn_raw(func)
        event.wait()
        error, value = result[0]
        self.assertTrue(error)
        self.assertIsInstance(value, RuntimeError)
        self.assertEqual(str(value),
                         "wrap_greenlet: the greenlet is running")

    def test_wrap_greenlet_dead(self):
        event = gevent.event.Event()
        def func():
            event.set()

        gt = gevent.spawn_raw(func)
        event.wait()
        msg = "wrap_greenlet: the greenlet already finished"
        self.assertRaisesRegex(RuntimeError, msg,
                               aiogevent.wrap_greenlet, gt)


if __name__ == '__main__':
    import unittest
    unittest.main()
