import os
import imagehash
import tqdm
import sys
from PIL import Image

USAGE = "Usage: rmSimilar.py imputDir resultFile"

# inputDir = "E:/field_additional/900nodamage/"
# resultFile = "E:/field_additional/900nodamage/exclude.bat"


def d_hash(img, otherimg):
    hash = imagehash.dhash(Image.open(img))
    other_hash = imagehash.dhash(Image.open(otherimg))
    return hash - other_hash


def ave_hash(img, otherimg):
    hash = imagehash.average_hash(Image.open(img))
    other_hash = imagehash.average_hash(Image.open(otherimg))
    return hash - other_hash


def p_hash(img, otherimg):
    hash = imagehash.phash(Image.open(img))
    other_hash = imagehash.phash(Image.open(otherimg))
    return hash - other_hash


def validation(args):
    argc = len(args)

    if argc != 3:
        print(USAGE)
        quit()


if __name__ == "__main__":

    # validation(sys.argv)

    inputDir = sys.argv[1]
    resultFile = sys.argv[2]

    outputdir, outfilename = os.path.split(resultFile)
    os.makedirs(outputdir, exist_ok=True)

    for class_name in os.listdir(inputDir):

        class_dir = os.path.join(inputDir, class_name)
        if not os.path.isdir(class_dir):
            continue

        imagelist = os.listdir(class_dir)
        imagelist = [x for x in imagelist if not x.endswith("txt")]
        length = len(imagelist)

        chtargetflg = True
        img1 = ""
        output = open(resultFile, 'a')

        for i in tqdm.tqdm(range(0, length - 1), desc=class_name):

            # 隣合う画像を比較
            if chtargetflg:
                img1 = os.path.join(class_dir, imagelist[i])

            img2 = os.path.join(class_dir, imagelist[i + 1])

            if ".db" in img1 or ".db" in img2:
                continue

            try:
                imghash = d_hash(img1, img2)
            except OSError as e:
                print(e)
                continue

            if imghash <= 20:

                dest = img2.replace("field_additional",
                                    "field_additional_exclude")

                destdir, destfilename = os.path.split(dest)
                os.makedirs(destdir, exist_ok=True)

                # 差分が20以下だったら類似画像とみなし削除する
                # os.remove(img2)
                # 削除バッチ用
                # output.writelines('del "{0}"/n'.format(img2))
                
                # 移動バッチ用
                output.writelines('move "{0}" "{1}"\n'.format(img2, dest))
                chtargetflg = False
            else:
                chtargetflg = True
