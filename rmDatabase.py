#!/usr/bin/python

import os, sys

# http://docs.python.org/2/library/pickle.html
import pickle, pprint

from remotesyncpart import RemoteFile

import myjson

class RMDatabase:
	
	dbpath = ""
	data = {}
	listfile = []
	ignorefiles = ['.DS_Store', 'Thumbs.db']
	
	def __init__(self, dbfile=None):
		if dbfile == None:
			dbfile = os.path.join(os.getcwd(),'db.dat')
		self.dbpath = dbfile
		self.data = {}
		self.listfile = []
		print self.dbpath
	
	def exist(self):
		return os.path.exists(self.dbpath)
	
	def open(self):
		if self.exist():
			print "## open db ", self.dbpath
			fp = open(self.dbpath, 'rb')
			self.data = pickle.load(fp)
			self.listfile = pickle.load(fp)
			#pprint.pprint(self.data)
			fp.close()
		else:
			print "Cannot open file", self.dbpath
			exit()
	
	def write(self):
		print "## write db", self.dbpath
		fp = open(self.dbpath, 'wb')
		if not fp:
			print "Cannot write file", self.dbpath
			exit()
		# Pickle dictionary using protocol 0.
		pickle.dump(self.data, fp)
		pickle.dump(self.listfile, fp)
		fp.close()
	
	def addDir(self, basedir):
		if not basedir in self.listfile:
			if os.path.exists(basedir):
				self.listfile.append(basedir)
			else:
				print "Directory", basedir, "doesn't exists!"
		if os.path.exists(basedir) and os.path.isfile(basedir):
			self.addFile(basedir)
	
	def addFile(self, filename):
		if not self.data.has_key(filename):
			print "## adding file", filename
			self.data[ filename ] = RemoteFile(filename)
	
	def addRemoteFile(self, tuple0):
		filename = tuple0[0]
		print "## adding remote file", tuple0
		self.data[ filename ] = tuple0
	
	def scanFiles(self):
		print "## scanFiles", len(self.listfile)
		for bdir in list(self.listfile):
			print "## basedir", bdir
			# http://stackoverflow.com/questions/2934281/python-os-path-walk-method
			for directory, dirnames, filenames in os.walk(bdir):
				directory = os.path.join(bdir,directory)
				#print "## subdir", directory
				#print filenames, dirnames
				for dirname in dirnames:
					if dirname in self.ignorefiles:
						#print "## ignoring directory", os.path.join(directory,dirname)
						continue
					dirname = os.path.join(directory, dirname)
					self.addDir(dirname)
				for filename in filenames:
					if filename in self.ignorefiles:
						#print "## ignoring file", os.path.join(directory,filename)
						continue
					filename = os.path.join(directory,filename)
					#print "## adding file", filename
					self.addFile(filename)
					
	def dump(self):
		pprint.pprint(self.data)
		pprint.pprint(self.listfile)
	
	def toJSON(self):
		return myjson.toJSON(self)
	
def testDb():
	#testDBFile = "/Users/fabio/.rmdb.dat"
	testDBFile = "/Users/fabio/Desktop/rmdb.dat"
	db = RMDatabase(testDBFile)
	if db.exist():
		db.open()
		pprint.pprint(db.data)
		pprint.pprint(db.listfiles)
	else:
		db.data = [1,2,'ciao']
		db.write()

def testDb2():
	testDBFile = "/Users/fabio/Desktop/rmdb.dat"
	db = RMDatabase(testDBFile)
	if db.exist():
		print "-- opening db"
		db.open()
		print "-- dumping db"
		db.dump()
	print "-- adding dir to db"
	db.addDir('/Users/fabio/Desktop/testDir')
	print "-- dumping db"
	db.dump()
	print "-- scanFile"
	db.scanFiles()
	print "-- dumping db"
	db.dump()
	print "-- writing db"
	db.write()

if __name__ == "__main__":
	testDb2()
