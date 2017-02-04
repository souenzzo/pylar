from pylar import test, core
from codecs import encode, decode


def hello(req):
    return dict(status=200, body=b"Ola mundo!!")


def echo(req):
    return dict(status=200, body=req["body"])


routes = core.table_routes([
    ["/", "GET", [hello]],
    ["/", "POST", [echo]]
])

server = {"router": routes}

assert (test.response_for(server, b"GET", b"/", b"") == b'HTTP/1.1 200 OK\r\nContent-Length: 11\r\n\r\nOla mundo!!')

assert (
    test.response_for(server, b"POST", b"/",
                      b"Ola mundo!") == b'HTTP/1.1 200 OK\r\nContent-Length: 10\r\n\r\nOla mundo!')


def GET(*path):
    path = encode("".join(path))
    return test.response_for2(server, b"GET", path, b"")


def POST(path, body):
    return test.response_for2(server, b"POST", encode(path), encode(body))


assert (GET("/") == {'protocol': 'HTTP/1.1',
                     'status': 'OK',
                     'code': '200',
                     'body': 'Ola mundo!!',
                     'headers': {'Content-Length': '11'}})
assert (POST("/", "Ola mundo!") == {'protocol': 'HTTP/1.1',
                                    'status': 'OK',
                                    'code': '200',
                                    'body': 'Ola mundo!',
                                    'headers': {'Content-Length': '10'}})
