# http_proxy_server.py
import socket
import sys
import os
import argparse
import re

BUFFER_SIZE = 1000000

parser = argparse.ArgumentParser()
parser.add_argument('hostname', help='the IP Address Of Proxy Server')
parser.add_argument('port', help='the port number of the proxy server')
args = parser.parse_args()
proxyHost = args.hostname
proxyPort = int(args.port)

try:
  # Create a server socket
  serverSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
  print('Created socket')
except:
  print('Failed to create socket')
  sys.exit()

try:
  # Bind the the server socket to a host and port
  serverSocket.bind((proxyHost, proxyPort))
  print('Port is bound')
except:
  print('Port is already in use')
  sys.exit()

try:
  # Listen on the server socket
  serverSocket.listen(10)
  print('Listening to socket')
except:
  print('Failed to listen')
  sys.exit()

# continuously accept connections
while True:
  print('Waiting for connection...')
  clientSocket = None

  try:
    # Accept connection from client and store in the clientSocket
    clientSocket, _ = serverSocket.accept()
    print('Received a connection')
  except:
    print('Failed to accept connection')
    sys.exit()

  try:
    # Get HTTP request from client and store it in the variable: message_bytes
    message_bytes = clientSocket.recv(BUFFER_SIZE)
    message = message_bytes.decode('utf-8')
    print('Received request:')
    print('< ' + message)
  except:
    clientSocket.close()
    continue

  requestParts = message.split()
  if len(requestParts) < 3:
    clientSocket.close()
    continue

  method = requestParts[0]
  URI = requestParts[1]
  version = requestParts[2]

  print('Method:\t\t' + method)
  print('URI:\t\t' + URI)
  print('Version:\t' + version)
  print('')

  URI = re.sub('^(/?)http(s?)://', '', URI, count=1)
  URI = URI.replace('/..', '')
  resourceParts = URI.split('/', 1)
  hostname = resourceParts[0]
  resource = '/' + resourceParts[1] if len(resourceParts) == 2 else '/'

  print('Requested Resource:\t' + resource)

  try:
    cacheLocation = './' + hostname + resource
    if cacheLocation.endswith('/'):
        cacheLocation = cacheLocation + 'default'

    print('Cache location:\t\t' + cacheLocation)

    fileExists = os.path.isfile(cacheLocation)
    cacheFile = open(cacheLocation, "rb")
    cacheData = cacheFile.read()

    print('Cache hit! Loading from cache file: ' + cacheLocation)

    # ProxyServer finds a cache hit, Send back response to client
    clientSocket.sendall(cacheData)
    cacheFile.close()
    print('Sent to the client:')
  except:
    originServerSocket = None

    try:
      # Create a socket to connect to origin server and store in originServerSocket
      originServerSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
      print('Connecting to:\t\t' + hostname + '\n')

      # Get the IP address for a hostname
      address = socket.gethostbyname(hostname)
      # Connect to the origin server
      originServerSocket.connect((address, 80))
      print('Connected to origin Server')

      # Create origin server request line and headers to send
      originServerRequest = f"GET {resource} HTTP/1.1"
      originServerRequestHeader = f"Host: {hostname}\r\nConnection: close"

      request = originServerRequest + '\r\n' + originServerRequestHeader + '\r\n\r\n'
      print('Forwarding request to origin server:')
      for line in request.split('\r\n'):
        print('> ' + line)

      try:
        originServerSocket.sendall(request.encode())
      except socket.error:
        print('Forward request to origin failed')
        sys.exit()

      print('Request sent to origin server\n')

      # Get the response from the origin server
      response = b''
      while True:
        data = originServerSocket.recv(BUFFER_SIZE)
        if not data:
          break
        response += data

      # Send the response to the client
      clientSocket.sendall(response)

      cacheDir, file = os.path.split(cacheLocation)
      print('cached directory ' + cacheDir)
      if not os.path.exists(cacheDir):
        os.makedirs(cacheDir)
      cacheFile = open(cacheLocation, 'wb')

      # Save origin server response in the cache file
      cacheFile.write(response)
      cacheFile.close()
      print('cache file closed')

      originServerSocket.close()
      clientSocket.shutdown(socket.SHUT_WR)
      print('origin response received. Closing sockets')
      print('client socket shutdown for writing')

    except OSError as err:
      print('origin server request failed. ' + err.strerror)

  try:
    clientSocket.close()
  except:
    print('Failed to close client socket')
