#!/usr/bin/python

import os, sys

# http://docs.python.org/2/library/pickle.html
import pickle, pprint

from remotesyncpart import RemoteFile
from rmDatabase import RMDatabase

# http://twistedmatrix.com/documents/current/core/howto/book.pdf
from twisted.internet import reactor, protocol
from twisted.protocols import basic

# https://twistedmatrix.com/documents/12.0.0/core/howto/ssl.html
from twisted.internet import ssl

# http://www.thegeekstuff.com/2009/07/linux-apache-mod-ssl-generate-key-csr-crt-file/
# openssl genrsa -des3 -out server.key 4096
# http://www.mnxsolutions.com/apache/removing-a-passphrase-from-an-ssl-key.html
# openssl rsa -in server.key -out server.open.key
server_key = 'keys/server.open.key'
# openssl req -new -key server.key -out server.csr
# openssl x509 -req -days 965 -in server.csr -signkey server.key -out server.crt
server_crt = 'keys/server.crt'

# http://stackoverflow.com/questions/2343535/easiest-way-to-serialize-a-simple-class-object-with-simplejson
import myjson

class controlServer:
	
	dbpath = '/Users/fabio/Desktop/rmdb.dat'
	db = None
	list_sended_file = []
	
	def __init__(self):
	    print '-- init', self
	    self.db = RMDatabase(self.dbpath)
	    if self.db.exist():
	        self.db.open()
	
	def getCmd(self,str0):
	    str1 = str0.lower()
	    cmd_list = ('list', 'get_files', 'get_file_part')
	    ris = (None, str0)
	    for cmd in cmd_list:
	        if len(str1) >= len(cmd) and str1[0:len(cmd)] == cmd:
	            ris = (cmd, str(str0[len(cmd):]).strip(' ').strip('\t').strip('\r').strip('\n'))
	            return ris
	    return ris
	
	def list(self, arg):
		print '-- list(', arg, ')'
		if not arg or len(arg) == 0:
			return self.db.listfile
	
	def newClient(self):
		self.list_sended_file = []
	
	def getFiles(self, args):
		(bdir, findex, flength) = args
		bdir = bdir.lower()
		ris = []
		fileCount = 0
		for filename in self.db.data.keys():
			#print filename, '><', bdir
			if filename.lower().startswith(bdir):
				if fileCount < findex:
					fileCount = fileCount + 1
				elif not filename in self.list_sended_file:
					#print filename
					#ris.append(str(self.db.data[filename]))
					ris.append(self.db.data[filename].serialize())
					self.list_sended_file.append(filename)
			if len(ris) >= flength:
				break
		print 'files', len(ris)
		print ris
		nextIndex = -1
		if len(ris) >= flength:
			nextIndex = findex + flength
		return (nextIndex, ris)
	
	def getFilePart(self, args):
		print args
		(filename, part) = args
		fr = None
		if part < 0:
			return None
		#print self.db.data.keys()
		if not self.db.data.has_key(filename):
			return None
		fr = self.db.data[filename]
		print fr
		if part >= fr.numblock:
			return None
		print '-- sending file', filename, 'part', part
		return True
	
	def isAllowedIp(self, addr):
		allowed = ["127.0.0.1","192.168.1.204"]
		#print addr, allowed
		# http://twistedmatrix.com/documents/10.0.0/api/twisted.internet.address.IPv4Address.html
		if addr.host in allowed:
			return True
		return False
	
	class controlServerProtocolFake(basic.LineReceiver):
		def connectionMade(self):
			self.transport.loseConnection()
		def dataReceived(self, data):
			self.transport.loseConnection()
		#def connectionLost(self, reason):
		#	
	
	class controlServerProtocol(basic.LineReceiver):
		
		server = 0
		
		def __init__(self, factory, server):
			self.factory = factory
			self.server  = server
		
		def connectionMade(self):
			print 'connection Made'
			self.factory.clients.add(self)
			self.server.newClient()
		
		def dataReceived(self, data):
			#print """As soon as any data is received, write it back."""
			#print data
			#self.transport.write(data)
			self.doWork(data)
		
		def connectionLost(self, reason):
			self.factory.clients.remove(self)
		
		def lineReceived(self, line):
			self.doWork(line)
		
		def doWork(self, line):
			for c in self.factory.clients:
				print "<{}> {}".format(self.transport.getHost(), line)
				#c.sendLine("<{}> {}".format(self.transport.getHost(), line))
				(cmd,line) = self.server.getCmd(line)
				if cmd:
					#c.sendLine("<{}> command {} line {}".format(self.transport.getHost(), cmd, line))
					print 'Command', cmd, 'Arguments', line
					if cmd == 'list':
						ris = self.server.list(line)
						ris = myjson.toJSON(ris)
						c.sendLine(ris)
					elif cmd == 'get_files':
						ris = self.server.getFiles(eval(line))
						ris = myjson.toJSON(ris)
						c.sendLine(ris)
					elif cmd == 'get_file_part':
						ris = self.server.getFilePart(eval(line))
						str0 = myjson.toJSON(ris)
						c.sendLine(str0)
						if ris:
							args = eval(line)
							filename = args[0]
							part = args[1]
							file = self.server.db.data[filename]
							print file.transmitOnePart(address=self.transport.getHost().host, partNumber=part, act_as_a_server=True)
				else:
					self.transport.loseConnection()
				break
		
		def toJSON(self):
			return myjson.toJSON(self)
	
	class controlServerFactory(protocol.Factory):
		server = 0
		
		def __init__(self,server):
			print 'controlServerFactory', self, 'init'
			self.server = server
			self.clients = set()
		
		def toJSON(self):
			return myjson.toJSON(self)
		
		def buildProtocol(self, addr):
			print "controlServerFactory new client connected with remote address", addr
			# http://stackoverflow.com/questions/1273297/python-twisted-restricting-access-by-ip-address
			#if addr.host == "127.0.0.1":
			#    return ServerFactory.buildProtocol(self, addr)
			if len(self.clients) > 0:
				return self.server.controlServerProtocolFake()
			if self.server.isAllowedIp(addr):
				return self.server.controlServerProtocol(self, self.server)
			return self.server.controlServerProtocolFake()
	
	def startServer(self, portNumber=1027):
		print "-- starting server at port", portNumber 
		reactor.listenTCP(portNumber, self.controlServerFactory(self))
		reactor.run()
	
	def startSSLServer(self, portNumber=1027):
		print "-- starting SSL server at port", portNumber 
		reactor.listenSSL(portNumber, self.controlServerFactory(self), ssl.DefaultOpenSSLContextFactory(server_key, server_crt))
		reactor.run()
	
	def stopServer(self):
		print "-- stopping server"
		reactor.stop()

if __name__ == "__main__":
	cs = controlServer()
	if not cs.db.exist() or True:
		cs.db.addDir('/Users/fabio/Desktop/testDir')
		cs.db.addDir('/Users/fabio/Desktop/big.file')
		cs.db.scanFiles()
	else:
		cs.db.dump()
	#cs.startServer()
	cs.startSSLServer()
	cs.db.write()
	cs.db.dump()
