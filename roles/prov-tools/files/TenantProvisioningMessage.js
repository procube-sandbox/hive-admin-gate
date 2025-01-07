/*
	NetSoarer ID Manager Ver. 2.0
	$Revision: 307 $
	Copyright (c) 2013 Procube Co.,Ltd. All Rights Reserved.
*/

/*
* プロジェクト固有のメッセージテーブル定義方法について
* - default.js のconfig.general.messageTableDir のディレクトリ内のjsファイルが対象です。サブディレクトリは読み込まれません。
* - 拡張子jsファイルを読み込みます。拡張子jsファイルの内容がjsとして不正な場合はエラーが発生し、そのままプロセスが落ちます。jsでmessageTable, messagePatternをexportしていない場合には、無視します。
* - プロジェクト毎の固有のエラーコードは「IDM2ユーザ使用領域 8000～8999」です。
* - idm2messageと重複した場合、config.general.messageTableDirの内容で上書きされます。重複とは具体的には以下を指します。
*    -> messageTableのlangとcodeの値が同じ場合
*    -> messagePatternのformatの値が同じ場合
* - config.general.messageTableDir内の記述内容が重複した場合の動作は不定です。config.general.messageTableDir内で重複しないようにしてください。
*/

module.exports = {
/*
	記述例：　記述方法はidm2message.jsと同じです。
*/
	"messageTable": {
		"ja": {
			"messageTable": [
				{
					"code": "8200",
					"format": "8200",
					"template": "<%= message %>"
				},
				{
					"code": "8201",
					"format": "8200",
					"template": "クラス '<%= class_name %>' を対象とした ansible プレイブック '<%= playbook %>'の実行を開始しました。"
				},
				{
					"code": "8202",
					"format": "8200",
					"template": "クラス '<%= class_name %>' を対象とした ansible プレイブック '<%= playbook %>'の実行がエラーになりました。： <%= message %>"
				},
				{
					"code": "8203",
					"format": "8200",
					"template": "クラス '<%= class_name %>' を対象とした ansible プレイブック '<%= playbook %>'の実行を終了しました。"
				},
				{
					"code": "8204",
					"format": "8200",
					"template": "クラス '<%= class_name %>' には対象となるデータがありませんでしたので、タスクを実行しませんでした。"
				},
				{
					"code": "8205",
					"format": "8200",
					"template": "プレイブック '<%= playbook %>'のサマリ： <%= stats %>"
				},
				{
					"code": "8206",
					"format": "8200",
					"template": "プレイ <%= play_name %> の実行を開始しました。"
				},
				{
					"code": "8207",
					"format": "8200",
					"template": "プレイ <%= play_name %> の実行を終了しました。"
				},
				{
					"code": "8208",
					"format": "8200",
					"template": "タスク <%= task_name %> の実行を開始しました。"
				},
				{
					"code": "8209",
					"format": "8200",
					"template": "タスク <%= task_name %> の実行を終了しました。"
				},
				{
					"code": "8210",
					"format": "8200",
					"template": "要素 <%= item %> について対象 '<%= host_name %>' に繰り返しタスク <%= task_name %> を実行しましたが失敗しました<%= message %>"
				},
				{
					"code": "8211",
					"format": "8200",
					"template": "要素 <%= item %> について対象 '<%= host_name %>' への繰り返しタスク <%= task_name %> をスキップしました"
				},
				{
					"code": "8212",
					"format": "8200",
					"template": "要素 <%= item %> について対象 '<%= host_name %>' への繰り返しタスク <%= task_name %> を実行しました"
				},
				{
					"code": "8213",
					"format": "8200",
					"template": "要素 <%= item %> について対象 '<%= host_name %>' への繰り返しタスク <%= task_name %> は処理済みでした"
				},
				{
					"code": "8214",
					"format": "8200",
					"template": "対象 '<%= host_name %>' にタスク <%= task_name %> を実行しましたが失敗しました<%= message %>"
				},
				{
					"code": "8215",
					"format": "8200",
					"template": "対象 '<%= host_name %>' にタスク <%= task_name %> をスキップしました"
				},
				{
					"code": "8216",
					"format": "8200",
					"template": "対象 '<%= host_name %>' にタスク <%= task_name %> を実行しました"
				},
				{
					"code": "8217",
					"format": "8200",
					"template": "対象 '<%= host_name %>' にタスク <%= task_name %> は処理済みでした"
				},
			]
		},
		"en": {
		}
	},
	"messagePattern": [
		{
			"format": "8200",
			"template": "<%= message %>"
		}
	]
}
