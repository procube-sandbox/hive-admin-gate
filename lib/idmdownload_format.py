#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright: (c) 2019, Mitsuru Nakakawaji <mitsuru@procube.jp>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

# TODO: METADATA, DOCUMENT, EXAMPLE should be written
# https://docs.ansible.com/ansible/latest/dev_guide/developing_modules_documenting.html#ansible-metadata-block

# to test this module
# ansible -m idm_fact -M . -c docker -i ,idm -a 'interface=_classes/_classDefinition' idm
from ansible.module_utils.basic import AnsibleModule
import json
import re

class IDMDownloadFormat(AnsibleModule):
  def __init__(self):
    argument_spec = dict(
      mongodb_data=dict(required=True,type='list',elements='dict'),
      mariadb_data=dict(required=True,type='list',elements='dict'),
      targets=dict(required=True,type='list',elements='dict'),
    )
    super(IDMDownloadFormat, self).__init__(argument_spec=argument_spec, supports_check_mode=True)

  def process_task(self):
    phases = []

    # change structure
    mariadb_data = self.params['mariadb_data']
    is_tables = {}
    for dataset in mariadb_data:  
      is_tables[dataset["item"]["name"]] = dataset["records"]

    # is_tables = list(map(lambda o: {"name": o["item"]["name"], "records": o["records"]}, mariadb_data))

    mongodb_data = self.params['mongodb_data']
    phases = {}
    for dataset in mongodb_data:
      phase = dataset["item"][0]["name"]
      if phase not in phases:
        phases[phase] = {}

      if_name = dataset["item"][1]["name"]
      phases[phase][if_name] = dataset["result"]

    result = {
      'phases_data': phases,
      'is_tables_data': is_tables
    }

    # replace values
    targets = self.params['targets']
 
    self.changed_list = []
    stack = []

    self.replace(result, targets, self.changed_list, stack)
    return result

  def replace(self, instance, targets, changed_list, stack):
    if type(instance) is dict:
      result = self.replace_dict(instance, targets, changed_list, stack)
    elif type(instance) is list:
      result = self.replace_list(instance, targets, changed_list, stack)
    else:
      result = self.replace_value(instance, targets, changed_list, stack)
    return result

  def replace_dict(self, instance, targets, changed_list, stack):
    for key in instance:
      stack.append(key)
      value = self.replace(instance[key], targets, changed_list, stack)
      instance[key] = value
      stack.pop()
    return instance

  def replace_list(self, instance, targets, changed_list, stack):
    def _replace_list(o):
      stack.append(str(o[0]))
      r = self.replace(o[1], targets, changed_list, stack)
      stack.pop()
      return r
    result = list(map(_replace_list, enumerate(instance)))
    return result
    
  def replace_value(self, value, targets, changed_list, stack):
    result = str(value)
    changed = False
    for target in targets:
      regex = target.get('regex')
      target_value = target.get('value')
      if regex and re.match(regex, result):
        result = re.sub(regex, result, '{{ ' + target['expression'] + ' }}')
        changed = True
      elif target_value and target_value in result:
        result = result.replace(target_value, '{{ ' + target['expression'] + ' }}')
        changed = True
    if changed:
      changed_list.append(".".join(stack))
    else:
      result = value
    return result

def main():
  module = IDMDownloadFormat()
  try:
    result = module.process_task()
  except Exception as e:
    module.fail_json(msg=str(e))
    # never reach here
  changed = len(module.changed_list) > 0

  module.exit_json(result=result, changed=changed, changed_list=module.changed_list)
  # never reach here

if __name__ == '__main__':
  main()