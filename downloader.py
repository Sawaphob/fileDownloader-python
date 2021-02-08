import os
from os.path import isfile, join
import sys
import urllib.request as urllib2
import shutil
import tqdm
from multiprocessing.pool import ThreadPool
import urllib.parse
import pysftp

support_protocol = ['http','https','ftp','sftp']

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
    with open(dest,'wb') as wfd:
        for f in file:
            with open(f,'rb') as fd:
                shutil.copyfileobj(fd, wfd)

def downloadSFTP(parse_url,des_path):
    cnopts = pysftp.CnOpts()
    cnopts.hostkeys = None
    with pysftp.Connection(parse_url.hostname,username=parse_url.username,password=parse_url.password,cnopts = cnopts) as sftp:
        if sftp.isfile(parse_url.path):
            sftp.get(parse_url.path,des_path)
            print('Download ' + filename + ' completed.')
        else:
            print(parse_url.path + ' File not found')

def basic_download(url,filename,destination_path):
    data = urllib2.urlopen(url)
    if data.info()['Content-Length'] is not None:
        directory = ".temp_"+filename
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
        for _ in tqdm.tqdm(ThreadPool(8).imap_unordered(partial_download, partial_download_input), total=len(partial_download_input)):
            pass
        files = sorted([path+'/'+f for f in os.listdir(path) if isfile(join(path, f))])
        concat_file(files,destination_path)
        shutil.rmtree(path)
    else:
        print('Cannot get data content-length switch to full download')
        full_download(url,destination_path)
    print('Download ' + filename + ' completed.')

def main_downloader(url):
    parse_url = urllib.parse.urlsplit(url)
    filename = os.path.basename(parse_url.path)
    scheme = parse_url.scheme
    if scheme in support_protocol:
        if (destination[-1] != '/'):
            destination_path = destination+'/'+filename
        else:
            destination_path = destination+filename
        if scheme == 'sftp':
            downloadSFTP(parse_url,destination_path)
        else:
            basic_download(url,filename,destination_path)
            
    else:
        print('Unsupport protocol (Application support only http,https,ftp and sftp')
input_url = ['ftp://speedtest:speedtest@ftp.otenet.gr/test10Mb.db','https://az764295.vo.msecnd.net/stable/8490d3dde47c57ba65ec40dd192d014fd2113496/VSCode-darwin.zip','sftp://demo:password@test.rebex.net/pub/example/KeyGenerator1.png']
destination = '/Users/SawaphobChavana/Desktop/testDownloader'
for _ in ThreadPool().imap(main_downloader, input_url):
    pass
