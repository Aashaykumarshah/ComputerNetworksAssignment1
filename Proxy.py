
import socket
import sys
import os
import argparse
import re

# 1MB buffer size
BUFFER_SIZE = 1000000

# Get the IP address and Port number to use for this web proxy server
parser = argparse.ArgumentParser()
parser.add_argument('hostname', help='the IP Address Of Proxy Server')
parser.add_argument('port', help='the port number of the proxy server')
args = parser.parse_args()
proxyHost = args.hostname
proxyPort = int(args.port)

# Create a server socket, bind it to a port and start listening
try:
  serverSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)  # ~~~~ INSERT CODE ~~~~
  serverSocket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
  print ('Created socket')
except:
  print ('Failed to create socket')
  sys.exit()

try:
  serverSocket.bind((proxyHost, proxyPort))  # ~~~~ INSERT CODE ~~~~
  print ('Port is bound')
except:
  print('Port is already in use')
  sys.exit()

try:
  serverSocket.listen(5)  # ~~~~ INSERT CODE ~~~~
  print ('Listening to socket')
except:
  print ('Failed to listen')
  sys.exit()

# continuously accept connections
while True:
  print ('Waiting for connection...')
  clientSocket = None

  try:
    clientSocket, clientAddress = serverSocket.accept()  # ~~~~ INSERT CODE ~~~~
    print ('Received a connection')
  except:
    print ('Failed to accept connection')
    sys.exit()

  try:
    message_bytes = clientSocket.recv(4096)  # ~~~~ INSERT CODE ~~~~
  except:
    print('Failed to receive data from client')
    clientSocket.close()
    continue

  message = message_bytes.decode('utf-8')
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

    clientSocket.sendall(cacheData)  # ~~~~ INSERT CODE ~~~~
    cacheFile.close()
    print ('Sent to the client.')
  except:
    originServerSocket = None

    try:
      originServerSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)  # ~~~~ INSERT CODE ~~~~

      print ('Connecting to:\t\t' + hostname + '\n')

      address = socket.gethostbyname(hostname)
      originServerSocket.connect((address, 80))  # ~~~~ INSERT CODE ~~~~
      print ('Connected to origin Server')

      originServerRequest = f"{method} {resource} {version}"
      originServerRequestHeader = f"Host: {hostname}\r\nConnection: close"
      # ~~~~ INSERT CODE ~~~~

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
        data = originServerSocket.recv(BUFFER_SIZE)  # ~~~~ INSERT CODE ~~~~
        if not data:
          break
        response_data += data

      clientSocket.sendall(response_data)  # ~~~~ INSERT CODE ~~~~

      cacheDir, file = os.path.split(cacheLocation)
      print ('cached directory ' + cacheDir)
      if not os.path.exists(cacheDir):
        os.makedirs(cacheDir)
      cacheFile = open(cacheLocation, 'wb')

      cacheFile.write(response_data)  # ~~~~ INSERT CODE ~~~~
      cacheFile.close()
      print ('cache file closed')

      print ('origin response received. Closing sockets')
      originServerSocket.close()

      clientSocket.shutdown(socket.SHUT_WR)
      print ('client socket shutdown for writing')
    except OSError as err:
      print ('origin server request failed. ' + err.strerror)

  try:
    clientSocket.close()
  except:
    print ('Failed to close client socket')
