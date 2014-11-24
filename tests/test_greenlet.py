import greenlet
import tests


class WrapGreenletTests(tests.TestCase):
    def test_wrap_greenlet(self):
        def func(value):
            return value * 3

        gl = greenlet.greenlet(func)
        fut = self.loop.wrap_greenthread(gl)
        gl.switch(5)
        result = self.loop.run_until_complete(fut)
        self.assertEqual(result, 15)

    def test_wrap_greenlet_exc(self):
        def func():
            raise ValueError(7)

        gl = greenlet.greenlet(func)
        fut = self.loop.wrap_greenthread(gl)
        gl.switch()
        self.assertRaises(ValueError, self.loop.run_until_complete, fut)

    def test_wrap_greenlet_no_run_attr(self):
        gl = greenlet.greenlet()
        msg = "wrap_greenthread: the run attribute of the greenlet is not set"
        self.assertRaisesRegexp(RuntimeError, msg,
                                self.loop.wrap_greenthread, gl)

    def test_wrap_greenlet_running(self):
        def func(value):
            gl = greenlet.getcurrent()
            return self.loop.wrap_greenthread(gl)

        gl = greenlet.greenlet(func)
        msg = "wrap_greenthread: the greenthread is running"
        self.assertRaisesRegexp(RuntimeError, msg, gl.switch, 5)

    def test_wrap_greenlet_dead(self):
        def func(value):
            return value * 3

        gl = greenlet.greenlet(func)
        gl.switch(5)
        msg = "wrap_greenthread: the greenthread already finished"
        self.assertRaisesRegexp(RuntimeError, msg,
                                self.loop.wrap_greenthread, gl)


if __name__ == '__main__':
    import unittest
    unittest.main()

