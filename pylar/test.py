import pylar.core
from codecs import encode, decode
import io


class Request:
    def __init__(self, inbytes):
        self.input = io.BytesIO(inbytes)
        self.output = io.BytesIO()
        self.output.close = lambda: None

    def makefile(self, x):
        if "rb" == x:
            return self.input
        elif "wb" == x:
            return self.output
        raise ("FAIL")


def response_for(server, method, path, body):
    handler = pylar.core.make_handler(server)
    req = Request(
        b"%s %s HTTP/1.1\r\nHost: localhost\r\nContent-Length: %i\r\n\r\n%s" % (method, path, len(body), body))
    handler(req, None, None)
    return req.output.getvalue()


"""
HTTP/1.1 200 OK
Date: Mon, 01 Dec 2008 00:23:53 GMT
Server: Apache/2.0.61
Access-Control-Allow-Origin: *
Keep-Alive: timeout=2, max=100
Connection: Keep-Alive
Transfer-Encoding: chunked
Content-Type: application/xml
"""


def parse_response_base(res_bytes):
    line, res = res_bytes.split(b"\r\n", 1)
    protocol, code, status = line.split(b" ", 3)
    headers = {}
    while True:
        header_full, res = res.split(b"\r\n", 1)
        if header_full == b"":
            break
        key, val = header_full.split(b": ", 1)
        headers = {**headers, decode(key): decode(val)}
    return {"protocol": decode(protocol),
            "status": decode(status),
            "code": decode(code),
            "body": decode(res),
            "headers": headers}


def response_for2(server, method, path, body):
    handler = pylar.core.make_handler(server)
    req = Request(
        b"%s %s HTTP/1.1\r\nHost: localhost\r\nContent-Length: %i\r\n\r\n%s" % (method, path, len(body), body))
    handler(req, None, None)

    return parse_response_base(req.output.getvalue())
