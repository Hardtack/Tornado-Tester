"""
tornado_tester.httpclient
=========================

Rich HTTP client.

"""
import random
import string
import urllib.parse

import tornado.httpclient
import tornado.simple_httpclient


_BOUNDARY_CHARS = string.ascii_letters + string.digits + '-_'


def random_boundary():
    return utf8('---' + ''.join(random.choice(_BOUNDARY_CHARS) for i in
                                range(random.randint(20, 50))) + '---')


def utf8(s):
    if isinstance(s, str):
        return s.encode('utf-8')
    elif isinstance(s, bytes):
        return s
    else:
        return utf8(str(s))


def encode_multipart(form, files, boundary: bytes):
    lines = []

    if callable(getattr(form, 'items', None)):
        form = form.items()
    if callable(getattr(files, 'items', None)):
        files = files.items()

    for key, value in form:
        lines.append(b'--' + boundary)
        lines.append(b'Content-Disposition: form-data; '
                     b'name="' + utf8(key) + b'"')
        lines.append('')
        lines.append(value)
    for key, (filename, fileobj) in files:
        lines.append(b'--' + boundary)
        lines.append(
            b'Content-Disposition: form-data; name="' + utf8(key) + b'"; ' +
            b'filename="' + utf8(filename) + b'"'
        )
        lines.append('')
        lines.append(fileobj.read())
    lines.append(b'--' + boundary + b'--')
    lines.append('')
    return b'\r\n'.join(map(utf8, lines))


class AsyncHTTPClient(tornado.simple_httpclient.SimpleAsyncHTTPClient):
    def fetch(self, request, callback=None, raise_error=True, **kwargs):
        form = kwargs.pop('form', None)
        files = kwargs.pop('files', None)

        if form and not files:
            headers = kwargs.pop('headers', {})
            kwargs.setdefault('method', 'POST')
            body = urllib.parse.urlencode(form)
            headers['Content-Type'] = 'application/x-www-form-urlencoded'
            headers['Content-Length'] = str(len(body))
            kwargs['body'] = body
            kwargs['headers'] = headers
        elif files:
            headers = kwargs.pop('headers', {})
            kwargs.setdefault('method', 'POST')
            form = form or {}
            # Multipart form data
            boundary = random_boundary()
            body = encode_multipart(form, files, boundary)
            content_type = b'multipart/form-data; boundary=' + boundary

            headers['Content-Type'] = content_type
            headers['Content-Length'] = str(len(body))

            kwargs['body'] = body
            kwargs['headers'] = headers

        return super().fetch(request,
                             callback=callback,
                             raise_error=raise_error,
                             **kwargs)
