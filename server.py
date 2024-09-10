#!/usr/bin/env python3

"""
A basic Python 3 HTTP/1.1 server.
"""

import socketserver
import pathlib

HOST = "0.0.0.0"
PORT = 8000
BUFSIZE = 4096
LINE_ENDING='\r\n'
SERVE_PATH = pathlib.Path('www').resolve()
HTTP_1_1 = 'HTTP/1.1'

class LabServer(socketserver.TCPServer):
    allow_reuse_address = True

class LabServerTCPHandler(socketserver.StreamRequestHandler):
    def __init__(self, *args, **kwargs):
        self.charset = "UTF-8"
        self.serve_path = pathlib.Path("www").resolve()
        super().__init__(*args, **kwargs)

    def recieve_line(self):
        return self.rfile.readline().strip().decode(self.charset, 'ignore')
    
    def send_line(self, line):
        self.wfile.write((line + LINE_ENDING).encode(self.charset, 'ignore'))
    
    def handle(self):
        """
        Handles incoming HTTP requests. Parses the request, checks the method,
        constructs the response based on the request path, and sends the appropriate
        response to the client.
        """
        start_line = self.recieve_line()  # Read the start line of the HTTP request
        print("<", start_line)

        # Split the start line into its method and path
        start_line_split = start_line.split()
        method = start_line_split[0]
        path = start_line_split[1]

        # Handle only GET method, send 405 Method Not Allowed for other methods
        if method != 'GET':
            self.send_headers('405 Method Not Allowed', 'text/html', 0)
            return
        
        # Normalize and secure the path
        secure_path = self.secure_path(path)

        # Send 404 Not Found if the path is not within the serve path
        if secure_path is None:
            self.send_headers('404 Not Found', 'text/html', 0)
            return

        # Redirect to path with '/' if it's a directory and doesn't end with '/'
        if secure_path.is_dir() and not path.endswith('/'):
            self.send_redirect(path + '/', '301 Moved Permanently')
            return

        # Serve the index.html file if the path is a directory
        if secure_path.is_dir():
            index_path = secure_path / 'index.html'
            if index_path.exists():
                self.send_file_content(index_path, 'text/html')
            else:
                self.send_headers('404 Not Found', 'text/html', 0)

        # Serve the file if the path is a file
        elif secure_path.is_file():
            content_type = ''
            if str(secure_path).endswith('.html'):
                content_type = 'text/html'
            elif str(secure_path).endswith('.css'):
                content_type = 'text/css'

            self.send_file_content(secure_path, content_type)
        # Send 404 Not Found for non-existing paths
        else:
            self.send_headers('404 Not Found', 'text/html', 0)

    def send_redirect(self, new_path, status_code):
        """
        Sends a redirect response to the client.
        
        :param new_path: The path to redirect to.
        :param status_code: The HTTP status code for redirection.
        """
        # Send the HTTP status line with the status code
        self.send_line(f"{HTTP_1_1} {status_code}")
        # Send the Location header with the new path
        self.send_line(f"Location: {new_path}")
        # Close the connection after sending the response
        self.send_line("Connection: close")
        # Send an empty line to indicate the end of the headers
        self.send_line("")

    def send_headers(self, status_code, content_type, content_length):
        """
        Sends the HTTP response headers.

        :param status_code: The HTTP status code for the response.
        :param content_type: The type of the response content.
        :param content_length: The length of the response content.
        """
        # Send the HTTP status line
        self.send_line(f"{HTTP_1_1} {status_code}")
        # Send the Content-Type header
        self.send_line(f"Content-Type: {content_type}")
        # Send the Content-Length header
        self.send_line(f"Content-Length: {content_length}")
        # Close the connection after sending the response
        self.send_line("Connection: close")
        # Send an empty line to indicate the end of the headers
        self.send_line("")

    def send_file_content(self, file_path, content_type):
        """
        Read and send the file content.

        :param file_path: The path to the file to read and extract the content.
        :param content_type: The type of the file.
        """
        # Open and read the file
        with open(file_path, 'rb') as file:
            content = file.read()
            # Determine the content length
            content_length = str(len(content))
            # Send headers with OK status, content type, and content length
            self.send_headers('200 OK', content_type, content_length)
            # Write the content to the response
            self.wfile.write(content)

    def secure_path(self, path):
        """
        Verify if the given path is within the self.serve_path directory.

        Note: This method is adapted from a Stack Overflow discussion:
        "How to check whether a directory is a sub-directory of another directory"
        URL: https://stackoverflow.com/questions/3812849/how-to-check-whether-a-directory-is-a-sub-directory-of-another-directory
        Date Accessed: January 20, 2024

        :param path: The path (relative to self.serve_path) to check and resolve.
        :return: The resolved pathlib.Path object if the path is a valid subdirectory of self.serve_path, None otherwise.
        """
    
        # Resolve the path and check if it is within the serve path
        resolved_path = (self.serve_path / path.strip('/')).resolve()
        if self.serve_path in resolved_path.parents or resolved_path == self.serve_path:
            # Return the resolved path if it is within the serve path
            return resolved_path
        # Return None if the path is not within the serve path
        return None
def main():
    # From https://docs.python.org/3/library/socketserver.html, The Python Software Foundation, downloaded 2024-01-07
    with LabServer((HOST, PORT), LabServerTCPHandler) as server:
        server.serve_forever()

if __name__ == "__main__":
    main()