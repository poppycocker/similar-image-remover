from typing import Dict, List
import os
import pathlib
import glob
import re
import datetime
import argparse
import shutil
from concurrent.futures import ProcessPoolExecutor
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


def split_imgs_per_dir(all_img_paths):
    d: Dict[str, DirChunk] = dict()
    for p in all_img_paths:
        dirname = os.path.dirname(p)
        basename = os.path.basename(p)
        chunk = d.get(dirname, DirChunk(dirname=dirname, fileresults=[]))
        chunk.fileresults.append(FileResult(filename=basename))
        d[dirname] = chunk
    return list(d.values())


def dhash(path2img: str):
    return imagehash.dhash(Image.open(path2img))


def buildDstPath(path2srcdir: str, path2dstdir: str, img: FileResult, chunk: DirChunk):
    src = os.path.join(chunk.dirname, img.filename)
    dst = src.replace(path2srcdir, path2dstdir)
    return dst


def move(src: str, dst: str):
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    shutil.move(src, dst)


def calc_hash_diff(base_hash, current_hash):
    if base_hash is None:
        return float('inf')
    return abs(base_hash - current_hash)


def worker_func(chunk, path2srcdir, path2dstdir, threshold, dry):
    chunk.fileresults.sort(key=lambda x: x.filename)
    base_hash = None
    logs: List[str] = []
    for img in chunk.fileresults:
        current_hash = dhash(os.path.join(chunk.dirname, img.filename))
        diff_hash = calc_hash_diff(base_hash, current_hash)
        img.is_similar_to_prev = (diff_hash <= threshold)
        # 連写継続中は基準を動かさない
        if base_hash is None or not img.is_similar_to_prev:
            base_hash = current_hash
        path2dstimg = buildDstPath(
            path2srcdir, path2dstdir, img, chunk)
        if not dry and img.is_similar_to_prev:
            move(os.path.join(chunk.dirname, img.filename), path2dstimg)
        logs.append(
            f'{chunk.dirname},{img.filename},{current_hash},{diff_hash},{img.is_similar_to_prev},{path2dstimg if img.is_similar_to_prev else ""}')

    return logs


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='類似画像隔離ツール')
    parser.add_argument('-s', '--source', help='処理対象ルートディレクトリのパス')
    parser.add_argument('-d', '--dest', help='類似判定された画像の隔離および結果ログファイル保存先パス')
    parser.add_argument('-t', '--threshold', type=int,
                        default=20, help='dhash値の差分がこの値以下なら類似画像と判断する')
    parser.add_argument('-p', '--parallel_num', type=int,
                        default=4, help='並列実行数')
    parser.add_argument('--dry', action='store_true',
                        help='指定した場合はログ出力のみ、隔離実行せず')
    args = parser.parse_args()
    path2srcdir = str(pathlib.Path.cwd() / pathlib.Path(args.source))
    path2dstdir = str(pathlib.Path.cwd() / pathlib.Path(args.dest))
    threshold = args.threshold
    dry = args.dry

    timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    os.makedirs(path2dstdir, exist_ok=True)
    path2log = os.path.join(path2dstdir, f'log_{timestamp}.csv')
    log = open(path2log, mode='w', encoding="utf_8")

    with Halo(text='処理対象をスキャン中', spinner='dots'):
        all_img_paths = list_all_imgs(path2srcdir)
        all_imgs_count = len(all_img_paths)
        # pprint(all_imgs_count)
        # pprint(all_img_paths)
        imgs_per_dir = split_imgs_per_dir(all_img_paths)
        # pprint(imgs_per_dir)
        log.write(f'全画像数:,{all_imgs_count}\n')
        log.write(f'ディレクトリ数:,{len(imgs_per_dir)}\n')

    with tqdm(total=0) as progress:
        progress.set_description(f'画像ハッシュ値を計算・比較{"・類似隔離" if dry else ""}中...')

        def on_done(f):
            logs: List[str] = f.result()
            log.write('\n'.join(logs) + '\n')
            progress.total = all_imgs_count
            progress.refresh()
            progress.update(len(logs))
        # https://gist.github.com/alexeygrigorev/79c97c1e9dd854562df9bbeea76fc5de
        with ProcessPoolExecutor(max_workers=args.parallel_num) as executor:
            futures = []
            for chunk in imgs_per_dir:
                future = executor.submit(worker_func, chunk, path2srcdir, path2dstdir, threshold, dry)
                future.add_done_callback(lambda f: on_done(f))
                futures.append(future)

    # pprint(imgs_per_dir)
    log.close()
    print(path2log)
