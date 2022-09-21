import datetime
import json
import shutil
import glob
import os
import secrets

from utils import get_ext
from utils import get_filename
from utils import read_file
from utils import write_file


def get_file_id(filename: str) -> str:
    return get_filename(filename).replace(' ', '')


def print_row() -> None:
    print('-----------------')


def reformat_link(html: str, pos, images: dict, ind):
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
    filename = src.split('/')[-1]
    new_filename = 'image-' + ind + get_ext(filename)
    if get_ext(new_filename) == '':
        files = glob.glob(os.path.join('temp', 'images', filename + '.*'))
        if len(files) == 0:
            print(new_filename, ' not found ext')
            return html, -1
        new_filename += get_ext(files[0])
        filename += get_ext(files[0])
    filepath = 'images/' + new_filename

    images[filename] = new_filename
    html = html[:src_start_pos + 6] + filepath + html[src_end_pos:]
    src_end_pos = html.find('"', src_start_pos + 6)
    a_end_pos = html.find('>', src_end_pos + 1)
    if html[a_end_pos - 1] != '/':
        html = html[:a_end_pos] + '/' + html[a_end_pos:]
        a_end_pos += 1
    return html, a_end_pos


def reformat_links(html, images: dict, ind: int):
    pos = 0
    image_ind = 1
    while True:
        html, pos = reformat_link(html, pos, images, str(ind) + '-' + str(image_ind))
        if pos == -1:
            break
        image_ind += 1
    return html


def get_media_type(file):
    ext = get_ext(file)
    if ext == '.png':
        return 'png'
    if ext == '.jpg' or ext == '.jpeg':
        return 'jpeg'
    return ''


def init_dirs():
    print('start init dirs')
    book_dir = 'book'

    if not os.path.exists(book_dir):
        os.mkdir(book_dir)
    else:
        shutil.rmtree(book_dir)
        os.mkdir(book_dir)
    shutil.copy2('templates/mimetype', os.path.join(book_dir, 'mimetype'))
    meta_inf_dir = os.path.join(book_dir, 'META-INF')
    if not os.path.exists(meta_inf_dir):
        os.mkdir(meta_inf_dir)
    shutil.copy2('templates/container.xml', os.path.join(meta_inf_dir, 'container.xml'))
    ops_dir = os.path.join(book_dir, 'OPS')
    if not os.path.exists(ops_dir):
        os.mkdir(ops_dir)
    images_dir = os.path.join(ops_dir, 'images')
    if not os.path.exists(images_dir):
        os.mkdir(images_dir)
    styles_dir = os.path.join(ops_dir, 'styles')
    if not os.path.exists(styles_dir):
        os.mkdir(styles_dir)
    shutil.copy2('temp/cover.jpg', os.path.join(images_dir, 'cover.jpg'))
    shutil.copy2('templates/CoverPage.css', os.path.join(styles_dir, 'coverPage.css'))
    shutil.copy2('templates/customCover.xhtml', os.path.join(ops_dir, 'customCover.xhtml'))
    print('finish init dirs')
    print_row()
    return ops_dir, images_dir


def load_chapters(ops_dir: str) -> (list, dict):
    print('start load chapters')
    i = 1
    chapter_template = read_file('templates/chapter.xml')
    image_dict = {}
    htmls = []
    for file in json.loads(read_file('temp/files.json')):
        old_name = os.path.join('temp/html', file['filename'])
        file_id = 'chapter' + str(i)
        new_name = os.path.join(ops_dir, 'chapter-' + str(i) + '.xhtml')

        html = read_file(old_name)
        html = reformat_links(html, image_dict, i)
        write_file(new_name, chapter_template.format(title=file['name'], content=html))
        htmls.append({'id': file_id, 'title': file['name'], 'filename': 'chapter-' + str(i) + '.xhtml'})
        i += 1
    print('finish load chapters')
    print_row()
    return htmls, image_dict


def load_images(images_dir: str, image_dict: dict) -> list:
    print('start load images')
    images = []
    for file in os.listdir('temp/images'):
        new_filename = image_dict[file]
        shutil.copy2(os.path.join('temp/images', file), os.path.join(images_dir, new_filename))
        images.append(new_filename)
    print('finish load images')
    print_row()
    return images


def make_manifest(htmls: list, images: list) -> str:
    print('start make manifest')
    manifest_item_template = read_file('templates/manifest_item.xml')

    manifest = '\n'.join(map(lambda x: manifest_item_template.format(id=get_file_id(x), href='images/' + x,
                                                                     media_type='image/' + get_media_type(x)),
                             images)) + \
               '\n'.join(map(lambda x: manifest_item_template.format(id=x['id'], href=x['filename'],
                                                                     media_type='application/xhtml+xml'), htmls))
    print('finish make manifest')
    print_row()
    return manifest


def make_spine(htmls: list) -> str:
    print('start make spine')
    spine_item_template = read_file('templates/spine_item.xml')
    spine = spine_item_template.format(id='nav') + '\n'.join(
        map(lambda x: spine_item_template.format(id=x['id']), htmls))

    print('finish make spine')
    print_row()
    return spine


def make_guide() -> str:
    print('start make guide')
    guide_item_template = read_file('templates/guide_item.xml')

    guide = '\n'.join([
        guide_item_template.format(type='text', title='Постер', href='customCover.xhtml'),
        guide_item_template.format(type='toc', title='Содержание', href='nav.xhtml'),
    ])
    print('finish make guide')
    print_row()

    return guide


def make_book_opf(ops_dir, info: dict, htmls: list, images: list) -> None:
    print('start make book.opf')
    title = info['title']
    uid = info['uid']
    description = info['description']
    creation_date = datetime.date.today()
    manifest = make_manifest(htmls, images)
    spine = make_spine(htmls)
    guide = make_guide()

    book_opf_template = read_file('templates/book.opf')

    book_opf = book_opf_template.format(title=title, date=creation_date, identifier=uid, description=description,
                                        manifest=manifest, spine=spine, guide=guide)

    write_file(os.path.join(ops_dir, 'book.opf'), book_opf)
    print('finish make book.opf')
    print_row()


def make_book_ncx(ops_dir: str, info: dict, htmls: list) -> None:
    print('start make book.ncx')
    title = info['title']
    uid = info['uid']
    navpoint_template = read_file('templates/navpoint.xml')
    book_ncx_template = read_file('templates/book.ncx')

    navmap = '\n'.join(
        map(lambda x: navpoint_template.format(id=x['id'], playOrder=htmls.index(x) + 3, src=x['filename'],
                                               text=x['title']),
            htmls))

    book_ncx = book_ncx_template.format(title=title, uid=uid, navMap=navmap)

    write_file(os.path.join(ops_dir, 'book.ncx'), book_ncx)
    print('finish make book.ncx')
    print_row()


def make_nav_page(ops_dir, htmls: list) -> None:
    print('start make nav page')
    nav_item_template = read_file('templates/nav_item.xml')
    nav_template = read_file('templates/nav.xhtml')

    nav_data = '\n'.join(
        map(lambda x: nav_item_template.format(href=x['filename'], title=x['title']), htmls)
    )
    nav = nav_template.format(nav=nav_data)
    write_file(os.path.join(ops_dir, 'nav.xhtml'), nav)
    print('finish make nav page')
    print_row()


def make_archive():
    print('start make archive')
    output_dir = 'output'
    zip_name = os.path.join(output_dir, secrets.token_urlsafe(10))
    shutil.make_archive(zip_name, 'zip', 'book')
    shutil.move(zip_name + '.zip', zip_name + '.epub')
    print('finish make archive')
    print_row()


async def make_book():
    ops_dir, images_dir = init_dirs()
    htmls, image_dict = load_chapters(ops_dir)

    images = load_images(images_dir, image_dict)

    book_info = json.loads(read_file('temp/book.json'))
    make_book_opf(ops_dir, book_info, htmls, images)
    make_book_ncx(ops_dir, book_info, htmls)
    make_nav_page(ops_dir, htmls)
    make_archive()

    print('completed')
    print_row()
