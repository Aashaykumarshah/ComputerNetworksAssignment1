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

while True:
  print('\nProxy ready for connections...')
  clientSocket = None

  try:
    clientSocket, addr = serverSocket.accept()
    print('Received a connection from:', addr)
  except:
    print('Failed to accept connection')
    sys.exit()

  try:
    message_bytes = clientSocket.recv(4096)
    print('Received raw request (first 200 bytes):')
    print(message_bytes[:200])
  except:
    print('Failed to receive data from client')
    clientSocket.close()
    continue

  message = message_bytes.decode('utf-8', errors='ignore')
  print('Full decoded request:')
  print('< ' + message)

  requestParts = message.split()
  if len(requestParts) < 3:
    print('Invalid HTTP request')
    clientSocket.close()
    continue

  method = requestParts[0]
  URI = requestParts[1]
  version = requestParts[2]

  print('Method:\t' + method)
  print('URI:\t' + URI)
  print('Version:\t' + version)

  URI = re.sub('^(/?)http(s?)://', '', URI, count=1)
  URI = URI.replace('/..', '')

  resourceParts = URI.split('/', 1)
  hostname = resourceParts[0]
  resource = '/' + resourceParts[1] if len(resourceParts) == 2 else '/'

  print('Hostname:\t' + hostname)
  print('Resource:\t' + resource)

  try:
    cacheLocation = './' + hostname + resource
    if cacheLocation.endswith('/'):
        cacheLocation = cacheLocation + 'default'

    print('Cache path:\t' + cacheLocation)

    cacheFile = open
