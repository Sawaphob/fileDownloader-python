import os
from os.path import isfile, join
import sys
import urllib.request as urllib2
import urllib
import shutil
from multiprocessing.pool import ThreadPool
import urllib.parse
import pysftp
import socket
from clint.textui import progress
from retry import retry
import io
from abc import ABC, abstractmethod

support_protocol = ['http','https','ftp','sftp']

class Downloader(ABC):
    @abstractmethod
    def download(self,url,filename,destination_path):
        pass
    def remove_temp_directory(self,filename):
        directory = ".temp_"+filename
        current_dir = os.path.dirname(os.path.realpath(__file__))
        path = os.path.join(current_dir, directory) 
        if os.path.exists(path):
            shutil.rmtree(path)
        return path
    def concat_file(self,file,dest):
        with open(dest,'wb') as wfd:
            for f in file:
                with open(f,'rb') as fd:
                    shutil.copyfileobj(fd, wfd)

class HTTPDownloader(Downloader):
    def download(self,url,filename,destination_path):
        try:
            data = urllib2.urlopen(url)
        except Exception as e:
            print("ERROR occur: %s \nPlease check url (%s) and try again" % (str(e),url))
            return
        if data.info()['Content-Length'] is not None:
            try:
                path = super().remove_temp_directory(filename)
                os.mkdir(path)
                full_path = path + '/' + filename
                content_size = int(data.info()['Content-Length'])
                partial_download_input = []
                for i in range(8):
                    if (i == 7):
                        partial_download_input.append((url,i,i*content_size//8,content_size,full_path))
                    else:
                        partial_download_input.append((url,i,i*content_size//8,((i+1)*content_size//8)-1,full_path))
                for _ in progress.bar(ThreadPool(8).imap_unordered(self.partial_download, partial_download_input), label='Downloading '+filename,expected_size=len(partial_download_input)):
                    pass
                files = sorted([path+'/'+f for f in os.listdir(path) if isfile(join(path, f))])
                self.concat_file(files,destination_path)
                shutil.rmtree(path)
            except Exception as e:
                print('Cannot do patial download try full download')
                self.full_download(url,filename,destination_path)
        else:
            print('Cannot get data content-length switch to full download')
            self.full_download(url,filename,destination_path)
        print('Download ' + filename + ' completed.')

    def fetch_store_content(self,resp, filename):
        if(os.path.exists(filename)):
            os.remove(filename)
        while True:
            content = resp.read(1024)
            if(content == b''):
                break
            with open(filename, 'ab') as f:
                f.write(content)
    
    @retry(tries=3, delay=3, backoff=2)
    def partial_download(self,partial_download_input):
        url,index,start,end,path = partial_download_input
        filename = path + '_' + str(index)
        req = urllib2.Request(url)
        req.headers['Range'] = 'bytes=%d-%d' % (start,end)
        chunked_resp = urllib2.urlopen(req, timeout=15)
        self.fetch_store_content(chunked_resp, filename)

    @retry(tries=3, delay=3, backoff=2)
    def full_download(self,url,filename,destination_path):
        print('Starting full download '+filename)
        resp = urllib2.urlopen(url)
        self.fetch_store_content(resp, destination_path)

class FTPDownloader(HTTPDownloader):
    def download(self,url,filename,destination_path):
        try:
            data = urllib2.urlopen(url)
        except Exception as e:
            print("ERROR occur: %s \nPlease check url (%s) and try again" % (str(e),url))
            return
        print('FTP support only full download')
        super().full_download(url,filename,destination_path)
        print('Download ' + filename + ' completed.')

class SFTPDownloader(Downloader):
    @retry(tries=3, delay=3, backoff=2)
    def download(self,url,filename,destination_path):
        parse_url = urllib.parse.urlsplit(url)
        cnopts = pysftp.CnOpts()
        cnopts.hostkeys = None
        with pysftp.Connection(parse_url.hostname,username=parse_url.username,password=parse_url.password,cnopts = cnopts) as sftp:
            print("SFTP only support full download")
            if sftp.isfile(parse_url.path):
                print('Start downloading ' + filename)
                sftp.get(parse_url.path,destination_path)
                print('Download ' + filename + ' completed.')
            else:
                print(parse_url.path + ' File not found')

def main_downloader(input_downloader):
    downloader,url,destination,filename = input_downloader
    if (destination[-1] != '/'):
        destination_path = destination+'/'+filename
    else:
        destination_path = destination+filename
    try:
        downloader.download(url,filename,destination_path)
    except Exception as e:
        print("ERROR occur: %s \nPlease check url (%s) and try again" % (str(e),url))
        downloader.remove_temp_directory(filename)
        if os.path.exists(destination_path):
            os.remove(destination_path)

if __name__ == '__main__':
    input_url = sys.argv[1].strip().split(',')
    destination = sys.argv[2]
    input_downloader = []
    for url in input_url:
        parse_url = urllib.parse.urlsplit(url)
        filename = os.path.basename(parse_url.path)
        scheme = parse_url.scheme
        if scheme in support_protocol:
            if scheme == 'http' or scheme == 'https':
                input_downloader.append((HTTPDownloader(),url,destination,filename))
            elif scheme == 'ftp':
                input_downloader.append((FTPDownloader(),url,destination,filename))
            elif scheme == 'sftp':
                input_downloader.append((SFTPDownloader(),url,destination,filename))
        else:
            print('Unsupport protocol (Application support only http,https,ftp and sftp')
    if (not os.path.exists(destination)):
        os.mkdir(destination)
        print('Create new directory')
    for _ in progress.bar(ThreadPool().imap_unordered(main_downloader, input_downloader),label='Overall download progress',expected_size=len(input_url)):
        pass


import unittest

class TestFetchStoreContentMethods(unittest.TestCase):

    def testfilesize(self):
        downloader = FTPDownloader()
        req = urllib2.Request('ftp://speedtest:speedtest@ftp.otenet.gr/test1Mb.db')
        resp = urllib2.urlopen(req, timeout=15)
        downloader.fetch_store_content(resp,'./test1Mb.db')
        self.assertEqual(int(resp.info()['Content-Length']),os.stat('./test1Mb.db').st_size)
        os.remove('./test1Mb.db')

class TestRemoveTempDirectoryMethods(unittest.TestCase):
    def testdirnotexist(self):
        downloader = HTTPDownloader()
        test_dir = '.temp_test1'
        downloader.remove_temp_directory('test1')
        self.assertFalse(os.path.exists(test_dir))
    def testdirexist(self):
        downloader = HTTPDownloader()
        test_dir = '.temp_test1'
        os.mkdir(test_dir)
        downloader.remove_temp_directory('test1')
        self.assertFalse(os.path.exists(test_dir))

class TestConcatMethods(unittest.TestCase):
    def testfilecontent(self):
        downloader = HTTPDownloader()
        os.mkdir('test')
        f1 = open("test/file.txt", "wb")
        f1.write(bytes("Content from file 1", 'utf-8'))
        f1.close()
        f2 = open("test/file2.txt", "wb")
        f2.write(bytes("Content from file 2", 'utf-8'))
        f2.close()
        downloader.concat_file(["test/file.txt","test/file2.txt"],"test/file3.txt")
        f3 = open("test/file3.txt", "rb")
        self.assertEqual(f3.readline(),(bytes("Content from file 1Content from file 2", 'utf-8')))
        f3.close()
        shutil.rmtree('test')

class TestFullDownload(unittest.TestCase):

    def testfilesize_content_ftp(self):
        downloader = FTPDownloader() 
        url = 'ftp://speedtest:speedtest@ftp.otenet.gr/test1Mb.db'
        req = urllib2.Request(url)
        resp = urllib2.urlopen(req, timeout=15)
        downloader.full_download(url,'test1Mb-ftp.db','./test1Mb-ftp.db')
        self.assertEqual(int(resp.info()['Content-Length']),os.stat('./test1Mb-ftp.db').st_size)
        test_material = open("test_material/test1Mb.db", "rb")
        actual_file = open("test1Mb-ftp.db", "rb")
        self.assertEqual(test_material.readlines(),actual_file.readlines())
        test_material.close()
        actual_file.close()
        os.remove('./test1Mb-ftp.db')
    def testfilesize_content_http(self):
        downloader = HTTPDownloader() 
        url = 'http://speedtest.ftp.otenet.gr/files/test1Mb.db'
        req = urllib2.Request(url)
        resp = urllib2.urlopen(req, timeout=15)
        downloader.full_download(url,'test1Mb-http.db','./test1Mb-http.db')
        self.assertEqual(int(resp.info()['Content-Length']),os.stat('./test1Mb-http.db').st_size)
        test_material = open("test_material/test1Mb.db", "rb")
        actual_file = open("test1Mb-http.db", "rb")
        self.assertEqual(test_material.readlines(),actual_file.readlines())
        test_material.close()
        actual_file.close()
        os.remove('./test1Mb-http.db')

class TestSFTPDownload(unittest.TestCase):
    def testfile_content_sftp(self):
        downloader = SFTPDownloader()
        url = 'sftp://demo:password@test.rebex.net/pub/example/KeyGenerator.png'
        parse_url = urllib.parse.urlsplit(url)
        filename = os.path.basename(parse_url.path)
        downloader.download(url,filename,'KeyGenerator.png')
        test_material = open("test_material/KeyGenerator.png", "rb")
        actual_file = open("KeyGenerator.png", "rb")
        self.assertEqual(test_material.readlines(),actual_file.readlines())
        test_material.close()
        actual_file.close()
        os.remove('KeyGenerator.png')
    def testfilenotfound(self):
        downloader = SFTPDownloader()
        capturedOutput = io.StringIO()       
        sys.stdout = capturedOutput                
        url = 'sftp://demo:password@test.rebex.net/pub/example/KeyGenerators.png'
        parse_url = urllib.parse.urlsplit(url)
        filename = os.path.basename(parse_url.path)
        downloader.download(url,filename,'KeyGenerators.png')               
        sys.stdout = sys.__stdout__       
        self.assertEqual('SFTP only support full download\n/pub/example/KeyGenerators.png File not found\n',capturedOutput.getvalue())
        
class TestPartialDownload(unittest.TestCase):
    def testfilesize_content_http(self):
        downloader = HTTPDownloader()
        url = 'http://speedtest.ftp.otenet.gr/files/test1Mb.db'
        test_input = (url,0,0,1023,'test1Mb.db-http')
        downloader.partial_download(test_input)
        self.assertTrue(os.path.exists('test1Mb.db-http_0'))
        self.assertEqual(1024,os.stat('test1Mb.db-http_0').st_size)
        os.remove('./test1Mb.db-http_0')

class TestMainDownload(unittest.TestCase):

    def test_raise_exception_http(self):
        downloader = HTTPDownloader()
        url = 'http://speedtest.ftp.otenet.gr/files/test1Mb.db1'
        capturedOutput = io.StringIO()       
        sys.stdout = capturedOutput   
        main_downloader((downloader,url,'.','test1Mb.db1'))                          
        sys.stdout = sys.__stdout__   
        self.assertEqual('ERROR occur: HTTP Error 404: Not Found \nPlease check url (http://speedtest.ftp.otenet.gr/files/test1Mb.db1) and try again\n',capturedOutput.getvalue())
    
    def test_raise_exception_ftp(self):
        downloader = FTPDownloader()
        url = 'ftp://speedtest.ftp.otenet.gr1/files/test1Mb.db'
        capturedOutput = io.StringIO()       
        sys.stdout = capturedOutput   
        main_downloader((downloader,url,'.','test1Mb.db1'))                          
        sys.stdout = sys.__stdout__   
        self.assertEqual('ERROR occur: <urlopen error [Errno 8] nodename nor servname provided, or not known> \nPlease check url (ftp://speedtest.ftp.otenet.gr1/files/test1Mb.db) and try again\n',capturedOutput.getvalue())
    
    def test_raise_exception(self):
        downloader = SFTPDownloader()
        url = 'sftp://demos:password@test.rebex.net/pub/example/KeyGenerator.png'
        capturedOutput = io.StringIO()       
        sys.stdout = capturedOutput   
        main_downloader((downloader,url,'.','KeyGenerator.png'))                          
        sys.stdout = sys.__stdout__   
        self.assertEqual('ERROR occur: Authentication failed. \nPlease check url (sftp://demos:password@test.rebex.net/pub/example/KeyGenerator.png) and try again\n',capturedOutput.getvalue())

    def test_full_download(self): 
        downloader = FTPDownloader()
        url = 'ftp://demo:password@test.rebex.net/pub/example/KeyGenerator.png'
        capturedOutput = io.StringIO()       
        sys.stdout = capturedOutput   
        main_downloader((downloader,url,'.','KeyGenerator.png'))                          
        sys.stdout = sys.__stdout__   
        self.assertEqual('FTP support only full download\nStarting full download KeyGenerator.png\nDownload KeyGenerator.png completed.\n',capturedOutput.getvalue())

    def test_partial_download(self): 
        downloader = HTTPDownloader()
        url = 'http://speedtest.ftp.otenet.gr/files/test1Mb.db'
        req = urllib2.Request(url)
        resp = urllib2.urlopen(req, timeout=15)
        main_downloader((downloader,url,'./','test1Mb.db'))
        self.assertEqual(int(resp.info()['Content-Length']),os.stat('./test1Mb.db').st_size)
        test_material = open("test_material/test1Mb.db", "rb")
        actual_file = open("test1Mb.db", "rb")
        self.assertEqual(test_material.readlines(),actual_file.readlines())
        test_material.close()
        actual_file.close()
        os.remove('./test1Mb.db')