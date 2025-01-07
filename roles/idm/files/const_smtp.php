<?php
/**
 * SMTP定数定義
 * -----------------------------------------------
 */

//SMTP設定
define('SMTP_HOST', 'smtp.email.com');
define('SMTP_PORT', 465);
define('SMTP_USER', "smtp_user@email.com");
define('SMTP_PASSWORD', "password");
define('SMTP_SSL', true); // true or false
define('SMTP_TLS', false); // true or false

// メール設定
define('TO_EMAILADDRESS', "to@email.com");
define('FROM_EMAILADDRESS', "from@email.com");
define('FROM_NAME', "送信者名");
define('MAIL_SUBJECT', "CSVファイルがアップロードされました");
