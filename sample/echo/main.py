from pylar.core import make_handler, table_routes

from http.server import HTTPServer
import codecs
import json


def hello(req):
    return dict(status=200, body={"Olá": "mundo!"})


def echo(req):
    print(req["path_params"])
    return dict(status=200, body=req["json_params"])


def body_to_json(ctx):
    body = ctx["request"]["body"]
    json_params = None
    if not body is None:
        print("~~~", body)
        json_params = json.loads(body)
    request = {**ctx["request"], "json_params": json_params}
    return {**ctx, "request": request}


def json_to_body(ctx):
    body = ctx["response"]["body"]
    headers = {"Content-Type": "application/json; charset=UTF-8"}
    response = {**ctx["response"],
                "headers": headers,
                "body": codecs.encode(json.dumps(body, ensure_ascii=False))}
    return {**ctx, "response": response}


json_body = dict(enter=body_to_json,
                 leave=json_to_body,
                 name="json_body")

routes = table_routes([
    ["/", "GET", [json_body, hello]],
    ["/coisa/:abc", "POST", [json_body, echo]],
    ["/", "GET", [json_body, echo]],
])


def fn404(ctx):
    return {**ctx, "response": {"body": b"404", "status": 404}}


server = dict(router=routes,
              not_found_interceptor=fn404)

if __name__ == "__main__":
    httpd = HTTPServer(("", 8080), make_handler(server))
    httpd.serve_forever()
