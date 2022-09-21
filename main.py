import asyncio
import epub
import sys
import urllib.parse
import downloader

from utils import print_error

asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


def main():
    if len(sys.argv) != 1:
        link = sys.argv[1]
    else:
        link = input('Enter ranobelib link:')
    if link == '':
        print_error('link was empty')
        return
    url = urllib.parse.urlparse(link)
    if url.hostname is None:
        if link[0] != '/':
            link = '/' + link
        link = 'https://ranobelib.me' + link
        url = urllib.parse.urlparse(link)
    elif url.hostname != 'ranobelib.me':
        print_error('Expected link to ranobelib')
        return
    link = url.geturl()
    # link = 'https://ranobelib.me/im-the-max-level-newbie?bid=10938&section=chapters&ui%5B0%5D=448860%3Fsection%3Dchapters&ui%5B1%5D=448860'
    # link = 'https://ranobelib.me/youjo-senkii/'
    # link = 'https://ranobelib.me/fourth-princes-debauchery/'
    if not downloader.load_chapters(link):
        print('crow download')
        return

    print('start making book')
    asyncio.run(epub.make_book())
    print('book made')


if __name__ == '__main__':
    main()
