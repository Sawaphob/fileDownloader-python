import os
from os.path import isfile, join
import sys
import urllib.request as urllib2
import shutil
import tqdm
from multiprocessing.pool import ThreadPool
from urllib.parse import urlparse


def store(filename, content):
    with open(filename, 'wb') as f:
        f.writelines(content)
    stat = os.stat(filename)


def fetch_content(resp, filename):
    content = resp.readlines()
    return content

def partial_download(partial_download_input):
    url,index,start,end,path = partial_download_input
    filename = path + '_' + str(index)
    req = urllib2.Request(url)
    req.headers['Range'] = 'bytes=%d-%d' % (start,end)
    chunked_resp = urllib2.urlopen(req, timeout=10)
    content = fetch_content(chunked_resp, filename)
    store(filename, content)

def full_download(url,path):
    print('Starting full download')
    resp = urllib2.urlopen(url)
    content = fetch_content(resp, path)
    store(path, content)

def concat_file(file,dest):
    print(dest)
    with open(dest,'wb') as wfd:
        for f in file:
            with open(f,'rb') as fd:
                shutil.copyfileobj(fd, wfd)
input_url = ['ftp://speedtest:speedtest@ftp.otenet.gr/test10Mb.db','ftp://demo:password@test.rebex.net/readme.txt']
destination = '/Users/sawaphob/Desktop/'
for url in input_url:
    data = urllib2.urlopen(url)
    filename = os.path.basename(urlparse(url).path)
    print(filename)
    if data.info()['Content-Length'] is not None:
        directory = ".temp"
        current_dir = os.path.dirname(os.path.realpath(__file__))
        path = os.path.join(current_dir, directory) 
        if os.path.exists(path):
            shutil.rmtree(path)
        os.mkdir(path)
        full_path = path + '/' + filename
        content_size = int(data.info()['Content-Length'])
        partial_download_input = []
        for i in range(8):
            if (i == 7):
                partial_download_input.append((url,i,i*content_size//8,content_size,full_path))
            else:
                partial_download_input.append((url,i,i*content_size//8,((i+1)*content_size//8)-1,full_path))
        print('Connection to %s' % url)
        for _ in tqdm.tqdm(ThreadPool(9).imap_unordered(partial_download, partial_download_input), total=len(partial_download_input)):
            pass
        files = sorted([path+'/'+f for f in os.listdir(path) if isfile(join(path, f))])
        concat_file(files,destination+str(filename))
        shutil.rmtree(path)
    else:
        full_download(url,destination+str(filename))
    print('Download ' + filename + ' complete.')