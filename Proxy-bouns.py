import socket
import sys
import os
import argparse
import re
import time
from urllib.parse import urlparse

# 1MB buffer size
BUFFER_SIZE = 1000000

# Get the IP address and Port number to use for this web proxy server
parser = argparse.ArgumentParser()
parser.add_argument('hostname', help='the IP Address Of Proxy Server')
parser.add_argument('port', help='the port number of the proxy server')
args = parser.parse_args()
proxyHost = args.hostname
proxyPort = int(args.port)

# Map to store max-age based expiry times
expiry_cache = {}

# Create a server socket, bind it to a port and start listening
try:
  serverSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
  serverSocket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
  print('Created socket')
except:
  print('Failed to create socket')
  sys.exit()

try:
  serverSocket.bind((proxyHost, proxyPort))
  print('Port is bound')
except:
  print('Port is already in use')
  sys.exit()

try:
  serverSocket.listen(5)
  print('Listening to socket')
except:
  print('Failed to listen')
  sys.exit()

# continuously accept connections
while True:
  print('Waiting for connection...')
  clientSocket = None
  
  # Accept connection from client and store in the clientSocket
  try:
    clientSocket, clientAddress = serverSocket.accept()
    print('Received a connection')
  except:
    print('Failed to accept connection')
    sys.exit()

  # Get HTTP request from client
  # and store it in the variable: message_bytes
  try:
    message_bytes = clientSocket.recv(4096)
  except:
    print('Failed to receive data from client')
    clientSocket.close()
    continue
  message = message_bytes.decode('utf-8')
  print('< ' + message)
  
  # Extract the method, URI and version of the HTTP client request 
  requestParts = message.split()
  if len(requestParts) < 3:
    clientSocket.close()
    continue

  method = requestParts[0]
  URI = requestParts[1]
  version = requestParts[2]
 
  # Get the requested resource from URI
  # Remove http protocol from the URI
  URI = re.sub('^(/?)http(s?)://', '', URI, count=1)
  # Remove parent directory changes - security
  URI = URI.replace('/..', '')
  # Split hostname from resource name
  resourceParts = URI.split('/', 1)
  hostname = resourceParts[0]
  resource = '/' + resourceParts[1] 
  if len(resourceParts) == 2 
  else '/'

  cacheLocation = './' + hostname + resource
  if cacheLocation.endswith('/'):
    cacheLocation = cacheLocation + 'default'

  expired = False
  if cacheLocation in expiry_cache:
    expiry_time = expiry_cache[cacheLocation]
    if time.time() > expiry_time:
      expired = True

  if os.path.isfile(cacheLocation) and not expired:
    try:
      with open(cacheLocation, 'rb') as cacheFile:
        cacheData = cacheFile.read()
        clientSocket.sendall(cacheData)
        print('Sent to client from cache')
        clientSocket.close()
        continue
    except Exception as e:
      print('Cache read error:', e)
  # Check if resource is in cache
  try:
    originServerSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    print('Connecting to:	' + hostname)
    address = socket.gethostbyname(hostname)
    port = 80
    if ':' in hostname:
      hostname, port = hostname.split(':')
      port = int(port)
    originServerSocket.connect((hostname, port))
    print('Connected to origin Server')

    originRequest = f"GET {resource} HTTP/1.1"
    originRequestHeader = f"Host: {hostname}\r\nConnection: close"
    request = originRequest + '\r\n' + originRequestHeader + '\r\n\r\n'
    originServerSocket.sendall(request.encode())

    response_data = b''
    while True:
      data = originServerSocket.recv(BUFFER_SIZE)
      if not data:
        break
      response_data += data

    headers_end = response_data.find(b'\r\n\r\n')
    headers = response_data[:headers_end].decode(errors='ignore')
    lines = headers.split('\r\n')
    for line in lines:
      if 'Cache-Control:' in line and 'max-age' in line:
        try:
          max_age = int(re.findall(r'max-age=(\d+)', line)[0])
          expiry_cache[cacheLocation] = time.time() + max_age
        except:
          pass

    clientSocket.sendall(response_data)
    os.makedirs(os.path.dirname(cacheLocation), exist_ok=True)
    with open(cacheLocation, 'wb') as cacheFile:
      cacheFile.write(response_data)

    originServerSocket.close()
    clientSocket.shutdown(socket.SHUT_WR)
    clientSocket.close()
  except Exception as e:
    print('Origin server request failed:', e)
    clientSocket.close()
    continue
