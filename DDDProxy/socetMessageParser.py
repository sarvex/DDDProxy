import re
class socetMessageParser():
	def __init__(self):
		self.message = ""
		self.lastMessage = ""
	def clear(self):
		self.lastMessage = self.message
		self.message = ""
		
	def putMessage(self, data):
		self.message += data
	
	def messageStatus(self):
		method, path, protocol = self.httpMessage()
		if protocol:
			if headers := self.httpHeaders():
				if method != "POST":
					return 1

				if "content-length" in headers and (int(headers["content-length"]) <= len(self.httpBodyStr())):
					return 1
		return 0

	def messageData(self):
		return self.message
		
	def httpMessage(self):
		if self.message.find("\r\n") > 0:
			firstLine = self.message.split('\r\n', 1)[0]
			try:
				method, path, protocol = firstLine.split()
				if re.match("HTTP/\d.\d", protocol):
					return method, path, protocol
			except:
				pass
		return "", "", ""
	def httpHeadersStr(self):
		method, path, protocol = self.httpMessage()
		return "" if not protocol else self.message.split("\r\n\r\n", 1)[0]
	def httpBodyStr(self):
		method, path, protocol = self.httpMessage()
		return "" if not protocol else self.message.split("\r\n\r\n", 1)[1]
	def httpHeaders(self):
		header = self.httpHeadersStr()
		headers = {}
		for item in header.lower().split("\r\n")[1:]:
			k, v = item.split(": ")
			headers[k] = v
		return headers
