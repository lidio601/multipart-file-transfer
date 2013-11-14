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

import myjson

class controlClient:
        dbpath = '/Users/fabio/Desktop/rmdb.local.dat'
        db = None
        remotedbpath = '/Users/fabio/Desktop/rmdb.remote_local.dat'
        remotedb = None
        dirindex = 0
        fileindex = 0
        filecount = 100

        def __init__(self):
                print '-- init', self
                self.db = RMDatabase(self.dbpath)
                if self.db.exist():
                        self.db.open()
                self.remotedb = RMDatabase(self.remotedbpath)

        # https://twistedmatrix.com/documents/12.0.0/core/howto/ssl.html
        class EchoClient(protocol.Protocol):

                def connectionMade(self):
                        self.lastCmd = "list"
                        print "-- Sending", self.lastCmd
                        #self.transport.write("hello, world!")
                        self.transport.write(self.lastCmd)
                
                def dataReceived(self, data):
                        print "-- Server said:", data
                        #self.transport.loseConnection()
                        
                        if self.lastCmd.startswith("list"):
                                self.lastCmd = None
                                #print 'list'
                                list = myjson.parseJSON(data)
                                for dir in list:
                                        print dir
                                        self.factory.client.db.addDir(dir)
                                
                                self.factory.client.db.scanFiles()

                                self.factory.client.dirindex = 0
                                self.factory.client.fileindex = 0
				
                                self.lastCmd = "get_files ('%s',%d,%d)" % ( self.factory.client.db.listfile[self.factory.client.dirindex], self.factory.client.fileindex, self.factory.client.filecount ) 
                                print "-- Sending", self.lastCmd
                                #self.transport.write("hello, world!")
                                self.transport.write(self.lastCmd)
                        
                        elif self.lastCmd.startswith("get_files"):
                            
                            (nextIndex,filelist) = myjson.parseJSON(data)
                            
                            for file in filelist:
                                self.factory.client.remotedb.addRemoteFile(file)

                                if nextIndex < 0:
                                	self.factory.client.dirindex = self.factory.client.dirindex + 1
	
                                	if self.factory.client.dirindex < len(self.factory.client.db.listfile):
                                		self.lastCmd = "get_files ('%s',%d,%d)" % ( self.factory.client.db.listfile[self.factory.client.dirindex], self.factory.client.fileindex, self.factory.client.filecount ) 
                                		print "-- Sending", self.lastCmd
                                		#self.transport.write("hello, world!")
                                		self.transport.write(self.lastCmd)
                                	else:
                                		print ""
                                		print "Finished downloading remote file list"
                                		self.lastCmd = "compare_files"
                                		data = "start"
                                else:
                                	self.factory.client.fileindex = newIndex
	
                                	self.lastCmd = "get_files ('%s',%d,%d)" % ( self.factory.client.db.listfile[self.factory.client.dirindex], self.factory.client.fileindex, self.factory.client.filecount ) 
                                	print "-- Sending", self.lastCmd
                                	#self.transport.write("hello, world!")
                                	self.transport.write(self.lastCmd)

                        if self.lastCmd.startswith("get_file_part"):
                        	print "-- Receiving file part", self.lastCmd
	       	
                        	rfilename = self.factory.client.remotedb.data.keys()[ self.factory.client.fileindex ]
                        	rfileinfo = self.factory.client.remotedb.data[rfilename]
                        	lfileinfo = None
	
                        	#print self.factory.client.db, self.factory.client.remotedb
                        	#self.factory.client.db.data[0] = 'ciao'
                        	#print ""
                        	#self.factory.client.db.dump()
                        	#print ""
                        	#self.factory.client.remotedb.dump()
	
                        	if self.factory.client.db.data.has_key(rfilename):
                        		lfileinfo = self.factory.client.db.data[rfilename]
	
                        	if not lfileinfo:
                        		print '-- File', rfilename, "doesnt' exists!"
                        		lfileinfo = RemoteFile(rfilename)
                        		lfileinfo.filesize = rfileinfo.filesize
                        		lfileinfo.numblock = rfileinfo.numblock
                        		lfileinfo.checksum = rfileinfo.checksum
	
                        	print lfileinfo
                        	if lfileinfo:
                        		lfileinfo.receiveOnePart(address=self.transport.getHost().host, act_as_a_server=False, partNumber= self.factory.client.fileindex)
            	
            
                        if self.lastCmd.startswith("compare_files"):
                            
                            if data == "start":
                                self.factory.client.fileindex = 0

                            while True:
                            	if self.factory.client.fileindex >= len(self.factory.client.remotedb.data.keys()):
                            		print ""
                            		print "-- Finished downloading remote files!!!"
                            		self.lastCmd = None
                            		self.transport.loseConnection()
                            		return True
	
                            	rfilename = self.factory.client.remotedb.data.keys()[ self.factory.client.fileindex ]
                            	rfileinfo = self.factory.client.remotedb.data[rfilename]
                            	lfileinfo = None
	
                            	#print self.factory.client.db, self.factory.client.remotedb
                            	#self.factory.client.db.data[0] = 'ciao'
                            	#print ""
                            	#self.factory.client.db.dump()
                            	#print ""
                            	#self.factory.client.remotedb.dump()
	
                            	if self.factory.client.db.data.has_key(rfilename):
                            		lfileinfo = self.factory.client.db.data[rfilename]
	
                            	if not lfileinfo:
                            		print '-- File', rfilename, "doesnt' exists!"
                            		lfileinfo = RemoteFile(rfilename)
                            		lfileinfo.filesize = rfileinfo.filesize
                            		lfileinfo.numblock = rfileinfo.numblock
                            		lfileinfo.checksum = rfileinfo.checksum
	
                            	print 'Remote filename to sync', rfilename
                            	print 'Remote file info', rfileinfo
                            	print 'Local file info ', lfileinfo
	
                            	if False and lfileinfo.exist() and rfileinfo[3] == lfileinfo.checksum and lfileinfo.verifyChecksum():
                            		print "Checksum confirms, file synchronized!!!"
                            	else:
                            		print "File to synchronize !!!"
                            		for part in range(0,lfileinfo.numblock):
                            			print part, '/', lfileinfo.numblock, lfileinfo.filepath(part)
                            			if not os.path.exists( lfileinfo.filepath(part) ):
                            				self.lastCmd = "get_file_part ('%s',%d)" % ( lfileinfo.filepath(), part) 
                            				print "-- Sending", self.lastCmd
                            				#self.transport.write("hello, world!")
                            				self.transport.write(self.lastCmd)
                            				return
	
                            	self.factory.client.fileindex = self.factory.client.fileindex + 1
	
                            	self.transport.loseConnection()
                            	break
    
    class EchoClientFactory(protocol.ClientFactory):

        protocol = 0
        client = 0

        def __init__(self, client):
            self.client = client
            self.protocol = self.client.EchoClient

        def clientConnectionFailed(self, connector, reason):
            print "Connection failed - goodbye!"
            #if reactor.running:
            #	reactor.stop()

        def clientConnectionLost(self, connector, reason):
            print "Connection lost - goodbye!"
            #if reactor.running:
            #	reactor.stop()
    
    # https://twistedmatrix.com/documents/12.0.0/core/howto/ssl.html
    def startClient(self, addr='localhost', port=8000):
        factory = self.EchoClientFactory(self)
        reactor.connectSSL(addr, port, factory, ssl.ClientContextFactory())
        reactor.run()

if __name__ == "__main__":
    cc = controlClient()
    cc.startClient('192.168.1.204',1027)
