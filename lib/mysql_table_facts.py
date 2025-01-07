#!/usr/bin/python
# -*- coding: utf-8 -*-


DOCUMENTATION = """
---
module: mysql_table_fact.py
author:
    - 'Mitsuru Nakakawaji'
short_description: Insert/update/remove rows in a mysql table.
description:
  - This module sets values in a mysql table, or insert records. Useful for webapplications that store configurations
     in database.
     The alomost codes are imported from https://github.com/zauberpony/ansible-mysql-query.
     The original code is published as GPLv3. So, the license of this code is also GPLv3.
options:
  db:
    required: True
    description:
      - database name
  table:
    required: True
    description:
      - table name where to insert/update/delete records
  login_host:
    required: False
    description:
      - the host name or ip address of database server.
  login_user:
    required: False
    default: root
    description:
      - the user account to access the database.
  login_password:
    required: False
    description:
      - the password for login_user.
  login_unix_socket:
    required: False
    description:
      - 'location of UNIX socket. Default: use default location or TCP for remote hosts'
  columns:
    required: False
    default: '*'
    description:
      - 'columns of projection: SQL select statement format'
  filter:
    required: False
    description:
      - 'filter for selection: SQL WHERE phrase format'
  html_fields:
    required: False
    type: list
    description: 'list of name of field that value is a html'
"""

EXAMPLES = """
- name: update a row
  mysql_query.py:
    db: ansible-playbook-example
    table: simple_table
    login_host: ::1
    login_user: root
    login_password: password
    identifiers:
      identifier1: 4
      identifier2: 'eight'
    values:
      value1: 16
      value2: 'sixteen plus 1'
    defaults:
      default1: can be anything, will be ignored for update
      default2: will not change

- name: insert a row
  mysql_query.py:
    db: ansible-playbook-example
    table: simple_table
    login_host: ::1
    login_user: root
    login_password: password
    identifiers:
      identifier1: 14
      identifier2: 'eighteen'
    values:
      value1: 115
      value2: 'one-hundred-sixteen'
    defaults:
      default1: 125
      default2: one-hundred-2
"""

from contextlib import closing

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.database import mysql_quote_identifier

# make mysql-query backward compatible with ansible < 2.7.2
try:
    from ansible.module_utils.mysql import mysql_connect, mysql_driver, mysql_driver_fail_msg
except ImportError:
    from ansible.module_utils.mysql import mysql_connect, mysqldb_found
    if mysqldb_found:
        import MySQLdb as mysql_driver
    else:
        mysql_driver = None
        mysql_driver_fail_msg = 'The MySQL-python module is required.'


try:
  from html.parser import HTMLParser
except ImportError:
  HTMLParser = None

from ansible.module_utils._text import to_native

import json
import re

all_space_re = re.compile('^\s*$')
no_tag_children_tags = ['hr', 'br', 'img']

class DictHTMLParser(HTMLParser):
    def __init__(self, module):
        HTMLParser.__init__(self)
        self.stack = []
        self.module = module

    def get_root(self):
        return self.root

    def handle_starttag(self, tag, attrs):
        if self.stack and self.stack[len(self.stack) - 1]['tag'] in no_tag_children_tags:
            self.handle_endtag(self.stack[len(self.stack) - 1]['tag'])
        self.module.debug('start tag tag={0} level={1}'.format(tag, len(self.stack)))
        data = dict(tag=tag)
        if attrs:
            data['tag_attrs'] = dict(attrs)
        self.stack.append(data)

    def handle_endtag(self, tag):
        if self.stack[len(self.stack) - 1]['tag'] != tag:
          self.handle_endtag(self.stack[len(self.stack) - 1]['tag'])
        data = self.stack.pop()
        if 'tag_children' in data and len(data['tag_children']) == 1:
          data['tag_children'] = data['tag_children'][0]
        if len(self.stack) > 0:
            target = self.stack[len(self.stack) - 1]
            if 'tag_children' not in target:
                target['tag_children'] = []
            target['tag_children'].append(data)
        else:
            self.root = data
        self.module.debug('end tag tag={0} level={1}'.format(tag, len(self.stack)))

    def handle_data(self, data):
        if all_space_re.match(data):
            return
        target = self.stack[len(self.stack) - 1]
        if 'tag_children' not in target:
            target['tag_children'] = []
        target['tag_children'].append(data)


def replace_html_field(data, module):
  module.log("data=" + str(data))
  for html_field in module.params['html_fields']:
    if html_field in data:
      if data[html_field]:
        parser = DictHTMLParser(module)
        parser.feed('<root>{0}</root>'.format(data[html_field]))
        data[html_field] = parser.get_root()['tag_children']
      else:
        data.pop(html_field)
  return data

class MysqlTable(AnsibleModule):
  def __init__(self):
    argument_spec = dict(
      filter=dict(required=False),
      table=dict(required=True),
      login_password=dict(required=False, no_log=True),
      login_unix_socket=dict(required=False),
      login_user=dict(default='root',required=False),
      login_host=dict(required=False),
      db=dict(required=True),
      columns=dict(default='*',required=False),
      html_fields=dict(required=False, type='list')
    )
    super(MysqlTable, self).__init__(argument_spec=argument_spec, supports_check_mode=True)
    self.db_connection = None
    self.exc_value = None
    self.records = []

  def build_connection_parameter(self):
    """
    fetch mysql connection parameters consumable by mysqldb.connect from module args or ~/.my.cnf if necessary
    :return:
    :rtype: dict
    """
    # map: (ansible_param_name, mysql.connect's name)
    param_name_map = [
        ('login_user', 'user'),
        ('login_password', 'passwd'),
        ('db', 'db'),
        ('login_host', 'host'),
        ('login_port', 'port'),
        ('login_unix_socket', 'unix_socket')
    ]

    t = [(mysql_name, self.params[ansible_name])
         for (ansible_name, mysql_name) in param_name_map
         if ansible_name in self.params and self.params[ansible_name]
         ]
    self.connection_parameter = dict(t)
    self.connection_parameter['cursorclass'] = mysql_driver.cursors.DictCursor

  def __enter__(self):
    if self.db_connection is not None:
      raise AssertionError('connection is already opened')
    self.build_connection_parameter()
    try:
      self.db_connection = mysql_driver.connect(**self.connection_parameter)
    except Exception as e:
      raise StandardError("Error connecting to mysql database: parameter = {0}, error = {1}".format(self.connection_parameter, e))
    self.debug('Connected to db:{0}'.format(self.connection_parameter))


  def __exit__(self, exc_type, exc_value, traceback):
    self.exc_value = exc_value
    if self.db_connection:
      try:
        self.db_connection.close()
      except Excetption as e:
        self.debug('error occured at close, but ignore it: {0}'.format(e))
      self.db_connection = None
      self.debug('Closed to db:{0}'.format(self.connection_parameter))

  def query_records(self):
    with self.db_connection.cursor() as cursor:
      table_id = mysql_quote_identifier(self.params['table'], 'table')
      query = "select {columns} from {table}".format(table=table_id, columns=self.params['columns'])
      if self.params['filter']:
        query += ' where ' + self.params['filter']
      res = cursor.execute(query)
      self.debug('execute query "{0}" count={1}'.format(query, res))
      self.records = cursor.fetchall()

  def process_task(self):
    if self.params['html_fields'] and HTMLParser is None:
        self.fail_json(msg='The HTMLParser module is required when use html_fields.')

    self.query_records()
    if self.params['html_fields']:
      self.records = map(lambda record: replace_html_field(record, self), self.records)

  def exit_process(self):
    if self.exc_value:
      self.fail_json(msg=str(self.exc_value))
    else:
      self.exit_json(records=self.records)
    # never reach here

def main():
  mysql_table = MysqlTable()
  if mysql_driver is None:
      mysql_table.fail_json(msg=mysql_driver_fail_msg)
  with mysql_table:
    mysql_table.process_task()
  mysql_table.exit_process()
  # never reach here

if __name__ == '__main__':
    main()
