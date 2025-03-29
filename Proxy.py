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

# Create a server socket, bind it to a port and start listening
try:
  serverSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
  serverSocket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
  print ('Created socket')
except:
  print ('Failed to create socket')
  sys.exit()

try:
  serverSocket.bind((proxyHost, proxyPort))
  print ('Port is bound')
except:
  print('Port is already in use')
  sys.exit()

try:
  serverSocket.listen(5)
  print ('Listening to socket')
except:
  print ('Failed to listen')
  sys.exit()

# continuously accept connections
while True:
  print ('Waiting for connection...')
  clientSocket = None

  try:
    clientSocket, addr = serverSocket.accept()
    print ('Received a connection')
  except:
    print ('Failed to accept connection')
    sys.exit()

  try:
    message_bytes = clientSocket.recv(4096)
  except:
    print('Failed to receive data from client')
    clientSocket.close()
    continue

  message = message_bytes.decode('utf-8', errors='ignore')
  print ('Received request:')
  print ('< ' + message)

  requestParts = message.split()
  if len(requestParts) < 3:
    print("Invalid HTTP request")
    clientSocket.close()
    continue

  method = requestParts[0]
  URI = requestParts[1]
  version = requestParts[2]

  print ('Method:\t\t' + method)
  print ('URI:\t\t' + URI)
  print ('Version:\t' + version)
  print ('')

  URI = re.sub('^(/?)http(s?)://', '', URI, count=1)
  URI = URI.replace('/..', '')

  resourceParts = URI.split('/', 1)
  hostname = resourceParts[0]
  resource = '/' + resourceParts[1] if len(resourceParts) == 2 else '/'

  print ('Requested Resource:\t' + resource)

  try:
    cacheLocation = './' + hostname + resource
    if cacheLocation.endswith('/'):
        cacheLocation = cacheLocation + 'default'

    print ('Cache location:\t\t' + cacheLocation)

    fileExists = os.path.isfile(cacheLocation)
    cacheFile = open(cacheLocation, "rb")
    cacheData = cacheFile.read()

    print ('Cache hit! Loading from cache file: ' + cacheLocation)
    clientSocket.sendall(cacheData)
    cacheFile.close()
    print ('Sent to the client (from cache).')
  except:
    originServerSocket = None

    try:
      originServerSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
      print ('Connecting to:\t\t' + hostname + '\n')
      address = socket.gethostbyname(hostname)
      originServerSocket.connect((address, 80))
      print ('Connected to origin Server')

      originServerRequest = f"{method} {resource} {version}"
      originServerRequestHeader = (
          f"Host: {hostname}\r\n"
          "User-Agent: Mozilla/5.0\r\n"
          "Accept: */*\r\n"
          "Connection: close"
      )

      request = originServerRequest + '\r\n' + originServerRequestHeader + '\r\n\r\n'

      print ('Forwarding request to origin server:')
      for line in request.split('\r\n'):
        print ('> ' + line)

      try:
        originServerSocket.sendall(request.encode())
      except socket.error:
        print ('Forward request to origin failed')
        sys.exit()

      print('Request sent to origin server\n')

      response_data = b''
      while True:
        data = originServerSocket.recv(BUFFER_SIZE)
        if not data:
          break
        response_data += data

      # Check for 404 or redirect
      status_line = response_data.split(b'\r\n')[0].decode(errors='ignore')
      if "404 Not Found" in status_line:
        print("404 Not Found - not caching")
        clientSocket.sendall(response_data)
        originServerSocket.close()
        clientSocket.close()
        continue
      if "301" in status_line or "302" in status_line:
        print("Redirect response - not caching")
        clientSocket.sendall(response_data)
        originServerSocket.close()
        clientSocket.close()
        continue

      # Send to client
      clientSocket.sendall(response_data)

      # Save to cache
      cacheDir, file = os.path.split(cacheLocation)
      print ('cached directory ' + cacheDir)
      if not os.path.exists(cacheDir):
        os.makedirs(cacheDir)
      with open(cacheLocation, 'wb') as cacheFile:
        cacheFile.write(response_data)
      print ('Saved to cache.')

      print ('origin response received. Closing sockets')
      originServerSocket.close()
    except OSError as err:
      print ('origin server request failed. ' + err.strerror)

  try:
    clientSocket.close()
  except:
    print ('Failed to close client socket')
