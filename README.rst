Tornado-Tester
==============

Testing tool of tornado web for any testing libraries.

Contextual Tester
-----------------

You can use testing tool by using 'with' statement. ::

    import unittest
    from tornado_tester import gen_test, Tester

    from yourapplication import app

    class Test(unittest.TestCase):
        @gen_test
        def test_app():
            with Tester(app) as tester:
                response = yield tester.http_client(tester.url_for('/hello'))
                ...

By using :meth:`url_for` you can make URL with current HTTP server's address.

And you can use it for py.test like. ::

    import pytest
    from tornado_tester import gen_test, Tester

    from yourapplication import app


    @pytest.fixture
    def tester(request):
        tester = Tester(app)

        tester.setup()
        request.addfinalizer(tester.teardown)
        return tester


    @gen_test
    def test_app(tester):
        response = yield tester.http_client(tester.url_for('/hello'))
        ...

.. warning::
   You can't use multiple Testers in one gen_test by default.

   You should provide a shared I/O loop to use multiple tester. ::

        import pytest
        from tornado.ioloop import IOLoop
        from tornado_tester import gen_test, Tester

        from yourapplication import app


        @gen_test
        def test_app():
            loop = IOLoop()
            tester1 = Tester(app, io_loop=loop)
            tester2 = Tester(app, io_loop=loop)

            with tester1:
                ...

            with tester2:
                ...
