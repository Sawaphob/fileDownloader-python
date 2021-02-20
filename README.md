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
input_url: string contain url and separated each url with ','

destination: Full path to place the downloaded file

```bash
python downloader.py $input_url $destination
```

Example:
```bash
python3 downloader.py 'ftp://speedtest:speedtest@ftp.otenet.gr/test10Mb.db,https://az764295.vo.msecnd.net/stable/8490d3dde47c57ba65ec40dd192d014fd2113496/VSCode-darwin.zip,sftp://demo:password@test.rebex.net/pub/example/KeyGenerator.png' /Users/SawaphobChavana/Desktop/testDownloader 
```

## Testing
```bash
python -m unittest downloader.py
```
