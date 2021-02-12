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

support_protocol = ['http','https','ftp','sftp']

def fetch_store_content(resp, filename):
    if(os.path.exists(filename)):
        os.remove(filename)
    while True:
        content = resp.readlines(1024)
        if(content == []):
            break
        with open(filename, 'ab') as f:
            f.writelines(content)

# @retry(tries=3, delay=3, backoff=2)
def partial_download(partial_download_input):
    url,index,start,end,path = partial_download_input
    filename = path + '_' + str(index)
    req = urllib2.Request(url)
    req.headers['Range'] = 'bytes=%d-%d' % (start,end)
    chunked_resp = urllib2.urlopen(req, timeout=15)
    fetch_store_content(chunked_resp, filename)

# @retry(tries=3, delay=3, backoff=2)
def full_download(url,path,filename):
    print('Starting full download '+filename)
    resp = urllib2.urlopen(url)
    fetch_store_content(resp, path)

def concat_file(file,dest):
    with open(dest,'wb') as wfd:
        for f in file:
            with open(f,'rb') as fd:
                shutil.copyfileobj(fd, wfd)

# @retry(tries=3, delay=3, backoff=2)
def downloadSFTP(parse_url,filename,des_path):
    cnopts = pysftp.CnOpts()
    cnopts.hostkeys = None
    with pysftp.Connection(parse_url.hostname,username=parse_url.username,password=parse_url.password,cnopts = cnopts) as sftp:
        print("SFTP only support full download")
        if sftp.isfile(parse_url.path):
            print('Start downloading ' + filename)
            sftp.get(parse_url.path,des_path)
            print('Download ' + filename + ' completed.')
        else:
            print(parse_url.path + ' File not found')

def remove_temp_directory(filename):
    directory = ".temp_"+filename
    current_dir = os.path.dirname(os.path.realpath(__file__))
    path = os.path.join(current_dir, directory) 
    if os.path.exists(path):
        shutil.rmtree(path)
    return path

def basic_download(url,filename,destination_path):
    try:
        data = urllib2.urlopen(url)
    except Exception as e:
        print("ERROR occur: %s \nPlease check url (%s) and try again" % (str(e),url))
        return
    if(url[:3]=='ftp'):
        print('FTP support only full download')
        full_download(url,destination_path,filename)
        print('Download ' + filename + ' completed.')
        return
    if data.info()['Content-Length'] is not None:
        try:
            path = remove_temp_directory(filename)
            os.mkdir(path)
            full_path = path + '/' + filename
            content_size = int(data.info()['Content-Length'])
            partial_download_input = []
            for i in range(8):
                if (i == 7):
                    partial_download_input.append((url,i,i*content_size//8,content_size,full_path))
                else:
                    partial_download_input.append((url,i,i*content_size//8,((i+1)*content_size//8)-1,full_path))
            for _ in progress.bar(ThreadPool(8).imap_unordered(partial_download, partial_download_input), label='Downloading '+filename,expected_size=len(partial_download_input)):
                pass
            files = sorted([path+'/'+f for f in os.listdir(path) if isfile(join(path, f))])
            concat_file(files,destination_path)
            shutil.rmtree(path)
        except Exception as e:
            print('Cannot do patial download try full download')
            full_download(url,destination_path,filename)
    else:
        print('Cannot get data content-length switch to full download')
        full_download(url,destination_path,filename)
    print('Download ' + filename + ' completed.')
    

def main_downloader(input_downloader):
    url,destination = input_downloader
    parse_url = urllib.parse.urlsplit(url)
    filename = os.path.basename(parse_url.path)
    scheme = parse_url.scheme
    if scheme in support_protocol:
        if (destination[-1] != '/'):
            destination_path = destination+'/'+filename
        else:
            destination_path = destination+filename
        try:
            if scheme == 'sftp':
                downloadSFTP(parse_url,filename,destination_path)
            else:
                basic_download(url,filename,destination_path)
        except Exception as e:
            print("ERROR occur: %s \nPlease check url (%s) and try again" % (str(e),url))
            remove_temp_directory(filename)
    else:
        print('Unsupport protocol (Application support only http,https,ftp and sftp')

if __name__ == '__main__':
    # input_url = ['sftp://demo:password@test.rebex.net/pub/example/KeyGenerator.png']
    input_url = ['ftp://speedtest:speedtest@ftp.otenet.gr/test10Mb.db','https://az764295.vo.msecnd.net/stable/8490d3dde47c57ba65ec40dd192d014fd2113496/VSCode-darwin.zip','sftp://demo:password@test.rebex.net/pub/example/KeyGenerator.png']
    destination = '/Users/SawaphobChavana/Desktop/testDownloader'
    input_downloader = []
    for url in input_url:
        input_downloader.append((url,destination))
    if (not os.path.exists(destination)):
        os.mkdir(destination)
        print('Create new directory')
    for _ in progress.bar(ThreadPool().imap_unordered(main_downloader, input_downloader),label='Overall download progress',expected_size=len(input_url)):
        pass


import unittest

class TestFetchStoreContentMethods(unittest.TestCase):

    def testfilesize(self):
        req = urllib2.Request('ftp://speedtest:speedtest@ftp.otenet.gr/test1Mb.db')
        resp = urllib2.urlopen(req, timeout=15)
        fetch_store_content(resp,'./test1Mb.db')
        self.assertEqual(int(resp.info()['Content-Length']),os.stat('./test1Mb.db').st_size)
        os.remove('./test1Mb.db')

class TestRemoveTempDirectoryMethods(unittest.TestCase):

    def testdirnotexist(self):
        test_dir = '.temp_test1'
        remove_temp_directory('test1')
        self.assertFalse(os.path.exists(test_dir))
    def testdirexist(self):
        test_dir = '.temp_test1'
        os.mkdir(test_dir)
        remove_temp_directory('test1')
        self.assertFalse(os.path.exists(test_dir))

class TestConcatMethods(unittest.TestCase):

    def testfilecontent(self):
        os.mkdir('test')
        f1 = open("test/file.txt", "wb")
        f1.write(bytes("Content from file 1", 'utf-8'))
        f1.close()
        f2 = open("test/file2.txt", "wb")
        f2.write(bytes("Content from file 2", 'utf-8'))
        f2.close()
        concat_file(["test/file.txt","test/file2.txt"],"test/file3.txt")
        f3 = open("test/file3.txt", "rb")
        self.assertEqual(f3.readline(),(bytes("Content from file 1Content from file 2", 'utf-8')))
        f3.close()
        shutil.rmtree('test')

class TestFullDownload(unittest.TestCase):

    def testfilesize_content_ftp(self):
        url = 'ftp://speedtest:speedtest@ftp.otenet.gr/test1Mb.db'
        req = urllib2.Request(url)
        resp = urllib2.urlopen(req, timeout=15)
        full_download(url,'./test1Mb-ftp.db','test1Mb-ftp.db')
        self.assertEqual(int(resp.info()['Content-Length']),os.stat('./test1Mb-ftp.db').st_size)
        test_material = open("test_material/test1Mb.db", "rb")
        actual_file = open("test1Mb-ftp.db", "rb")
        self.assertEqual(test_material.readlines(),actual_file.readlines())
        test_material.close()
        actual_file.close()
        os.remove('./test1Mb-ftp.db')
    def testfilesize_content_http(self):
        url = 'http://speedtest.ftp.otenet.gr/files/test1Mb.db'
        req = urllib2.Request(url)
        resp = urllib2.urlopen(req, timeout=15)
        full_download(url,'./test1Mb-http.db','test1Mb-http.db')
        self.assertEqual(int(resp.info()['Content-Length']),os.stat('./test1Mb-http.db').st_size)
        test_material = open("test_material/test1Mb.db", "rb")
        actual_file = open("test1Mb-http.db", "rb")
        self.assertEqual(test_material.readlines(),actual_file.readlines())
        test_material.close()
        actual_file.close()
        os.remove('./test1Mb-http.db')

class TestSFTPDownload(unittest.TestCase):

    def testfile_content_sftp(self):
        url = 'sftp://demo:password@test.rebex.net/pub/example/KeyGenerator.png'
        parse_url = urllib.parse.urlsplit(url)
        filename = os.path.basename(parse_url.path)
        downloadSFTP(parse_url,filename,'KeyGenerator.png')
        test_material = open("test_material/KeyGenerator.png", "rb")
        actual_file = open("KeyGenerator.png", "rb")
        self.assertEqual(test_material.readlines(),actual_file.readlines())
        test_material.close()
        actual_file.close()
        os.remove('KeyGenerator.png')
    def testfilenotfound(self):
        capturedOutput = io.StringIO()       
        sys.stdout = capturedOutput                
        url = 'sftp://demo:password@test.rebex.net/pub/example/KeyGenerators.png'
        parse_url = urllib.parse.urlsplit(url)
        filename = os.path.basename(parse_url.path)
        downloadSFTP(parse_url,filename,'KeyGenerators.png')               
        sys.stdout = sys.__stdout__       
        self.assertEqual('SFTP only support full download\n/pub/example/KeyGenerators.png File not found\n',capturedOutput.getvalue())
        
class TestPartialDownload(unittest.TestCase):

    def testfilesize_content_http(self):
        url = 'http://speedtest.ftp.otenet.gr/files/test1Mb.db'
        test_input = (url,0,0,1023,'test1Mb.db-http')
        partial_download(test_input)
        self.assertTrue(os.path.exists('test1Mb.db-http_0'))
        self.assertEqual(1024,os.stat('test1Mb.db-http_0').st_size)
        os.remove('./test1Mb.db-http_0')

class TestBasicDownload(unittest.TestCase):

    def test_raise_exception(self):
        url = 'http://speedtest.ftp.otenet.gr/files/test1Mb.db1'
        capturedOutput = io.StringIO()       
        sys.stdout = capturedOutput   
        basic_download(url,'test1Mb.db','./test1Mb.db1')                          
        sys.stdout = sys.__stdout__   
        self.assertEqual('ERROR occur: HTTP Error 404: Not Found \nPlease check url (http://speedtest.ftp.otenet.gr/files/test1Mb.db1) and try again\n',capturedOutput.getvalue())

    def test_full_download(self): 
        url = 'ftp://demo:password@test.rebex.net/pub/example/KeyGenerator.png'
        capturedOutput = io.StringIO()       
        sys.stdout = capturedOutput   
        basic_download(url,'KeyGenerator.png','./KeyGenerator.png')                          
        sys.stdout = sys.__stdout__   
        self.assertEqual('FTP support only full download\nStarting full download KeyGenerator.png\nDownload KeyGenerator.png completed.\n',capturedOutput.getvalue())

    def test_partial_download(self): 
        url = 'http://speedtest.ftp.otenet.gr/files/test1Mb.db'
        req = urllib2.Request(url)
        resp = urllib2.urlopen(req, timeout=15)
        basic_download(url,'test1Mb.db-par','./test1Mb.db-par')
        self.assertEqual(int(resp.info()['Content-Length']),os.stat('./test1Mb.db-par').st_size)
        test_material = open("test_material/test1Mb.db", "rb")
        actual_file = open("test1Mb.db-par", "rb")
        self.assertEqual(test_material.readlines(),actual_file.readlines())
        test_material.close()
        actual_file.close()
        os.remove('./test1Mb.db-par')

class TestMainDownload(unittest.TestCase):
    def test_not_support_scheme(self):
        url = 'ftps://demo:password@test.rebex.net/pub/example/KeyGenerator.png'
        destination = os.path.dirname(os.path.realpath(__file__))
        capturedOutput = io.StringIO()       
        sys.stdout = capturedOutput   
        main_downloader((url,destination))                          
        sys.stdout = sys.__stdout__   
        self.assertEqual('Unsupport protocol (Application support only http,https,ftp and sftp\n',capturedOutput.getvalue())
    def test_sftp(self):
        url = 'sftp://demo:password@test.rebex.net/pub/example/KeyGenerator.png'
        destination = os.path.dirname(os.path.realpath(__file__))+'/'
        capturedOutput = io.StringIO()
        sys.stdout = capturedOutput   
        main_downloader((url,destination))                          
        sys.stdout = sys.__stdout__   
        self.assertEqual('SFTP only support full download\nStart downloading KeyGenerator.png\nDownload KeyGenerator.png completed.\n',capturedOutput.getvalue())
        os.remove(destination+"KeyGenerator.png")
    def test_basic(self):
        url = 'http://speedtest.ftp.otenet.gr/files/test1Mb.db'
        destination = os.path.dirname(os.path.realpath(__file__))
        req = urllib2.Request(url)
        resp = urllib2.urlopen(req, timeout=15)
        main_downloader((url,destination))
        self.assertEqual(int(resp.info()['Content-Length']),os.stat('test1Mb.db').st_size)
        test_material = open("test_material/test1Mb.db", "rb")
        actual_file = open("test1Mb.db", "rb")
        self.assertEqual(test_material.readlines(),actual_file.readlines())
        test_material.close()
        actual_file.close()
        os.remove('test1Mb.db')