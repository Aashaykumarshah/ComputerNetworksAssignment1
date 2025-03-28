import socket
import sys
import os
import argparse


# 1MB buffer size
BUFFER_SIZE = 1000000
parser = argparse.ArgumentParser()
parser.add_argument('hostname', help='the IP Address Of Proxy Server')
parser.add_argument('port', help='the port number of the proxy server')
args = parser.parse_args()

proxyHost = args.hostname
proxyPort = args.port
serverSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
serverSocket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
serverSocket.bind((proxyHost, proxyPort)) 
serverSocket.listen(5)
