# private submodule の取り扱い

非公開にしたい Cog / ドメインロジックは、別の **private リポジトリ** に置き、このリポジトリの `private/` に git submodule として取り込む。
public 側に記録されるのは「private のどのコミットを使うか（コミット ID）」と `.gitmodules` の URL だけで、コードは公開されない。

```
discord-bot/              ← public（このリポジトリ）
├── .gitmodules           ← private リポジトリの URL（公開される）
├── private/              ← submodule（中身は private リポジトリ）
│   ├── __init__.py
│   ├── CLAUDE.md         ← 非公開機能の作業ルール・仕様
│   ├── cogs/             ← main.py が自動ロード（private.cogs.xxx）
│   ├── func/             ← from private.func.xxx import ...
│   └── tests/
│       └── __init__.py
└── main.py
```

## ルール

- **依存は private → public の一方向。** public の `cogs/` `func/` などから `private` を import しない（submodule を持たない環境で動かなくなり、機能の存在も漏れる）。
- private 内のレイヤー規則は public と同じ（`private/cogs` は Discord との接点、`private/func` は Discord に依存しない）。サービスは public の `service/container.py` 経由で取得する。
- 非公開機能の内容を public 側に書かない。
  - SPEC.md・CLAUDE.md・`.env.example`・コミットメッセージ・PR 本文に機能名や仕様を書かない。
  - ポインタ更新のコミットメッセージは「private を更新」程度にする。
  - 非公開機能の仕様・環境変数は `private/` 内のドキュメントに書く（`.env` 自体は共有でよい）。
- private リポジトリは `main` 1 本で運用する。本番でどの版を使うかは public 側の `main` が指すコミットで決まる。
- 一度でも public 側にコミット・push した内容は履歴に残る。間違えたら消すだけでは不十分（`git filter-repo` 等で履歴を書き換える）。

## 初回セットアップ（一度だけ）

1. GitHub で空の private リポジトリを作る（README 等も付けない）。
2. public 側で submodule を追加してコミット:
   ```sh
   git switch dev
   git switch -c feat/xxx
   git submodule add -b main git@github.com:nairoki23/<private-repo>.git private
   git add .gitmodules private
   git commit -m "private を submodule として追加"
   ```
3. `private/` に `__init__.py`、`cogs/`、`func/`、`tests/__init__.py` を作り、private 側でコミット・push。その後 public 側で `git add private` してコミット。

### 手元の git 設定（推奨）

```sh
git config submodule.recurse true            # pull / switch / checkout で submodule も追従
git config push.recurseSubmodules on-demand  # public を push すると未 push の private も push
git config status.submoduleSummary true      # git status に private の変更概要を表示
git config diff.submodule log                # diff でポインタの変化をコミット一覧で表示
```

### 別の場所に clone するとき

```sh
git clone --recurse-submodules git@github.com:nairoki23/discord-bot.git
# 既に clone 済みなら
git submodule update --init
```

private リポジトリにアクセスできない環境では `private/` は空のまま。`main.py` は何もロードしないだけで、public 部分は普通に動く。

### 本番サーバー

- private リポジトリの Settings → Deploy keys に、サーバーの公開鍵を **読み取り専用** で登録する。
- public リポジトリも SSH で使っていて鍵が別になる場合は、`~/.ssh/config` にホストの別名を設定し、サーバー側だけ URL を差し替える:
  ```sh
  git config submodule.private.url git@github-private:nairoki23/<private-repo>.git
  ```
- 初回に `git submodule update --init` を実行する。

## 普段の開発

### private を変更する

```sh
cd private
git switch main && git pull      # 作業前に必ずブランチに乗る（submodule は detached HEAD になっている）
# 編集・テスト
git add . && git commit -m "..."
cd ..
git add private                  # public 側のポインタを更新
git commit -m "private を更新"
git push                         # on-demand 設定があれば private も先に push される
```

- public と private にまたがる変更: それぞれで作業し、public 側のコミットに `git add private` を含める。
- public 側のブランチ運用（`feat/*` → `dev` → `main`）はそのまま。ポインタの変更も PR で一緒に移る。
- private の最新 `main` にポインタだけ合わせたいとき: `git submodule update --remote private` → `git add private` → コミット。

### テスト

```sh
python -m unittest                                   # public
python -m unittest discover -s private/tests -t .    # private
```

`private/__init__.py` と `private/tests/__init__.py` が必要（`private.tests.xxx` として import されるため）。

### PR レビュー

public 側の PR では `Subproject commit abc… → def…` としか出ない。private の差分は手元で確認する:

```sh
git diff dev -- private          # diff.submodule=log ならコミット一覧が出る
cd private && git log --oneline <旧>..<新>
```

## 本番反映

```sh
git pull                          # submodule.recurse 設定済みならこれで private も更新
git submodule update --init       # 未設定なら追加で実行
sudo systemctl restart discordbot
```

ロールバックも public 側を戻して `git submodule update` すれば、private もその時点の版に戻る。

## トラブルシューティング

| 症状 | 原因 | 対処 |
|---|---|---|
| `git status` に `modified: private (new commits)` | ポインタが記録と違う | 意図した変更なら `git add private` してコミット。意図しないなら `git submodule update` で記録どおりに戻す |
| `modified: private (modified content)` | private 内に未コミットの変更がある | `cd private` してコミットするか破棄する |
| private でコミットしたのに消えた | detached HEAD のまま作業した | `cd private && git reflog` でコミット ID を探し、`git switch main && git merge <id>` |
| `fatal: ... not our ref` / `did not contain <sha>` | private のコミットを push し忘れた | 手元で `cd private && git push` |
| `private/` が空 | submodule を初期化していない | `git submodule update --init` |
| 起動ログに `private.cogs.*` が出ない | 同上、または `private/cogs` がない | 上記を確認 |
| dev → main のマージでポインタが衝突 | 両ブランチで別々に private を更新した | 採用したい方のコミットを `cd private && git switch --detach <sha>` で選び、`git add private` |

## Claude Code で作業するとき

- サンドボックス設定で github.com への通信が拒否されているため、Claude は `submodule add` / `update --init` / `pull` / `push` を実行できない。これらは自分で実行する（Claude Code 上なら `! git ...`）。
- Claude は `private/` 内のファイルを読み書きできる。private 側の作業ルールは `private/CLAUDE.md` に書く。
