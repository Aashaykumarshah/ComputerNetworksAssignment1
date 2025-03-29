import socket
import sys
import os
import argparse
import re

BUFFER_SIZE = 1000000

# Argument parsing
parser = argparse.ArgumentParser()
parser.add_argument('hostname', help='IP address of the proxy server')
parser.add_argument('port', type=int, help='Port number of the proxy server')
args = parser.parse_args()

proxy_host = args.hostname
proxy_port = args.port

# Start proxy server
try:
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind((proxy_host, proxy_port))
    server_socket.listen(5)
    print(f"Proxy server running on {proxy_host}:{proxy_port}")
except Exception as e:
    print(f"Failed to set up server socket: {e}")
    sys.exit()

# Main server loop
while True:
    try:
        print("Waiting for connection...")
        client_socket, client_address = server_socket.accept()
        print(f"Connection established with {client_address}")
    except Exception as e:
        print(f"Error accepting connection: {e}")
        continue

    try:
        request_data = client_socket.recv(4096)
        request_text = request_data.decode('utf-8')
        print("Received request:")
        print(request_text)
    except Exception as e:
        print(f"Error receiving or decoding request: {e}")
        client_socket.close()
        continue

    # Parse HTTP request
    request_lines = request_text.split()
    if len(request_lines) < 3:
        print("Invalid HTTP request")
        client_socket.close()
        continue

    method = request_lines[0]
    uri = request_lines[1]
    version = request_lines[2]

    # Clean the URI
    uri = re.sub(r'^(/?)http(s?)://', '', uri, count=1)
    uri = uri.replace('/..', '')  # Prevent directory traversal
    parts = uri.split('/', 1)
    hostname = parts[0]
    resource = '/' + parts[1] if len(parts) == 2 else '/'

    print(f"Method: {method}")
    print(f"URI: {uri}")
    print(f"Version: {version}")
    print(f"Host: {hostname}")
    print(f"Resource: {resource}")

    # Construct cache location
    cache_path = './' + hostname + resource
    if cache_path.endswith('/'):
        cache_path += 'default'
    print(f"Cache path: {cache_path}")

    # Check if in cache
    if os.path.isfile(cache_path):
        try:
            with open(cache_path, 'rb') as cache_file:
                cached_response = cache_file.read()
            print("Cache hit. Serving from cache.")
            client_socket.sendall(cached_response)
            client_socket.close()
            continue
        except Exception as e:
            print(f"Error reading from cache: {e}")

    # Cache miss, fetch from origin server
    try:
        origin_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        origin_ip = socket.gethostbyname(hostname)
        origin_socket.connect((origin_ip, 80))
        print(f"Connected to origin server {hostname} ({origin_ip})")
    except Exception as e:
        print(f"Failed to connect to origin server: {e}")
        client_socket.close()
        continue

    origin_request = f"{method} {resource} {version}\r\nHost: {hostname}\r\nConnection: close\r\n\r\n"

    try:
        origin_socket.sendall(origin_request.encode())
    except Exception as e:
        print(f"Error sending request to origin: {e}")
        origin_socket.close()
        client_socket.close()
        continue

    # Receive response from origin
    origin_response = b''
    try:
        while True:
            chunk = origin_socket.recv(BUFFER_SIZE)
            if not chunk:
                break
            origin_response += chunk
    except Exception as e:
        print(f"Error receiving from origin server: {e}")

    # Send response to client
    try:
        client_socket.sendall(origin_response)
    except Exception as e:
        print(f"Error sending response to client: {e}")

    # Save to cache
    try:
        cache_dir = os.path.dirname(cache_path)
        if not os.path.exists(cache_dir):
            os.makedirs(cache_dir)
        with open(cache_path, 'wb') as cache_file:
            cache_file.write(origin_response)
        print("Saved response to cache.")
    except Exception as e:
        print(f"Error writing to cache: {e}")

    origin_socket.close()
    client_socket.close()
