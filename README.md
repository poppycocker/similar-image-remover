# similar-image-remover

## setup

install Anaconda3 before run following commands.

```sh
conda create -n similar-image-remover python=3.8
conda activate similar-image-remover
pip install -r requirements.txt
```

## design

- ルートから辿って全ディレクトリを処理する
  - まず全スキャンを掛け、(ディレクトリ, 画像数)リストを作成する
  - tqdm用に全画像数も計算しておく
- 類似判定処理は各ディレクトリ単位で実行する
  - ディレクトリ内の画像のdhash値を比較して差分が指定以下なら類似と判定する
    - (dry=false時) ディレクトリ構造を保ったまま、destに隔離する(ルートをdestに変える)
    - 結果をログ(CSV)に記録する

### log fields

- directory
- filename
- dhash val: number(hex)
- dhash diff: number
- is similar to prev img: boolean
- moved to

### args

- -s, --source: 処理対象ルートディレクトリのパス
- -d, --dest: 類似判定された画像の隔離および結果ログファイル保存先パス
- -t, --threshold=20: dhash値の差分がこの値以下なら類似画像と判断する
- --dry: ログ出力のみ、隔離実行せず
