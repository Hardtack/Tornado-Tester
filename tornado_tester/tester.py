"""
tornado_tester.tester
=====================

Testing tool for tornado web.

"""
import socket
import inspect
import functools
import urllib.parse

import tornado.gen
import tornado.web
import tornado.ioloop
import tornado.testing
import tornado.httpclient
import tornado.httpserver
from tornado import netutil

from .httpclient import AsyncHTTPClient

__all__ = ['Tester', 'gen_test']


def _add_query_params(url, params: dict):
    """Add query parameters to given URL."""
    if params:
        query = urllib.parse.urlencode(params)
        split = url.split('#', 1)
        if '?' in split[0]:
            url = split[0] + '&' + query
        else:
            url = split[0] + '?' + query
        if len(split) > 1:
            url += '#' + split[1]
    return url


class Tester(object):
    """Set of utilities for testing tornado application.
    It targets for any unittest frameworks.

    You can apply it to py.test like this ::

        from tornado_tester import gen_test, Tester


        @pytest.fixture
        def tester(app):
            return Tester(app)


        @gen_test
        def test_application(tester):
            with tester:
                response = yield tester.http_client(
                    tester.url_for('name', 'arg'))
                ...

    or you can use setup/teardown concept by ::

        from tornado_tester import gen_test, Tester


        @pytest.fixture
        def tester(request, app):
            tester = Tester(app)
            # Set up
            tester.setup()
            # Teardown
            request.addfinalizer(tester.teardown)

            return tester


        @gen_test
        def test_application(tester):
            response = yield tester.http_client(
                tester.url_for('name', 'arg'))
            ...

    """
    def __init__(self, app: tornado.web.Application, port: int=None,
                 io_loop: tornado.ioloop.IOLoop=None,
                 http_client_class=AsyncHTTPClient):
        #: Tornado web application
        self.app = app

        #: Tornado I/O loop
        self.io_loop = io_loop or tornado.ioloop.IOLoop()

        #: Setup flag
        self._setup = False
        self._used = False

        self.http_client_class = http_client_class

        #: Tornado HTTP Client for tester's I/O loop
        self._http_client = None

        self._last_current = None
        self._http_server = None
        self._sock = None
        self.port = port

    @property
    def sock(self) -> socket.SocketType:
        if not self._setup:
            raise RuntimeError("Tester should be set up before using this "
                               "property.")
        return self._sock

    @property
    def http_server(self) -> tornado.httpserver.HTTPServer:
        """Tornado HTTP server from the application."""
        if not self._setup:
            raise RuntimeError("Tester should be set up before using this "
                               "property.")
        return self._http_server

    @property
    def http_client(self) -> tornado.httpclient.AsyncHTTPClient:
        """Tornado HTTP client for testing."""
        if not self._setup:
            raise RuntimeError("Tester should be set up before using this "
                               "property.")
        return self._http_client

    # Contextual methods
    def __enter__(self):
        self.setup()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.teardown()

    def setup(self):
        """Start using this tester as current tester"""
        if self._setup:
            raise RuntimeError("This tester was already setup.")
        if self._used:
            raise RuntimeError("Tester can not be reused.")
        # Flag
        self._used = True

        # I/O loop
        self._last_current = tornado.ioloop.IOLoop.current()
        self.io_loop.make_current()

        # Create contextual values
        self._http_server = tornado.httpserver.HTTPServer(self.app,
                                                          io_loop=self.io_loop)
        self._http_client = self.http_client_class(
            io_loop=self._http_server.io_loop)
        if self.port is None:
            self._sock, self.port = tornado.testing.bind_unused_port()
        else:
            self._sock = netutil.bind_sockets(self.port)
        self._http_server.add_socket(self._sock)

        self._setup = True

    def teardown(self):
        """Teardown tester."""
        if not self._setup:
            raise RuntimeError("You can not teardown tester not setup yet.")

        self.http_client.close()
        self.http_server.stop()
        self.sock.close()

        self._last_current.make_current()

        self._last_current = None
        self._http_client = None
        self._http_server = None
        self._sock = None

        self._setup = False

    # Methods for testing
    @property
    def base_url(self):
        """Base URL for current http server"""
        if not self._setup:
            raise RuntimeError("Tester should be set up before using this "
                               "property.")
        return 'http://{0}:{1}'.format(*self.sock.getsockname())

    def url_for(self, name_or_url: str, *args, **kwargs):
        """Generate URL for its application. ::

            >>> tester = Tester(app)
            >>> tester.url_for('user', 'foo')
            'http://localhost:8080/user/foo'
            >>> tester.url_for('/foo')
            'http://localhost:8080/user/foo'
            >>> tester.url_for('https://www.google.com')
            'https://www.google.com'
            >>> tester.url_for('user', 'foo', query='baz')
            'http://localhost:8080/user/foo?query=baz'

        """
        if not self._setup:
            raise RuntimeError("Tester should be set up before using this "
                               "method.")
        if name_or_url.startswith(('http://', 'https://')):
            url = name_or_url
        elif name_or_url.startswith('/'):
            url = self.base_url + name_or_url
        else:
            url = self.base_url + self.app.reverse_url(name_or_url, *args)
        return _add_query_params(url, kwargs)


def gen_test(fn):
    """Decorate test case function as tornado coroutine function"""
    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        # We need generator function only
        if not inspect.isgeneratorfunction(fn):
            return fn(*args, **kwargs)

        # Get generator
        generator = fn(*args, **kwargs)
        # Convert to iterator
        iterator = iter(generator)

        # Get next value to call setup in tester.
        first = next(iterator)
        # This I/O loop should never be changed while executing test.
        io_loop = tornado.ioloop.IOLoop.current()

        # Wrap with tornado coroutine
        @tornado.gen.coroutine
        def with_ioloop():
            try:
                value = first
                while True:
                    try:
                        # Yield yielded value from generator to I/O loop
                        receive = (yield value)
                    except Exception as e:
                        # Catch all exceptions, and send to generator.
                        value = generator.throw(e)
                    else:
                        # Send sent value from I/O loop to generator.
                        value = generator.send(receive)
                    # We cannot handle multiple I/O loop.
                    if tornado.ioloop.IOLoop.current() != io_loop:
                        value = generator.throw(RuntimeError(
                            'You cannot use multiple I/O loops '
                            'in one test.'))
            except StopIteration as e:
                # Handle coroutine return
                return e.value
        return io_loop.run_sync(with_ioloop)
    return wrapper
