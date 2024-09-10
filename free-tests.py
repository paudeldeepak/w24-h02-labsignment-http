from http.client import HTTPResponse
import sys
from typing import Any
from multiprocessing import Process
import pathlib
import re
import traceback
import random
import difflib
from urllib import request
from urllib.parse import urljoin
import http
from inspect import cleandoc
import os

class NoErrorHTTPErrorProcessor(request.HTTPErrorProcessor):
    def http_response(self, request, response):
        return response
class NoRedirectHTTPRedirectHandler(request.HTTPRedirectHandler):
    def http_response(self, request, response):
        return response
request.install_opener(request.build_opener(
    NoErrorHTTPErrorProcessor,
    NoRedirectHTTPRedirectHandler
))

NAME = pathlib.Path(__file__).name

class TestEntry:
    def __init__(self, tester, print_args) -> None:
        self.tester = tester
        self.print_args = print_args
        self.entered = False

    def __enter__(self):
        self.tester.enter(*self.print_args)
        self.entered = True
    
    def __exit__(self, exc_type, exc_value, _traceback):
        if (not exc_type) and (not exc_value):
            self.tester.leave()
        self.entered = False

class Tester:
    def __init__(self) -> None:
        self.inside = []
        self.cleanup = []
        self.passed = 0
    
    def number(self):
        return self.passed + len(self.inside)
    
    def print_indented(self, *print_args):
        indent = "..." * len(self.inside)
        print(NAME, indent, *print_args, file=sys.stderr)

    def enter(self, *print_args):
        self.print_indented(f"{self.number():04}", "Checking", *print_args)
        self.inside.append(print_args)
    
    def leave(self):
        print_args = self.inside.pop()
        self.passed += 1
        self.print_indented(f"{self.number():04}", "OK", *print_args)
    
    def run(self, *functions):
        self.failed = False
        for function in functions:
            try:
                function(self)
            except Exception as e:
                tb = traceback.TracebackException.from_exception(e)
                self.failed = True
                print("\n".join(tb.format(chain=False)), file=sys.stderr)
                if isinstance(e, http.client.RemoteDisconnected):
                    self.print("'Remote Disconnected' error is probably the result of an earlier error, scroll up!")
                while len(self.inside) > 0:
                    print_args = self.inside.pop()
                    self.print_indented(f"{self.number():04}", "FAIL", *print_args)
            finally:
                for cleanup_func in self.cleanup:
                    cleanup_func()
            # assert len(self.inside) == 0
            if not self.failed:
                self.print("ALL OK")
                self.print("Remember:")
                self.print("""
                    Your code still needs to follow all the rules and
                    perform its functions as described in the assignment.
                    
                    * This does not test everything possible.
                    * secret_tests will be run to make sure your code
                        isn't "memorizing" answers.
                    * You must NOT include any imports that aren't allowed
                        by the assignment, and follow all the other rules listed
                        in the assignment.
                    
                    Go re-read the assignment.
                """)
    
    def print(self, *args):
        self.print_indented(*args)
    
    def __call__(self, *print_args) -> Any:
        return TestEntry(self, print_args)

RANDOM_NUMBER_PREFIX = "Here's a random number: "
RANDOM_NUMBER_REGEX = re.escape(RANDOM_NUMBER_PREFIX) + r'\d+'

def relate(base, relative=None, *more):
    if relative is None:
        return base
    
    dot = hex(random.randrange(2**128))[2:]
    base = base.replace('.', dot)
    relative = relative.replace('.', dot)
    result = urljoin(base, relative).replace(dot, '.')
    if len(more) > 0:
        return relate(result, *more)
    
    return result

index_html = cleandoc("""
    <!DOCTYPE html>
    <html lang="en-CA">
    <head>
        <title>Example Page</title>
        <meta http-equiv="Content-Type" content="text/html;charset=utf-8">
        <!-- check conformance at http://validator.w3.org/check -->
        <link rel="stylesheet" type="text/css" href="base.css">
    </head>
    <body>
        <main class="eg">
            <h1>An Example Page</h1>
            <ul>
                <li>It works?</li>
                <li><a href="deep/index.html">A deeper page</a></li>
                <li>Here's a random number: 6601674</li>
            </ul>
        </main>
    </body>
    </html>
""")

base_css = cleandoc("""
    h1 {
        color:orange;
        text-align:center;
    }
""")

deep_index = cleandoc("""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Deeper Example Page</title>
            <meta http-equiv="Content-Type"
            content="text/html;charset=utf-8"/>
            <!-- check conformance at http://validator.w3.org/check -->
            <link rel="stylesheet" type="text/css" href="deep.css">
    </head>

    <body>
        <div class="eg">
            <h1>An Example of a Deeper Page</h1>
            <ul>
                <li>It works?</li>
                            <li><a href="../index.html">A page below!</a></li>
            </ul>
        </div>
    </body>
    </html> 
""")

deep_css = cleandoc("""
    h1 {
        color:green;
        text-align:center;
    }
""")

def one_giant_function(tester):
    global index_html
    with tester("Making www dir..."):
        with tester("you are running this file in the current directory"):
            wd = pathlib.Path(".").resolve()
            me = pathlib.Path(__file__).resolve().parent
            assert wd == me

        www = me / "www"

        if not www.is_dir():
            www.mkdir()

        with tester("writing files"):
            index_html_path = www / "index.html"
            assert RANDOM_NUMBER_PREFIX in index_html
            index_html = re.sub(RANDOM_NUMBER_REGEX, RANDOM_NUMBER_PREFIX+str(random.randrange(9999999)), index_html)
            index_html_path.write_text(index_html)
            assert index_html_path.read_text() == index_html

            base_css_path = www / "base.css"
            base_css_path.write_text(base_css)

            deep_path = www / "deep"
            if not deep_path.is_dir():
                deep_path.mkdir()
            
            deep_index_path = deep_path / "index.html"
            deep_index_path.write_text(deep_index)

            deep_css_path = deep_path / "deep.css"
            deep_css_path.write_text(deep_css)

    tester.enter("your code is named server.py in the same directory as this file!")
    import server
    tester.leave()

    tester.enter("your server has main")
    server_main = server.main
    tester.leave()

    tester.enter("your server has PORT")
    server_port = server.PORT
    tester.leave()

    tester.enter("starting your server")
    server_process = Process(target=server_main)
    
    def cleanup_server():
        tester.print("Killing the server...")
        server_process.kill()
        server_process.join(1)
        tester.print("KILLED")
        assert not server_process.is_alive()
    tester.cleanup.append(cleanup_server)

    server_process.start()
    tester.leave()

    tester.enter("did your server crash")
    server_process.join(1)
    assert server_process.is_alive()
    tester.leave()

    base_path = f"http://127.0.0.1:{server_port}/"

    def do_urlopen(relatives, data=None, method=None):
        if isinstance(data, str):
            data = data.encode()
        url = relate(base_path, *relatives)
        req = request.Request(url=url, data=data, method=method)
        tester.print(f"{method} {url}")
        return request.urlopen(req, timeout=1)

    def get(*relatives):
        return do_urlopen(relatives, method='GET')
    
    def post(*relatives, data=b''):
        return do_urlopen(relatives, data=data, method='POST')

    def same_text(expected, got):
        def repr_mostly(thing):
            r = repr(thing)
            if r[0] in ['"', "'"] and r[-1] in ['"', "'"]:
                r = r[1:-1]
            return r

        def ws_diff(expected, got):
            expected = list(map(repr_mostly, expected.splitlines(keepends=True)))
            got = list(map(repr_mostly, got.splitlines(keepends=True)))
            return list(difflib.unified_diff(expected, got, fromfile="expected", tofile="recieved"))

        if isinstance(expected, bytes):
            expected = expected.decode()
        if isinstance(got, bytes):
            got = got.decode()
        if expected != got:
            sys.stderr.write(os.linesep.join(ws_diff(expected, got)+['']))
        assert expected == got, "Didn't recieve what I expected, see diff above"
    
    def check_mime(expected, response):
        with tester("Content-Type is accurate"):
            assert 'Content-Type' in response.headers, "Missing Content-Type header"
            got = response.headers['Content-Type']
            if isinstance(expected, bytes):
                expected = expected.decode()
            if isinstance(got, bytes):
                got = got.decode()
            got = got.split(";")[0]
            assert expected == got, "Expected type {expected} got type {got}"

    with tester("get index.html directly"):
        response = get("/index.html")

        with tester("Response 200 OK"):
            assert response.status == 200, f"Expected code 200 got {response.status}"
            assert response.reason == "OK"
        
        with tester("Content is accurate"):
            same_text(index_html, response.read())
        
        check_mime("text/html", response)

    with tester("get /"):
        response = get("")

        with tester("Response 200 OK"):
            assert response.status == 200, f"Expected code 200 got {response.status}"
            assert response.reason == "OK"
        
        with tester("Content is accurate"):
            same_text(index_html, response.read())
        
        check_mime("text/html", response)
    
    with tester("get /base.css"):
        response = get("/base.css")

        with tester("Response 200 OK"):
            assert response.status == 200, f"Expected code 200 got {response.status}"
            assert response.reason == "OK"
        
        with tester("Content is accurate"):
            same_text(base_css, response.read())
        
        check_mime("text/css", response)

    with tester("a page that doesn't exist"):
        dne_path = www / "doesnt_exist.html"
        assert not dne_path.exists()

        with tester("GET /doesnt_exist.html"):
            response = get("doesnt_exist.html")
            assert response.status == 404, f"Expected code 404 got {response.status}"

    with tester("/deep"):
        with tester("GET /deep"):
            response = get("deep")
            assert response.status in [301, 308], f"Expected code 303 got {response.status}"
            assert 'Location' in response.headers, f"Didn't find location header"
            location = response.headers['Location']
            assert location.endswith('/'), location

        with tester("following redirect"):
            response = get(response.url, location)
            assert response.status == 200, f"Expected code 200 got {response.status}"
            same_text(deep_index, response.read())
            check_mime("text/html", response)
            
            with tester("deep/deep.css"):
                response = get(response.url, "deep.css")
    
    with tester("how secure are you?"):
        response = get("../../../../../../../../../../etc/os-release")
        assert response.status in [403, 404], f"Expected code 403 got {response.status}"
    
    with tester("testing 405s"):
        response = post('', data="heh?")
        assert response.status == 405, f"Expected code 405 got {response.status}"


def main():
    tester = Tester()
    tester.run(one_giant_function)

if __name__ == "__main__":
    main()
