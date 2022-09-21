import asyncio
import datetime
import json
import os
import urllib.parse
import urllib.error
import utils
import traceback
import shutil
from utils import get_ext
from http.server import HTTPServer, BaseHTTPRequestHandler
from utils import print_error

def get_unloaded(links):
    for link in links:
        if link['status'] == 0:
            link['status'] = 1
            return link
        now_time = datetime.datetime.now()
        delta = now_time - link['time']
        if link['status'] == 1 and delta.seconds >= 20:
            return link
    return None


CLOSE_SERVER = False


class SimpleHTTPRequestHandler(BaseHTTPRequestHandler):
    url = ''
    links = []
    PageStatus = 0

    # определяем метод `do_GET`
    def do_GET(self):
        global CLOSE_SERVER
        if CLOSE_SERVER:
            self.server.server_close()
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', 'chrome-extension://lkoijhjdemidjgpbeigkpnpbapoebljl')
        self.end_headers()

        if self.path == '/request':
            if SimpleHTTPRequestHandler.PageStatus == 0:
                response = {"type": "page", "link": SimpleHTTPRequestHandler.url, "name": "main"}
                self.wfile.write(json.dumps(response).encode('utf-8'))
                SimpleHTTPRequestHandler.PageStatus = 1
            elif SimpleHTTPRequestHandler.PageStatus == 2 and (
                    link := get_unloaded(SimpleHTTPRequestHandler.links)) is not None:
                link['time'] = datetime.datetime.now()
                response = {'type': 'chapter', 'link': 'https://ranobelib.me' + link['link'],
                            'name': SimpleHTTPRequestHandler.links.index(link)}
                text = json.dumps(response).encode('utf-8')
                self.wfile.write(text)
            else:
                self.wfile.write(json.dumps({"type": "exit"}).encode('utf-8'))
        else:
            self.wfile.write(json.dumps({"type": "exit"}).encode('utf-8'))

    def do_POST(self):
        content_length = int(self.headers['Content-Length'])
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', self.headers['ORIGIN'])
        self.end_headers()

        result = self.rfile.read(content_length)

        paths = self.path.split('/')
        if len(paths) < 2:
            return
        action = paths[1]

        if action == 'result':
            data = json.loads(result.decode('utf-8'))
            content = data['content']
            chapters = []
            if SimpleHTTPRequestHandler.PageStatus == 1:
                content.reverse()
                i = 1
                for link in content:
                    chapters.append(
                        {'link': link['link'], 'status': 0, 'time': datetime.datetime.now(), 'name': link['name'],
                         'filename': str(i) + '.html'})
                    i += 1
                SimpleHTTPRequestHandler.links = chapters
                info = json.loads('{}')
                info['title'] = data['title']
                info['description'] = data['description']
                info['uid'] = '8c437648-2351-4f84-9e11-2d075b73ad31'
                for link in SimpleHTTPRequestHandler.links:
                    print(link)
                with open('temp/book.json', 'w', encoding='utf-8') as file:
                    file.write(json.dumps(info, ensure_ascii=False))

                SimpleHTTPRequestHandler.PageStatus = 2
            elif SimpleHTTPRequestHandler.PageStatus == 2:
                num = int(data['name'])
                if data['type'] == 'page':
                    utils.write_file(os.path.join('temp', 'html', SimpleHTTPRequestHandler.links[num]['filename']),
                                     content)
                elif data['type'] == 'exit':
                    SimpleHTTPRequestHandler.links[num]['status'] = 2
                if self.all_loaded():
                    for link in SimpleHTTPRequestHandler.links:
                        link.pop('time')
                        link.pop('status')
                        link.pop('link')
                    with open('temp/files.json', 'w', encoding='utf-8') as file:
                        file.write(json.dumps(SimpleHTTPRequestHandler.links, ensure_ascii=False))
                    SimpleHTTPRequestHandler.links = []
                    global CLOSE_SERVER
                    CLOSE_SERVER = True

        elif action == 'images':
            if get_ext(paths[2]) == '':
                if result[:8] == b'\x89\x50\x4e\x47\x0d\x0a\x1a\x0a':
                    paths[2] = paths[2] + '.png'
                elif result[:4] == b'\xFF\xD8\xFF\xDB':
                    paths[2] = paths[2] + '.jpg'
                elif result[:4] in [b'\xFF\xD8\xFF\xE0', b'\xFF\xD8\xFF\xE1']:
                    paths[2] = paths[2] + '.jpeg'

            with open(os.path.join('temp', 'images', paths[2]), 'wb') as file:
                file.write(result)
        elif action == 'cover':
            with open(os.path.join('temp', 'cover' + get_ext(paths[2])), 'wb') as file:
                file.write(result)
        elif action == 'error':
            global CLOSE_SERVER
            CLOSE_SERVER = True
            print_error(result.decode('utf-8'))

    def all_loaded(self):
        for link in SimpleHTTPRequestHandler.links:
            if link['status'] != 2:
                return False
        return True

    def do_OPTIONS(self):
        self.send_response(200, "ok")
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, OPTIONS')
        self.send_header("Access-Control-Allow-Headers", "X-Requested-With")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()


def get_image_ext(image):
    if image[:8] == b'\x89\x50\x4e\x47\x0d\x0a\x1a\x0a':
        return '.png'
    elif image[:4] == b'\xFF\xD8\xFF\xDB':
        return '.jpg'
    elif image[:4] in [b'\xFF\xD8\xFF\xE0', b'\xFF\xD8\xFF\xE1']:
        return '.jpeg'
    return ''


def find_image_link(html: str, pos: int):
    a_start_pos = html.find('<img', pos)
    if a_start_pos == -1:
        return html, -1
    src_start_pos = html.find(' src="', a_start_pos)
    if src_start_pos == -1:
        return html, -1
    src_end_pos = html.find('"', src_start_pos + 6)

    if src_end_pos == -1:
        return html, -1
    src = html[src_start_pos + 6:src_end_pos]
    a_end_pos = html.find('>', src_end_pos + 1)
    return src, a_end_pos


import aiohttp


async def load_image(src: str):
    filename = src.split('/')[-1]
    temp_filepath = os.path.join('temp', 'images', filename)

    try:
        url = urllib.parse.urlparse(src)
        if url.hostname is None:
            src = 'https://ranobelib.me' + src
            url = urllib.parse.urlparse(src)

        if url.hostname != 'ranobelib.me':
            print('start load ', src)
            async with aiohttp.ClientSession() as session:
                async with session.get(src) as response:
                    content = await response.content.read()
                    if get_ext(filename) == '':
                        temp_filepath += get_image_ext(content)
                        filename += get_image_ext(content)
                    with open(temp_filepath, 'wb') as file:
                        file.write(content)
                    print('end load ', src)
            # page = requests.get(src)
            # if get_ext(filename) == '':
            #     temp_filepath += get_image_ext(page.content)
            #     filename += get_image_ext(page.content)

            # with open(temp_filepath, 'wb') as file:
            #     file.write(page.content)
    except:
        traceback.print_exc()


async def load_images(html):
    pos = 0
    tasks = []
    while True:
        link, pos = find_image_link(html, pos)
        if pos == -1:
            break
        task = load_image(link)
        tasks.append(task)
    if len(tasks) != 0:
        await asyncio.wait(tasks)
    return html


def load_pages(path):
    SimpleHTTPRequestHandler.url = path
    server = HTTPServer(('localhost', 59675), SimpleHTTPRequestHandler)
    print('server started')
    server.serve_forever()
    print('server closed')


def init_dirs():
    print('start init dirs')
    if os.path.exists('temp'):
        shutil.rmtree('temp')
    os.mkdir('temp')
    os.mkdir('temp/html')
    os.mkdir('temp/images')
    print('finish init dirs')


async def load_page_images():
    print('start download images')
    books = json.loads(utils.read_file('temp/files.json'))
    tasks = []
    for book in books:
        html = utils.read_file(os.path.join('temp', 'html', book['filename']))
        task = load_images(html)
        tasks.append(task)
    if len(tasks) != 0:
        await asyncio.wait(tasks)
    print('finish download images')


def load_chapters(path: str) -> bool:
    try:
        init_dirs()
        load_pages(path)
        asyncio.run(load_page_images())
        return True
    except:
        print(traceback.print_exc())
        return False
