from DDDProxy.server import ServerHandler, baseServer, DDDProxySocketMessage
import DDDProxyConfig
from DDDProxy.socetMessageParser import socetMessageParser
from DDDProxy import hostParser, domainConfig
import re
import socket
import sys
import traceback
import ssl
import time
import math
import struct
import hashlib
import thread
import threading



class proxyServerHandler(ServerHandler):  
	def __init__(self, conn, addr, threadid):
		super(proxyServerHandler, self).__init__(conn, addr, threadid)
		self.source = conn
# 		self.source.settimeout(sendPack.timeout);
		self.method = ""
		self.threadid = threadid
		self.remoteSocket = None
		self.httpMessage = ""
		self.blockHost = DDDProxyConfig.blockHost
	def info(self):
		return "%s	%s" % (ServerHandler.info(self), self.httpMessage)
	def domainAnalysisAddData(self,dataType,length):
		domainConfig.analysis.incrementData(addr=self.addr, dataType=dataType, hostPort=self.hostPort, message=self.httpMessage, length=length)
	def sourceToServer(self):
		baseServer.log(1, self.threadid, "}}}}", "<")
		try:
			socetParser = socetMessageParser()
			while self.source != None:
				tmp = self.source.recv(DDDProxyConfig.cacheSize)
				if not tmp:
					break
				baseServer.log(1, "}}}}", tmp)
				DDDProxySocketMessage.send(self.remoteSocket, tmp)
				if socetParser is not None:
					socetParser.putMessage(tmp)
					if socetParser.messageStatus():
						self.httpMessage = socetParser.httpMessage()
						host, port = hostParser.parserUrlAddrPort(
							self.httpMessage[1]
							if self.httpMessage[0] != "CONNECT"
							else f"https://{self.httpMessage[1]}"
						)
						threading.currentThread().name = "%d-%s-%s:%d-send"%(self.threadid,self.addr,host,port)
						self.hostPort = (host, port)

						ipAddr = re.match("(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3})", host)
						foundIp = False
						if ipAddr:
							ipAddr = ipAddr.groups()
							mathIp = f"{ipAddr[0]}.{ipAddr[1]}.{ipAddr[2]}";
							for i in self.blockHost:
								if i.startswith(mathIp):
									foundIp = True
									break
						if foundIp or host in self.blockHost:
							baseServer.log(3, self.threadid, "block", host)
							break

						baseServer.log(1, "}}}}", self.addr, self.httpMessage)
						self.domainAnalysisAddData("connect", 1)
						socetParser = None

				self.domainAnalysisAddData("incoming", len(tmp))
				self.markActive()
		except socket.timeout:
			pass
		except:
			baseServer.log(3, self.threadid, "}}}} error!", sys.exc_info(), traceback.format_exc())

# 		sendPack.end(self.remoteSocket)
		baseServer.log(1, self.threadid, "}}}}", ">")

		self.close()
		
	def serverToSource(self):
		baseServer.log(1, self.threadid, "-<")
		try:
			for data in DDDProxySocketMessage.recv(self.remoteSocket):
				self.source.send(data)
				self.markActive()
				self.domainAnalysisAddData("outgoing", len(data))
		except:
			pass
		baseServer.log(1, self.threadid, "->")
		self.close()
		
	def connRemoteProxyServer(self):

		DDDProxyConfig.fetchRemoteCert()
		
		self.remoteSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		self.remoteSocket = ssl.wrap_socket(self.remoteSocket, ca_certs=DDDProxyConfig.SSLLocalCertPath,
										 cert_reqs=ssl.CERT_REQUIRED)		
		self.remoteSocket.connect((DDDProxyConfig.remoteServerHost, DDDProxyConfig.remoteServerListenPort))
		randomNum = math.floor(time.time())
		self.remoteSocket.send(struct.pack("i", randomNum))
		checkA = hashlib.md5("%s%d" % (DDDProxyConfig.remoteServerAuth, randomNum)).hexdigest()
		self.remoteSocket.send(checkA)
		baseServer.log(1, self.threadid, checkA, randomNum)

	def close(self):
		try:
			if self.source:
				self.source.shutdown(0)
		except:
			pass
		self.source = None
		try:
			if self.remoteSocket:
				DDDProxySocketMessage.end(self.remoteSocket)
		except:
			pass
		try:
			if self.remoteSocket:
				self.remoteSocket.shutdown(0)
		except:
			pass
		self.remoteSocket = None
	def AgreeConnIp(self, ipAddr=''):
		return bool(
			ipAddr.startswith("127.0.0.")
			or ipAddr.startswith("10.0.")
			or ipAddr.startswith("192.168.")
		)
	def run(self):
		if not self.AgreeConnIp(self.addr):
			baseServer.log(2, self.threadid, f"not agree ip {self.addr} connect!")
			return;

		baseServer.log(1, self.threadid, "..... threadid start")
		self.connRemoteProxyServer()
		DDDProxySocketMessage.sendOne(self.remoteSocket, "[%d]" % (self.threadid))
		baseServer.log(1, self.threadid, "threadid mark")
		thread.start_new_thread(self.sourceToServer, tuple())
		threading.currentThread().name = "%d-%s-recv"%(self.threadid,self.addr)
		self.serverToSource()
		baseServer.log(1, self.threadid, "!!!!! threadid end")
