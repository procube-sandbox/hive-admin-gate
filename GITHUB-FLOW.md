# github flow 運用ポリシー
このリポジトリは [github flow](https://gist.github.com/Gab-km/3705015) に基づいて管理されています。github flow におけるプルリクエストのブランチの命名規則を以下に示します。

機能種別/派生元リビジョン/機能名

例えば、 Feature/2.2.12-3-g371b837/add-twitter-publisher のようなブランチ名を使用します。

## 機能種別
機能種別には以下のいずれかを指定します。

### Feature
新機能を実装する場合には機能種別に "Feature" を指定します。

### Support
OS、ミドルウェア、ライブラリ、フレームワークなどの新しいバージョンをサポートする場合には機能種別に "Support" を指定します。

### Fix
バグ修正を行う場合には機能種別に "Fix" を指定します。

### Docs
ドキュメント、サンプルを修正する場合には機能種別に "Docs" を指定します。

### Dev
nec-disaster-mother 自身の開発にのみ影響する修正を行う場合には機能種別に "Dev" を指定します。

## 機能名
機能名は短い英文です。空白の代わりにハイフン(-)を使用します。

# 手順
以下に修正を main ブランチにマージする手順を示します。

## 1. ブランチの作成
修正を開始する場合、最初にローカルリポジトリで以下のコマンドを実行してブランチを作成してください。

```shell
git checkout -b ブランチ名
```
例えば、 Twitter のパブリッシャを追加する場合は、以下のようなコマンドになります。
```shell
git checkout -b Feature/$(git describe --tags)/add-twitter-publisher
```

#### 補足
> main ブランチで修正を始めてしまっていても add や commit を行っていなければブランチを作成することができます。
> その場合でも上記コマンドで修正内容は失われることはありません。他の目的の修正と混じってしまった場合には、後述の commit の手順でプルリクエストに含めるファイルを選択することができます。ファイル内で混じってしまった場合には、 git stash などを使ってファイル内を切り分ける必要があるでしょう。

## 2. 修正&テスト
ローカルリポジトリで修正とテストを繰り返してください。

## 3. ステージング
修正したファイルおよび追加するファイルをステージングに移してください。

#### 補足
> 追加ファイルがなく、修正したファイルをすべて commit する場合、次の commit のコマンドに -a オプションを追加することでこの手順をスキップできます。

### 3-A. ファイル名を指定する場合
以下のコマンドでファイルを指定してステージングに移してください。
```shell
git add ファイル名1 ファイル名2
```
例えば、GITHUB-FLOW-ja.mdと inventory/hive.yml をステージングに移す場合は、以下のコマンドを実行します。
```shell
git add GITHUB-FLOW-ja.md inventory/hive.yml
```

### 3-B. すべてのファイルをステージングに移す場合
以下のコマンドで追加したファイルと修正したファイルをすべてステージングに移してください。
```shell
git add -A
```

## 4. commit
以下のコマンドでステージングされたファイルを commit してください。
```shell
git commit -m 'コミット内容の記述'
```
コミット内容の記述は短い文章でコミットの内容を記述してください。例えば、Twitter のパブリッシャを追加する機能を commit する場合は、以下のようなコマンドになります。
```shell
git commit -m 'add twitter publisher'
```

## 5. push
以下のコマンドでステージングされたファイルを push してください。
```shell
git push origin ブランチ名
```
例えば、 Twitter のパブリッシャを追加する機能を 2.2.12 に追加した場合は、以下のようなコマンドになります。
```
git push origin Feature/2.2.12/add-twitter-publisher
```

## 6. プルリクエストの作成
[プルリクエストの作成](https://backlog.com/ja/git-tutorial/pull-request/06/)に従ってプルリクエストを作成してください。

プリリクエストの名前は自動的にブランチ名から作成されますが、先頭に[]で囲んで機能種別を追加してください。例えば、「Feature/2.2.12/add-twitter-publisher」というブランチに対するプルリクエストは「add twitter publisher」という名前が自動的に設定されますが、これを「[Feature] add twitter publisher」に修正してください。

その後、Create pull request をクリックしてください。

## 7. レビューと修正
レビューによりプルリクエストを修正する必要が生じた場合は、ローカルリポジトリを修正してpushしてください。すなわち、手順 2. から 5. を繰り返し実施してください。push すると自動的に pull request に組み込まれるので、 Web 上の[Pull requests](https://procube.backlog.jp/git/NSAG/hive-admin-gate/pullRequests?q.statusId=1)から自分のプルリクエストを開き、コメントを入力することで議論を続行してください。

#### 補足
> 修正を複数人で行う場合はブランチをそれぞれのローカルリポジトリに pull するして修正してください。

## 8. マージ
レビューが終わったプルリクエストは「Squash and merge」をクリックしてマージしてください。
#### 補足
> マージするとプリリクエストは完了となり、クローズ状態になります。新たに修正が必要になった場合は、たとえ過去のプルリクエストに関連する場合でも、この手順の最初からやり直して新しいプルリクエストとしてください。

## 9. ブランチの削除
マージが完了したブランチは削除してください。

## 9-1. ローカルリポジトリのブランチの削除
以下のコマンドでローカルリポジトリのブランチを削除してください。
```shell
git branch -D ブランチ名
```
例えば、 Twitter のパブリッシャを追加する機能を 2.2.12 に追加するプリリクエストのマージを終えた場合、以下のようなコマンドになります。
```shell
git branch -D Feature/2.2.12/add-twitter-publisher
```

## 9-2. リポジトリのブランチの削除
マージが終わったプルリクエストを Web で開き、「Delete branch」をクリックしてブランチを削除してください。
#### 補足
> マージが完了したプルリクエストはデフォルトでは[Pull requests](https://procube.backlog.jp/git/CITSIDAAS/hive-idaas/pullRequests?q.statusId=1)に表示されません。「Filters」にデフォルトで指定されている「is:open」を削除して再検索して対象のプルリクエストを探して開いてください。

# 環境ブランチの利用

開発者個人用の hive や結合テスト用の hive を構築するためにこのソースコードの修正が必要な場合、環境ブランチを作成することができます。

## 1. 環境ブランチを作成
個人デバッグ用環境、結合テスト環境、お客様環境など main のコードとは別に環境用に修正を行う場合は環境ブランチを作成してください。
環境ブランチは local/環境名としてください。たとえば、 aws東京リージョンに作る結合テスト環境であれば、以下のようなコマンドでブランチを作成してください。

```
git checkout -b local/aws-tokyo
```

このブランチ上でドメイン名、hive名、 IaaS のイメージ名などを必要に応じて環境用にカスタマイズしてください。
カスタマイズが終わったところで一旦 commit してください。

#### 補足
> 環境ブランチ上でコードの修正を行わずに、他の人が main に加えた修正を取り込む場合は、次の手順 2.から 5. および 7. は実施する必要はありません。
「6. 環境ブランチへのプルリクエストの取り込み」のみを行ってください。

## 2. 修正用ブランチ作成→修正&テスト→ commit
環境ブランチを直接修正すると後の rebase が難しくなりますので、修正用のブランチを作成してそこで、修正とcommit を行ってください。
具体的には、前章の 1.から4.を実施してください
ただし、前章 1. でブランチを作成するとき派生元ブランチが環境ブランチとなるようにしてください。例えば、以下のように git chekout コマンドでカレントが環境ブランチとなっている状態から実行してください。

```
git checkout local/aws-tokyo
git checkout -b Feature/local/add-twitter-publisher
```

#### 注意!
> 修正用ブランチでは、前章5.push を実行しないでください。このブランチから直接pushすると、自分専用にカスタマイズされた部分がプルリクエストに入ってしまいます。


## 3.プルリクエスト用ブランチの作成
前章1.と同様の手順でプルリクエスト用ブランチを作成してください。派生元を main としてください。例えば、以下のコマンドを実行してください。

```
git checkout main
git pull origin main
git checkout -b Feature/$(git describe --tags)/add-twitter-publisher
```

## 4. ローカルでの修正内容をマージ
ログを確認してローカルのコミットのIDを取得してください。例えば、以下のように表示されたとします。

```
$ git checkout local/aws-tokyo
$ git log
commit 27ea9f6315aa874c49917ae7295b83eac0dd5d53
Author: hoge hogehoge
Date:   San Jun 25 12:55:00 2017 +0900

    new_branch 追加 3

commit 516b29f44ebff0b18fe1d7dc3aab15d17a942d62
Author: hoge hogehoge
Date:   San Jun 25 12:50:00 2017 +0900

    new_branch 追加 2

commit 47210350a1abbd59a0e538ff2904b5ae45e07d73
Author: hoge hogehoge
Date:   San Jun 25 12:45:00 2017 +0900

    Update another user.
```

プルリクエスト用ブランチに差分を適用してください。
例えば、上記のうち、最新の2つだけを差分でリリースしたい場合は以下のようにコマンドを実行してください。

```
git checkout Feature/1.0.2-xxx/add-twitter-publisher
git cherry-pic 27ea9f6315aa874c49917ae7295b83eac0dd5d53 516b29f44ebff0b18fe1d7dc3aab15d17a942d62
```

cherry-pick で競合が発生した場合は http://naiki.hatenablog.com/entry/20140219/1392740162 などを参考にして解決してください。

## 5. プルリクエスト
前章 6.から 9. の手順でプルリクエストを進めてください。

## 6. 環境ブランチへのプルリクエストの取り込み
以下の手順で main に取り込まれたプルリクエストの修正内容を環境ブランチにマージしてください。

```
git checkout main
git pull origin main
git checkout local/aws-tokyo
git rebase main
```
rebase で競合が発生した場合は https://docs.github.com/ja/github/collaborating-with-issues-and-pull-requests/resolving-a-merge-conflict-using-the-command-line などを参考にして解決してください。

## 7. 不要になったブランチの削除
コードのリリースが成功していることが確認できたら、以下のようなコマンドで修正用ブランチ、プルリクエスト用ブランチを削除してください。

```
git branch -D Feature/local/add-twitter-publisher
git branch -D Feature/1.0.2-xxx/add-twitter-publisher
```

