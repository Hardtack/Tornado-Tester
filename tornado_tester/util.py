"""
tornado_tester.util
===================

Utilities

"""

import json
import email

import tornado.httpclient


def encoding(response:  tornado.httpclient.HTTPResponse) -> str:
    """Returns encoding of HTTP response."""
    if 'Content-Encoding' in response.headers:
        return response.headers['Content-Encoding'].decode()
    elif 'Content-Type' in response.headers:
        headers = email.message_from_string('Content-Type: ' +
                                            response.headers['Content-Type'])
        return headers.get_param('charset', 'utf-8')
    else:
        return 'utf-8'


def text_body(response: tornado.httpclient.HTTPResponse) -> str:
    """Get HTTP response body as text."""
    return response.body.decode(encoding(response))


def json_body(response: tornado.httpclient.HTTPResponse):
    """Get HTTP response body as json"""
    return json.loads(text_body(response))
