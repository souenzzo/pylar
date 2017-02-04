from codecs import decode, encode
import re


def make_re_part(part):
    if part.startswith(":"):
        return "(?P<%s>[^/]+)" % part[1:]
    return part


def make_re_path(path):
    parts = path.split("/")
    re_parts = map(make_re_part, parts)
    return "^%s$" % "/".join(re_parts)


def table_routes(routes):
    method_map = dict()
    for route in routes:
        path = route[0]
        method = route[1]
        *interceptors, handler = route[2]
        re_path = make_re_path(path)
        path_matcher = re.compile(re_path)
        route_map = dict(path=path,
                         method=method,
                         handler=handler,
                         interceptors=interceptors,
                         re_path=re_path,
                         path_matcher=path_matcher)
        method_routes = method_map.get(method, [])
        method_map = {**method_map, method: [*method_routes, route_map]}
    return method_map


def split_path_query(s):
    frag = s.split(b"?", 1)
    path = frag[0]
    query = ""
    if len(frag) == 2:
        query = frag[1]
    return [path, query]


def parse_http(ctx):
    f = ctx["servlet_request"].makefile("rb")
    line = f.readline()
    method, raw_path, version = line.split(b" ")
    path, query = split_path_query(raw_path)
    request = dict(method=decode(method),
                   path=decode(path),
                   query_string=query,
                   version=decode(version),
                   request_body=f)
    return {**ctx, "request": request}


def parse_headers(ctx):
    f = ctx["request"]["request_body"]
    pattern = re.compile(b"^(.+): (.+)\r\n$")
    headers = {}
    while True:
        line = f.readline()
        if line == b"\r\n":
            break
        match = pattern.match(line)
        attr, value = match.groups()
        headers = {**headers, decode(attr): decode(value)}
    length = int(headers.get("Content-Length", 0))
    body = None
    if length > 0:
        body = f.read(length)
    request = ctx["request"]
    request = {**request, "headers": headers, "body": body}
    return {**ctx, "request": request}


def find_route(ctx):
    method = ctx["request"]["method"]
    path = ctx["request"]["path"]
    router = ctx.get("router", dict()).get(method, [])
    path_params = dict()
    match_route = None
    for route in router:
        path_matcher = route["path_matcher"]
        match = path_matcher.match(path)
        if match is None:
            pass
        else:
            match_route = route
            path_params = match.groupdict()
            break
    if match_route is None:
        fn = ctx["not_found_interceptor"]
        return fn(ctx)
    return {**ctx, "request": dict(**ctx["request"], path_params=path_params),
            "route": match_route, "stack": match_route["interceptors"],
            "handler": match_route["handler"]}


def chain_route(ctx):
    stage = ctx.get("stage", "enter")
    if stage == "handler":
        handler = ctx["handler"]
        ## try
        response = handler(ctx["request"])
        ## catch
        return chain_route({**ctx, "response": response, "stage": "leave"})
    elif stage == "enter":
        stack = ctx.get("stack")
        if stack is None:
            return ctx
        lstack = ctx.get("lstack", [])
        if len(stack) > 0:
            inter = stack[0]
            fn = inter.get("enter", lambda x: x)
            ## try
            ctx = fn({**ctx, "stack": stack[1:], "lstack": [inter, *lstack]})
            ## catch
            return chain_route(ctx)
        else:
            return chain_route({**ctx, "stage": "handler"})
    else:
        lstack = ctx.get("lstack", [])
        if len(lstack) > 0:
            inter = lstack[0]
            fn = inter.get("leave", lambda x: x)
            ## try
            ctx = fn({**ctx, "lstack": lstack[1:]})
            ## catch
            return chain_route(ctx)
        else:
            return ctx


def write_headers(ctx):
    headers = ctx["response"].get("headers", {})
    length = len(ctx["response"]["body"])
    status = ctx["response"]["status"]
    headers = {"Content-Length": "%i" % length, **headers}
    bytes = b""
    for k, v in headers.items():
        bytes = b"%s%s: %s\r\n" % (bytes, encode(k), encode(v))
    f = ctx["servlet_request"].makefile("wb")
    f.write(b"HTTP/1.1 %i OK\r\n" % status)
    f.write(bytes)
    f.write(b"\r\n")

    return dict(**ctx, response_body=f)


def write_http(ctx):
    body = ctx["response"]["body"]
    f = ctx["response_body"]
    f.write(body)
    f.flush()
    f.close()
    ctx.pop("response_body")
    return ctx


def parse_query(ctx):
    query = ctx.get("query_string", None)
    if query is None:
        return ctx
    return ctx


def parse_ctx(ctx):
    ctx = parse_http(ctx)
    ctx = parse_headers(ctx)
    ctx = parse_query(ctx)
    ctx = find_route(ctx)
    ctx = chain_route(ctx)
    ctx = write_headers(ctx)
    return write_http(ctx)


def make_handler(server):
    return lambda servlet_request, client_address, servlet: parse_ctx(dict(**server,
                                                                           servlet_request=servlet_request,
                                                                           client_address=client_address,
                                                                           servlet=servlet))
