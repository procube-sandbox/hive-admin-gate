# クラス定義

本システムで ID Manager に定義されているクラスについて説明します。

{% for class in md_data.result %}
## {{ class.displayName }}({{ class.name }})
{%   if class.desciption is defined %}
{{ class.displayName }}({{ class.name }}) は{{ class.description }}です。
{%   endif %}
{%   if class.isNestedObject %}
このクラスは内包オブジェクトです。
{%   else %}
クラスのキー属性は{{ class.keyProperty }} です。
{%   endif %}
{%   if class.outputLdapSchema %}
このクラスでは対応する LDAP スキーマが自動的に設定されます。
{%     if class.ldapSuperClass %}
LDAPスキーマの親クラスは {{ class.ldapSuperClass }} です。
{%     endif %}
{%   endif %}
このクラスの属性は以下のとおりです。
{%   for property in class.propertyDefinitionList %}
### {{ property.displayName }}({{ property.name }})
{%     if property.description is defined %}
{{ property.displayName }}({{ property.name }}) は{{ property.description }}です。
{%     endif %}
| データ型|{{ property.type }}{% if property.isArray | default(false) %}の配列{% endif %}|
|----|----------------|
|必須|{% if property.required | default(false) %}:o:{% else %}:x:{% endif %}|
|一意|{% if property.unique| default(false) %}:o:{% if property.uniqueIgnoreCase | default(false) %}（大文字小文字無視）{% endif %}{% else %}:x:{% endif %}|
{%     if property.maxLen is defined %}
| 最大長|{{ property.maxLen }}|
{%     endif %}
{%     if property.minLen is defined %}
| 最小長|{{ property.minLen }}|
{%     endif %}
{%   endfor %}
{% endfor %}
