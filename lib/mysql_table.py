#!/usr/bin/python
# -*- coding: utf-8 -*-


DOCUMENTATION = """
---
module: mysql_table.py
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
  delete_orphands:
    required: False
    default: True
    description:
      - delete orphand records when True
  state:
    required: False
    default: update
    choices:
    - absent
    - present
    - update
    description:
    - 'mode of the action(present: ensure exist record, update: update the record, absent: ensure absent any record)'
  login_host:
    required: False
    default: ::1
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
  key_columns:
    required: true
    type: list
    elements: str
    description:
      - list of column names which are processed as key of record.
  values:
    required: false
    type: list
    elements: dict
    description:
        - list of records.
  columns:
    required: False
    default: '*'
    description:
      - 'columns of projection: SQL select statement format'
  filter:
    required: False
    description:
      - 'filter for selection: SQL WHERE phrase format'
"""

EXAMPLES = """
  - name: upload infoscoop settings
    mysql_table:
      db: iscoop
      table: "{{ item.name }}"
      key_columns: "{{ item.key_columns }}"
      values: "{{ lookup('file', source_directory + '/tables/' + item.name + '.yml') | from_yaml }}"
    loop:
    - name: is_tablayouts
      key_columns:
      - tabId
      - roleOrder
      - temp
    - name: is_portallayouts
      key_columns:
      - name
"""

# TODO: bit型で2bit 以上あるものが key_columns 指定された場合、key 文字列に変換できない
# TODO: timestamp型が key_columns 指定された場合、key 文字列に変換できない

try:
  from dictdiffer import diff
except ImportError:
  diff = None
  diff_fail_msg = 'The dictdiffer module is required.'

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.database import mysql_quote_identifier
import json
import datetime

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

from ansible.module_utils._text import to_native

class MultiKeyMap:
  def __init__(self, key_columns, module):
    self.key_columns = key_columns
    self.map_dict= {}
    self.module = module
    self.module.debug('MultiKeyMap.init called key_columns={0} type={1}'.format(key_columns, type(key_columns)))

  def set(self, value, map_dict= None, key_index = 0):
    if map_dict is None:
      map_dict= self.map_dict
    if key_index >= len(self.key_columns):
      raise AssertionError('key index {0} is out of range for key columns {1}'.format(key_index, self.key_columns))
    key = self.key_columns[key_index]
    self.module.debug('MultiKeyMap.set key = {0}'.format(key))
    if key not in value:
      self.module.debug('MultiKeyMap.set Error: {Value {0} does not have key {1}'.format(json.dumps(value, ensure_ascii=False), key))
      raise IndexError('MultiKeyMap.set: Value {0} does not have key {1}'.format(json.dumps(value, ensure_ascii=False), key))

    self.module.debug('MultiKeyMap.set key: value={0} {1} {2}'.format(value, type(value[key]), value[key] == '\x00'))
    # self.module.debug('MultiKeyMap.set key: value[{0}] = {1}'.format(key, value[key]))
    key_value = value[key]
    if key_value == '\x00' or key_value == b'\x00':
      key_value = 'bit0'
    if key_value == '\x01' or key_value == b'\x01':
      key_value = 'bit1'

    if key_index == len(self.key_columns) - 1:
      if key_value in map_dict:
        raise LookupError('MultiKeyMap.set: Value {0} has same key  with {1}'.format(json.dumps(value, ensure_ascii=False), json.dumps(map_dict[key], ensure_ascii=False)))
      map_dict[key_value] = value
      self.module.debug('MultiKeyMap.set {0} : {1} for {2}'.format(key_value, value, key))
    else:
      if key_value not in map_dict:
        map_dict[key_value] = dict()
      self.module.debug('MultiKeyMap.set recursive call for {0} for {1}'.format(key_value, key))
      self.set(value, map_dict = map_dict[key_value], key_index = key_index + 1)

  def pop(self, value, map_dict = None, key_index = 0):
    if map_dict is None:
      map_dict = self.map_dict
    if key_index >= len(self.key_columns):
      raise AssertionError('key index {0} is out of range for key columns {1}'.format(key_index, self.key_columns))
    key = self.key_columns[key_index]
    if key not in value:
      raise IndexError('MultiKeyMap.get: Key value {0} does not have key {1}'.format(json.dumps(value, ensure_ascii=False), key))
    key_value = value[key]
    if key_value == '\x00' or key_value == b'\x00':
      key_value = 'bit0'
    if key_value == '\x01' or key_value == b'\x01':
      key_value = 'bit1'
    if key_value not in map_dict:
      return None
    elif key_index == len(self.key_columns) - 1:
      return map_dict.pop(key_value)
    else:
      return self.pop(value, map_dict = map_dict[key_value], key_index = key_index + 1)

  # def len(self, map_dict = None, key_index = 0):
  #   if map_dict is None:
  #     map_dict = self.map_dict
  #   if key_index >= len(self.key_columns):
  #     raise AssertionError('key index {0} is out of range for key columns {1}'.format(key_index, self.key_columns))
  #   elif key_index == len(self.key_columns) - 1:
  #     return len(map_dict.keys())
  #   else:
  #     return sum(map(lambda key: self.len(map_dict = map_dict[key], key_index = key_index + 1), map_dict.keys()))

  def keys(self, map_dict = None, key_index = 0):
    if map_dict is None:
      map_dict = self.map_dict
    if key_index >= len(self.key_columns):
      raise AssertionError('key index {0} is out of range for key columns {1}'.format(key_index, self.key_columns))
    elif key_index == len(self.key_columns) - 1:
      for key in map_dict.keys():
        dict_val = {}
        dict_val[self.key_columns[key_index]] = key
        yield dict_val
    else:
      for my_key in map_dict.keys():
        for children_key in self.keys(map_dict = map_dict[my_key], key_index = key_index + 1):
          children_key[self.key_columns[key_index]] = my_key
          yield children_key

def str2time(record, module):
  for key in record.keys():
    try:
      record[key] = datetime.datetime.strptime(record[key], "%Y-%m-%dT%H:%M:%S")
      module.debug('value {0} of datetime field {1} is converted'.format(record[key], key))
    except:
      pass
  return record

class MysqlTable(AnsibleModule):
  def __init__(self):
    argument_spec = dict(
      filter=dict(required=False),
      table=dict(required=True),
      state=dict(required=False,default='update', choices=['absent', 'present', 'update']),
      login_password=dict(required=False, no_log=True),
      login_unix_socket=dict(required=False),
      login_user=dict(default='root',required=False),
      login_host=dict(required=False),
      db=dict(required=True),
      columns=dict(default='*',required=False),
      key_columns=dict(type='list',elements='str', required=True),
      delete_orphands=dict(required=False,type='bool',default=True),
      values=dict(type='list',elements='dict',required=True)
    )
    super(MysqlTable, self).__init__(argument_spec=argument_spec, supports_check_mode=True)
    self.db_connection = None
    self.deleted_list = []
    self.updated_list = []
    self.added_list = []
    self.exc_value = None

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
    self.connection_parameter['use_unicode'] = True
    self.connection_parameter['charset'] = 'utf8'
    self.connection_parameter['cursorclass'] = mysql_driver.cursors.DictCursor

  def __enter__(self):
    if self.db_connection is not None:
      raise AssertionError('connection is already opened')
    self.build_connection_parameter()
    try:
      self.db_connection = mysql_driver.connect(**self.connection_parameter)
    except Exception as e:
      raise Exception("Error connecting to mysql database: parameter = {0}, error = {1}".format(self.connection_parameter, e))
    self.debug('Connected to db:{0}'.format(self.connection_parameter))


  def __exit__(self, exc_type, exc_value, traceback):
    if self.db_connection:
      try:
        if exc_type is None:
          self.db_connection.commit()
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
      return cursor.fetchall()

  def build_where_clause(self):
    where = ' AND '.join(['{0} = %s'.format(mysql_quote_identifier(column, 'column')) for column in self.params['key_columns']])
    if self.params['filter']:
      where += ' AND ({0})'.format(self.params['filter'])
    return where

  def insert_record(self, target):
    with self.db_connection.cursor() as cursor:
      table_id = mysql_quote_identifier(self.params['table'], 'table')
      cols = ', '.join(map(lambda x: mysql_quote_identifier(x, 'column'), target.keys()))
      value_placeholder = ", ".join(["%s"] * len(target))
      query = "INSERT INTO {0} ({1}) VALUES ({2})".format(table_id, cols, value_placeholder)
      res = cursor.execute(query, tuple(target.values()))
      self.debug('execute query "{0}" with parameter={1} count={2}'.format(query, tuple(target.values()), res))

  def update_record(self, target):
    with self.db_connection.cursor() as cursor:
      table_id = mysql_quote_identifier(self.params['table'], 'table')
      set_clause = ', '.join(['{0} = %s'.format(mysql_quote_identifier(column, 'column')) for column in target.keys()])
      query = "UPDATE {0} SET {1} WHERE {2} LIMIT 1".format(table_id, set_clause, self.build_where_clause())
      key_values = list() #空のリスト作成
      for param in self.params['key_columns']: #for文、self.params['key_columns']をparamに入れて順にぶん回し
        value = target[param]
        if param == 'temp':
          if value == '\x00' or value == b'\x00':
            value = '0'
            key_values.append(value) #\x00なら配列に0を代入
          else:
            value = '1'
            key_values.append(value) #\x00以外なら1を代入
        else:
          key_values.append(value)
      # TODO
      values = tuple(list(target.values()) + key_values)
      # values = tuple(target.values() + map(lambda col: target[col], self.params['key_columns']))
      res = cursor.execute(query, values)
      self.debug('execute query "{0}" with parameter={1} count={2}'.format(query, values, res))

  def delete_record(self, target):
    with self.db_connection.cursor() as cursor:
      table_id = mysql_quote_identifier(self.params['table'], 'table')
      query = "DELETE FROM {0} WHERE {1}".format(table_id, self.build_where_clause())
      values = tuple(map(lambda col: target[col], self.params['key_columns']))
      res = cursor.execute(query, values)
      self.debug('execute query "{0}" with parameter={1} count={2}'.format(query, values, res))

  def do_update(self, before_map):
    state = self.params['state']
    for target in self.params['values']:
      if any(map(lambda key: key not in target, self.params['key_columns'])):
        raise IndexError('Raw {0} does not have some of key column {1}'.format(json.dumps(target, ensure_ascii=False), self.params['key_columns']))
      target = str2time(target,self)
      key = dict(map(lambda col: (col, target[col]), self.params['key_columns']))
      before_value = before_map.pop(key)
      if before_value is not None:
        if state == 'absent':
          if not self.check_mode:
            self.delete_record(key)
          self.deleted_list.append(key)
        elif state == 'update' and target != before_value:
          if not self.check_mode:
            self.update_record(target)
          diff_result = diff(target, before_value)
          self.debug('differrence of target and before value: {0}'.format(list(diff_result)))
          self.updated_list.append(key)
      elif state != 'absent':
        if not self.check_mode:
          
          self.insert_record(target)
        self.added_list.append(key)
    if len(list(before_map.keys())) > 0 and self.params['delete_orphands'] and state != 'absent' :
      for key in before_map.keys():
        self.debug('delete_orphands {0}'.format(key))
        if not self.check_mode:
          self.delete_record(key)
        self.deleted_list.append(key)

  def exit_process(self):
    changed = len(self.deleted_list) > 0 or len(self.updated_list) > 0 or len(self.added_list) > 0
    self.exit_json(changed=changed, deleted_list=self.deleted_list, updated_list=self.updated_list, added_list=self.added_list)
    # never reach here

  def process_task(self):
    before_records = self.query_records()
    before_map = MultiKeyMap(self.params['key_columns'], self)
    for target in before_records:
      try:
        before_map.set(target)
      except Exception as e:
        raise Exception('fail to build before value map from table {0}:{1}'.format(self.params['table'], e))

    self.do_update(before_map)

def main():
  mysql_table = MysqlTable()
  if mysql_driver is None:
    mysql_table.fail_json(msg=mysql_driver_fail_msg)
    # never reach here
  if diff is None:
    mysql_table.fail_json(msg=diff_fail_msg)
    # never reach here
  try:
    with mysql_table:
      mysql_table.process_task()
  except Exception as e:
    mysql_table.fail_json(msg=str(e))
    # never reach here
  mysql_table.exit_process()
  # never reach here

if __name__ == '__main__':
    main()
