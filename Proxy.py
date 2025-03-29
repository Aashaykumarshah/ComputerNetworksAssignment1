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
    serverSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
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
    serverSocket.listen(10)
    print('Listening to socket')
except:
    print('Failed to listen')
    sys.exit()

while True:
    print('Waiting for connection...')
    try:
        clientSocket, _ = serverSocket.accept()
        print('Received a connection')
    except:
        print('Failed to accept connection')
        continue

    try:
        message_bytes = clientSocket.recv(BUFFER_SIZE)
        message = message_bytes.decode('utf-8')
        print('< ' + message)
    except:
        clientSocket.close()
        continue

    requestParts = message.split()
    if len(requestParts) < 3:
        clientSocket.close()
        continue

    method, URI, version = requestParts[:3]

    URI = re.sub('^(/?)http(s?)://', '', URI, count=1)
    URI = URI.replace('/..', '')
    resourceParts = URI.split('/', 1)
    hostname = resourceParts[0]
    resource = '/' + resourceParts[1] if len(resourceParts) == 2 else '/'

    cacheLocation = './' + hostname + resource
    if cacheLocation.endswith('/'):
        cacheLocation += 'default'

    print('Cache location:		' + cacheLocation)
    fileExists = os.path.isfile(cacheLocation)

    if fileExists:
        try:
            with open(cacheLocation, 'rb') as cacheFile:
                cacheData = cacheFile.read()
                clientSocket.sendall(cacheData)
                print('Sent to the client: (from cache)')
        except Exception as e:
            print('Cache read error:', e)
    else:
        try:
            originServerSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            address = socket.gethostbyname(hostname)
            originServerSocket.connect((address, 80))
            print('Connected to origin Server')

            originRequest = f"GET {resource} HTTP/1.1\r\nHost: {hostname}\r\nConnection: close\r\n\r\n"
            originServerSocket.sendall(originRequest.encode())

            response = b''
            while True:
                data = originServerSocket.recv(BUFFER_SIZE)
                if not data:
                    break
                response += data

            clientSocket.sendall(response)

            cacheDir = os.path.dirname(cacheLocation)
            if not os.path.exists(cacheDir):
                os.makedirs(cacheDir)
            with open(cacheLocation, 'wb') as cacheFile:
                cacheFile.write(response)

            originServerSocket.close()
            clientSocket.shutdown(socket.SHUT_WR)
            print('Origin response sent and cached')
        except Exception as e:
            print('Origin server request failed:', e)

    clientSocket.close()
