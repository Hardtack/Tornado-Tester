import io

import pytest
import tornado.ioloop
from tornado.web import Application, RequestHandler, url
from tornado.httpclient import HTTPError

from tornado_tester import Tester, gen_test
from tornado_tester.util import text_body


@gen_test
def test_simpleapp():
    """Test using simple tornado app."""
    class Handler(RequestHandler):
        def get(self):
            self.write('Hello')

    app = Application([url('/hello', Handler)])

    with Tester(app) as tester:
        response = yield tester.http_client.fetch(tester.url_for('/hello'))
        assert 'Hello' == text_body(response)


@gen_test
def test_fileupload():
    """Test file uploading."""
    class Handler(RequestHandler):
        def post(self):
            self.write(self.request.files['file'][0]['body'])

    app = Application([url('/hello', Handler)])

    with Tester(app) as tester:
        with io.BytesIO('Hello'.encode('utf8')) as f:
            response = yield tester.http_client.fetch(
                tester.url_for('/hello'), files={
                    'file': ('hello.txt', f)
                })
            assert 'Hello' == text_body(response)


@gen_test
def test_url_for():
    """Test :meth:`url_for` method of tester."""
    class Handler(RequestHandler):
        def get(self):
            self.write('Hello')

    app = Application([
        url('/hello', Handler, name='hello'),
        url('/hello2', Handler),
        ])
    with Tester(app) as tester:
        assert tester.base_url + '/hello' == tester.url_for('hello')
        assert tester.base_url + '/hello2' == tester.url_for('/hello2')
        assert 'https://www.google.com/api' == tester.url_for(
            'https://www.google.com/api')


@gen_test
def test_general_function():
    """Test :func:`gen_test` to working for non-coroutine function"""
    assert True


@pytest.fixture
def tester(request):
    """Tester fixture."""
    class Handler(RequestHandler):
        def get(self):
            self.write('Hello')

    app = Application([url('/hello', Handler)])

    tester = Tester(app)
    tester.setup()
    request.addfinalizer(tester.teardown)
    return tester


@gen_test
def test_fixture(tester: Tester):
    """Test tester fixture."""
    response = yield tester.http_client.fetch(tester.url_for('/hello'))
    assert 'Hello' == text_body(response)


@gen_test
def test_multiple_yields():
    """Test multiple yields."""
    class Handler(RequestHandler):
        def get(self):
            self.write('Hello')

    app = Application([url('/hello', Handler)])

    with Tester(app) as tester:
        for i in range(10):
            response = yield tester.http_client.fetch(tester.url_for('/hello'))
            assert 'Hello' == text_body(response)


@gen_test
def test_reuse():
    """Tester is not reusable."""
    class Handler(RequestHandler):
        def get(self):
            self.write('Hello')

    app = Application([url('/hello', Handler)])

    tester = Tester(app)
    with tester:
        response = yield tester.http_client.fetch(tester.url_for('/hello'))
        assert 'Hello' == text_body(response)

    with pytest.raises(RuntimeError):
        tester.setup()


@gen_test
def test_another_loop():
    """We can handle only one I/O loop per test."""
    class Handler(RequestHandler):
        def get(self):
            self.write('Hello')

    app = Application([url('/hello', Handler)])

    tester1 = Tester(app)
    with tester1:
        response = yield tester1.http_client.fetch(
            tester1.url_for('/hello'))
        assert 'Hello' == text_body(response)

    tester2 = Tester(app)
    with tester2:
        with pytest.raises(RuntimeError):
            yield tester2.http_client.fetch(
                tester2.url_for('/hello'))


@gen_test
def test_shared_loop():
    """But, we can use same I/O loop in multiple testers."""
    class Handler(RequestHandler):
        def get(self):
            self.write('Hello')

    app = Application([url('/hello', Handler)])

    io_loop = tornado.ioloop.IOLoop()

    tester1 = Tester(app, io_loop=io_loop)
    with tester1:
        response = yield tester1.http_client.fetch(
            tester1.url_for('/hello'))
        assert 'Hello' == text_body(response)

    tester2 = Tester(app, io_loop=io_loop)
    with tester2:
        response = yield tester2.http_client.fetch(
            tester2.url_for('/hello'))
        assert 'Hello' == text_body(response)


@gen_test
def test_exception():
    """Tester should send exceptions into coroutine."""
    class Handler(RequestHandler):
        def get(self):
            self.set_status(400)
            self.write('Fail')

    app = Application([url('/hello', Handler)])

    with Tester(app) as tester:
        for i in range(5):
            try:
                yield tester.http_client.fetch(
                    tester.url_for('/hello'))
            except HTTPError as e:
                assert 400 == e.code
            else:
                assert False
