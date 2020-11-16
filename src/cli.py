from typing import Dict, List
import os
import glob
import re
import argparse
from dataclasses import dataclass, field
from pprint import pprint
from collections import OrderedDict
from PIL import Image
import imagehash
from halo import Halo
from tqdm import tqdm
import time

only_imgs = re.compile('.+\.(png|jpg|jpeg)$', re.IGNORECASE)


@dataclass
class FileResult:
    filename: str = ''
    is_similar_to_prev: bool = False


@dataclass
class DirChunk:
    dirname: str = ''
    fileresults: List[FileResult] = field(default=list)


def is_img(path: str):
    return only_imgs.match(path) is not None


def list_all_imgs(path2root: str):
    all_items = glob.glob(f'{path2root}/**/*', recursive=True)
    all_files = list(filter(os.path.isfile, all_items))
    # pprint(all_files)
    all_imgs = list(filter(is_img, all_files))
    # pprint(all_imgs)
    return all_imgs


def split_imgs_per_dir(all_img_paths: List[str]):
    d: Dict[str, DirChunk] = dict()
    for p in all_img_paths:
        dirname = os.path.dirname(p)
        basename = os.path.basename(p)
        chunk = d.get(dirname, DirChunk(dirname=dirname, fileresults=[]))
        chunk.fileresults.append(FileResult(filename=basename))
        d[dirname] = chunk
    return list(d.values())


def dhash(img):
    return imagehash.dhash(Image.open(img))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='類似画像隔離ツール')
    parser.add_argument('-s', '--source', help='処理対象ルートディレクトリのパス')
    parser.add_argument('-d', '--dest', help='類似判定された画像の隔離および結果ログファイル保存先パス')
    parser.add_argument('-t', '--threshold', type=int,
                        default=20, help='dhash値の差分がこの値以下なら類似画像と判断する')
    parser.add_argument('--dry', action='store_true',
                        help='指定した場合はログ出力のみ、隔離実行せず')
    args = parser.parse_args()
    path2srcdir = os.path.join(os.getcwd(), args.source)
    path2destdir = os.path.join(os.getcwd(), args.dest)
    threshold = args.threshold
    dry = args.dry

    with Halo(text='処理対象をスキャン中', spinner='dots'):
        all_img_paths = list_all_imgs(path2srcdir)
        all_imgs_count = len(all_img_paths)
        pprint(all_imgs_count)
        pprint(all_img_paths)
        imgs_per_dir = split_imgs_per_dir(all_img_paths)
        pprint(imgs_per_dir)
        time.sleep(1)

    with tqdm(range(0, all_imgs_count - 1)) as pbar:
        pbar.set_description('画像ハッシュ値を計算・比較中...')
        prev_hash = None
        for chunk in imgs_per_dir:
            chunk.fileresults.sort(key=lambda x: x.filename)

            # TODO: 並列化
            # 90,000imgs * 2sec = 180,000sec = 50h

            for img in chunk.fileresults:
                pbar.set_postfix(OrderedDict(
                    dir=chunk.dirname, file=img.filename))
                current_hash = dhash(os.path.join(chunk.dirname, img.filename))
                img.is_similar_to_prev = (prev_hash is not None) and (abs(
                    prev_hash - current_hash) <= threshold)
                prev_hash = current_hash
                time.sleep(1)
                pbar.update()
            prev_hash = None

    pprint(imgs_per_dir)
