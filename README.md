# fileDownloader-python

This program is a file downloader written in python. There are 4 support protocol which is http, https, ftp and sftp

## Installation

Create virtual environment in python:

```bash
virtualenv -p python3 venv
```

Active your virtual environment:
```bash
source venv/bin/activate
```

Install all dependencies:
```bash
pip install -r requirements.txt
```
## Usage
Change the input_url and destination variable
input_url: list of files url that you want to download
destination: Full path to place the downloaded file
Example:
```python
input_url = ['ftp://speedtest:speedtest@ftp.otenet.gr/test10Mb.db','sftp://demo:password@test.rebex.net/pub/example/KeyGenerator.png']
destination = '/Users/SawaphobChavana/Desktop/testDownloader'
```
Then run:
```bash
python downloader.py
```

## Testing
```bash
python -m unittest downloader.py
```
