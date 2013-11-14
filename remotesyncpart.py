#!/usr/bin/python

import os, sys

# http://stackoverflow.com/questions/16874598/how-do-i-calculate-the-md5-checksum-of-a-file-in-python
# Import hashlib library (md5 method is part of it)
import hashlib

import time

# http://twistedmatrix.com/trac/
# http://stackoverflow.com/questions/3488616/bandwidth-throttling-in-python
# http://stackoverflow.com/questions/13047458/bandwidth-throttling-using-twisted
# http://twistedmatrix.com/pipermail/twisted-python/2007-July/015738.html
from twisted.internet import reactor, protocol
from twisted.protocols import basic, policies
from twisted.internet.protocol import ClientFactory
from twisted.internet.defer import Deferred

# http://txt.binnyva.com/2009/01/use-dd-to-create-file-of-any-size/
# Use the DD command to create a 10 MB (10*1024*1024=10485760 bytes) size file named testfile_10MB
# dd if=/dev/zero of=big.file bs=10485760 count=1

# https://raw.github.com/mattvonrocketstein/twisted-demos/master/filesender.py
import filesender

# http://stackoverflow.com/questions/546508/how-can-i-split-a-file-in-python

# http://docs.python.org/2/library/shutil.html
import shutil

""" 
###################################
WRAPPER per basic.LineReceiver in modo da fargli mandare solo una parte del file leggendolo da un filestream
###################################
"""

# basic.LineReceiver
class myFileIOClient(filesender.FileIOClient):
	""" my file sender """
	def __init__(self, remoteFile, partNumber, controller):
		
		self.remoteFile = remoteFile
		self.partNumber = partNumber
		
		s = ("*s.part*0.%dd" % (len("%d"%(self.remoteFile.numblock,)),) ).replace("*","%")
		self.path = s % (remoteFile.filepath(),partNumber)
		self.controller = controller
		
		print "start block", self.remoteFile.startBlock(partNumber)
		
		start = self.remoteFile.startBlock(partNumber)
		stop = self.remoteFile.blockSize(partNumber)
		total = self.remoteFile.filesize
		
		fp = open(self.remoteFile.filepath(), 'rb')
		fp.seek(start)
		bin = fp.read(min(stop,total-start))
		
		class fakeFileHandler:
			bytes = None
			readed = 0
			total = 0
			def __init__(self, bytes):
				self.bytes = bytes
				self.total = len(bytes)
				self.readed = 0
			def read(self, len0):
				print "read", len0, self.readed
				ris = self.bytes[self.readed:self.readed+len0]
				self.readed = self.readed + len0
				return ris
			def readline(self):
				return self.read()
			def close(self):
				return None
			def md5(self):
				return getMD5ChecksumFromData(self.bytes)
		
		self.infile = fakeFileHandler(bin)
		self.controller.instruction['md5_part'] = self.infile.md5()
		self.controller.instruction['md5_final'] = self.remoteFile.checksum
		
		print "block length", self.remoteFile.blockSize(partNumber)
		self.insize = remoteFile.blockSize(partNumber)	#os.stat(self.path).st_size
		
		self.result = None
		self.completed = False
		
		self.controller.file_sent = 0
		self.controller.file_size = self.insize

class myClientFactory(policies.ThrottlingFactory):
	#protocol.Factory):
	def __init__(self):
		self.wrappedFactory = ClientFactory() #protocol.Factory()
		policies.ThrottlingFactory.__init__(self, self.wrappedFactory, maxConnectionCount=sys.maxint, readLimit=144, writeLimit=144)
		self.clients = set()
		#print self.checkReadBandwidth()


# basic.LineReceiver
class myFileIOClientFactory(myClientFactory): #ClientFactory):
	
    """ my file sender factory """
    protocol = myFileIOClient
    
    def __init__(self, remoteFile, partNumber, controller):
    	self.wrappedFactory = ClientFactory() #protocol.Factory()
    	#print "init"
    	#print "remoteFile", remoteFile
    	#print "partNumber", partNumber
    	#print "controller", controller
        self.remoteFile = remoteFile
        if remoteFile.startBlock(partNumber) == 0 and partNumber <> 0:
        	partNumber = 0
        self.partNumber = partNumber
        self.controller = controller
	
    def clientConnectionFailed(self, connector, reason):
    	print "clientConnectionFailed", reason
        ClientFactory.clientConnectionFailed(self, connector, reason)
        self.controller.completed.errback(reason)
	
    def buildProtocol(self, addr):
        print "building protocol"
        p = self.protocol(self.remoteFile, self.partNumber, self.controller)
        p.factory = self
        return p

""" 
###################################
WRAPPER per basic.LineReceiver in modo da fargli leggere solo una parte del file finale
###################################
"""

class myFileIOServerFactory(myClientFactory):
	
	protocol = filesender.FileIOProtocol
	
	def __init__(self, db, options={}, remoteFile=None, partNumber=0, controller=None):
		self.wrappedFactory = ClientFactory() #protocol.Factory()
		self.db = db
		self.options = options
		self.remoteFile = remoteFile
		if remoteFile.startBlock(partNumber) == 0 and partNumber <> 0:
			partNumber = 0
		self.partNumber = partNumber
		self.controller = controller
		self.receiveFile = True
	
	def clientConnectionFailed(self, connector, reason):
		print "serverConnectionFailed", reason
		ClientFactory.clientConnectionFailed(self, connector, reason)
		self.controller.completed.errback(reason)
	
	def buildProtocol(self, addr):
		print "server building protocol"
		p = self.protocol() #self.remoteFile, self.partNumber, self.controller)
		p.factory = self
		return p

# http://stackoverflow.com/questions/1094841/reusable-library-to-get-human-readable-version-of-file-size
def sizeof_fmt(num):
	for x in ['bytes','KB','MB','GB']:
		if num < 1024.0 and num > -1024.0:
			return "%3.1f%s" % (num, x)
		num /= 1024.0
	return "%3.1f%s" % (num, 'TB')

# http://stackoverflow.com/questions/16874598/how-do-i-calculate-the-md5-checksum-of-a-file-in-python
def getMD5Checksum(file_name):
	# File to check
	#file_name = 'filename.exe'
	# Correct original md5 goes here
	#original_md5 = '5d41402abc4b2a76b9719d911017c592'
	md5_returned = -1
	# Open,close, read file and calculate MD5 on its contents
	with open(file_name) as file_to_check:
		# read contents of the file
		data = file_to_check.read()
	# pipe contents of the file through
	md5_returned = hashlib.md5(data).hexdigest()
	# Finally compare original MD5 with freshly calculated
	#if orginal_md5 == md5_returned:
	#	print "MD5 verified."
	#else:
	#	print "MD5 verification failed!."
	#print md5_returned
	return md5_returned

def getMD5ChecksumFromData(data):
	md5_returned = hashlib.md5(data).hexdigest()
	return md5_returned

# http://docs.python.org/2/tutorial/classes.html
class RemoteFile:
	
	filename = None
	dirname  = None
	
	numblock = 10
	filesize = 0
	checksum = None
	
	def __init__(self, filepath):
		self.filename = os.path.basename(filepath)
		self.dirname = os.path.dirname(filepath)
		#print 'exist', self.filepath(), self.exist()
		self.filesize = self.readfilesize()
		self.checksum = self.calcchecksum()
		print "new RemoteFile(%s)" % (self,)
	
	# http://stackoverflow.com/questions/4912852/how-do-i-change-the-string-representation-of-a-python-class
	def __str__(self):
		return "file at: %s/%s [exists=%s] [filesize=%d,%s] [checksum=%s,%s]" % (self.dirname,self.filename,self.exist(), self.filesize, sizeof_fmt(self.filesize), self.checksum, self.verifyChecksum())
	
	def serialize(self):
		c = None
		if self.verifyChecksum():
			c = self.checksum
		return ( self.filepath(), self.exist(), self.filesize, c, self.numblock)
	
	def exist(self, partNumber=-1):
		return os.path.exists(self.filepath(partNumber))
		
	
	def readfilesize(self):
		if self.exist():
			# http://stackoverflow.com/questions/6591931/getting-file-size-in-python
			return os.path.getsize(self.filepath())
		return -1
	
	def startBlock(self,blockNumber):
		if blockNumber < 0 or blockNumber >= self.numblock:
			return 0
		else:
			return int( blockNumber * ( self.filesize / ( self.numblock * 1.0 ) ) )
	
	def blockSize(self,blockNumber):
		if blockNumber == self.numblock - 1:
			return int( self.filesize - self.startBlock(blockNumber) )
		else:
			return int( ( self.filesize / ( self.numblock * 1.0 ) ) )
	
	def filepath(self, partNumber=-1):
		if partNumber < 0 or partNumber >= self.numblock:
			return os.path.join(self.dirname,self.filename)
		else:
			s = ("*s.part*0.%dd" % (len("%d"%(self.numblock,)),) ).replace("*","%")
			s = s % (os.path.join(self.dirname,self.filename), partNumber)
			return s
	
	def calcchecksum(self):
		if self.exist():
			return getMD5Checksum(self.filepath())
		return -1
	
	def verifyChecksum(self, file0=None):
		if not self.exist():
			return False
		if not file0:
			file0 = self.filepath()
		if self.checksum == getMD5Checksum(file0):
			#print "MD5 verified."
			return True
		else:
			#print "MD5 verification failed!."
			return False
	
	def randomPort(self,destinationIpAddress):
		os.environ['TZ'] = 'EU/Rome'
		time.tzset()
		#print time.tzname
		#print time.strftime('%m%d%H')
		t = int(time.strftime('%m%d%H'))
		maxt = 123123
		#t = 012110
		t = int( 100 * ( t / (maxt*1.0) ) )
		#print t, maxt
		ip = destinationIpAddress.split(".")
		maxip = 255
		for i in range(len(ip)):
			ip[i] = int( 100 * ( int(ip[i]) / (maxip*1.0) ) )
		#print ip, maxip
		portfrac = ( ( 65535 - 1025 ) / 5 ) / 100.0
		port = 1025
		port += t * portfrac
		for i in range(len(ip)):
			port += ip[i] * portfrac
		#print port
		return int(port)
	
	# http://twistedmatrix.com/trac/
	class ServerProtocol(basic.LineReceiver):
		def __init__(self, factory):
			self.factory = factory
		
		def connectionMade(self):
			self.factory.clients.add(self)
		
		def connectionLost(self, reason):
			self.factory.clients.remove(self)
		
		def lineReceived(self, line):
			for c in self.factory.clients:
				c.sendLine("<{}> {}".format(self.transport.getHost(), line))
	
	class ServerFactory(policies.ThrottlingFactory):
	#protocol.Factory):
		def __init__(self):
			self.wrappedFactory = protocol.Factory()
			policies.ThrottlingFactory.__init__(self, self.wrappedFactory, maxConnectionCount=sys.maxint, readLimit=14400, writeLimit=14400)
			self.clients = set()
			#print self.checkReadBandwidth()
		
		def buildProtocol(self, addr):
			return RemoteFile.ServerProtocol(self)
	
	def receiveOnePart(self,address='127.0.0.1',port=None,outpath='/tmp',act_as_a_server=True, partNumber=-1):
		#reactor.listenTCP(port, RemoteFile.ServerFactory())
		#reactor.run()
		options = {}
		options['output_dir'] = outpath
		db = {}
		if not port:
			port = self.randomPort(address)
		if act_as_a_server:
			fileio = filesender.FileIOFactory(db=db,options=options)
			reactor.listenTCP(port, fileio)
			print 'Listening on port',port,'..'
		else:
			print "connection to", address, port
			instruction = {}
			instruction['partNumber'] = partNumber
			controller = type('test',(object,),{'cancel':False, 'total_sent':0,'completed':Deferred(),'instruction':instruction})
			fileio = myFileIOServerFactory(db, options, self, partNumber, controller)
			reactor.connectTCP(address, port, fileio)
		
		if not reactor.running:
			reactor.run()
		
		if db.has_key('md5_part') and db.has_key('new_file'):
			if getMD5Checksum(db['new_file']) != db['md5_part']:
				print 'Checksum of part', partNumber, 'is corrupted! Deleting file'
			else:
				shutil.move( db['new_file'], db['original_file'] )
		else:
			print 'wrong db?', db
		
		if act_as_a_server:
			return db
		else:
			db['controller'] = controller
			#return (dbcontroller.cancel, controller.total_sent, controller.completed)
			return db
	
	def transmitOnePart(self, address='127.0.0.1', partNumber=0, port=None,act_as_a_server=False):
		""" helper for file transmission """
		instruction = {}
		instruction['partNumber'] = partNumber
		controller = type('test',(object,),{'cancel':False, 'total_sent':0,'completed':Deferred(),'instruction':instruction})
		#print "controller", controller
		# Utilizzo il mio ClientFactory con il mio FileIOProtocol
		# in modo da mandare solo una parte del file
		f = myFileIOClientFactory(self, partNumber, controller)
		if not port:
			port = self.randomPort(address)
		if not act_as_a_server:
			print "connection to", address, port
			reactor.connectTCP(address, port, f)
		else:
			reactor.listenTCP(port, f)
			print 'Listening on port',port,'..'
		if not reactor.running:
			reactor.run()
		return (controller.cancel, controller.total_sent, controller.completed)
	
	def checkParts(self):
		for i in range(self.numblock):
			#print 'part', i, 'of', self.numblock, self.filepath(i), self.exist(i)
			if not self.exist(i):
				return False
		return True
	
	def joinParts(self):
		if self.checkParts() and not self.exist():
			cmd = "cat "
			for i in range(self.numblock):
				#print 'part', i, 'of', self.numblock, self.filepath(i), self.exist(i)
				cmd = "%s \"%s\"" % (cmd, self.filepath(i),)
			cmd = "%s >\"%s\"" % (cmd, self.filepath(),)
			#print cmd
			os.system(cmd)
		print self, self.verifyChecksum()
	
if __name__ == "__main__":
	#print sys.argv
	#exit()
	add = "192.168.1.204"
	part = 0
	file = RemoteFile("/Users/fabio/Desktop/big.file")
	if len(sys.argv) > 1 and sys.argv[1] == 'server':
		if len(sys.argv) > 2 and int(sys.argv[2])>0:
			part = int(sys.argv[2])
		db = file.receiveOnePart(address=add, act_as_a_server=False, partNumber=part)
		#print db
		#file.checkParts()
		#file.joinParts()
	else:
		if len(sys.argv) > 1 and int(sys.argv[1])>0:
			part = int(sys.argv[1])
		#port = file.randomPort('188.10.149.11')
		#print 'port', port
		#file.startServer(port)
		print file.transmitOnePart(address=add, partNumber=part, act_as_a_server=True)
	
