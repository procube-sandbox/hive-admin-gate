#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright: (c) 2019, Mitsuru Nakakawaji <mitsuru@procube.jp>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

"""
ID Manager inventory: dynamic inventory plugin for ID Manager
"""

from ansible.plugins.inventory import BaseInventoryPlugin, Cacheable
from ansible.errors import AnsibleParserError, AnsibleError
from ansible.module_utils._text import to_text
from ansible.module_utils.urls import open_url
import ansible.module_utils.six.moves.urllib.error as urllib_error
import json
import socket
import http.client as httplib
import os

DOCUMENTATION = r'''
  name: idm_inventory
  plugin_type: inventory
  author:
    - Mitsuru Nakakawaji (mitsuru@procube.jp)
  short_description: Inventory fromID Manager
  description:
    - Inventory from ID Manager
  extends_documentation_fragment:
    - inventory_cache
  options:
    plugin:
      description: token that ensures this is a source file for the 'idm_inventory' plugin.
      required: True
      choices: ['idm_inventory']
    host:
      description: ID Manager host name
      default: localhost
    port:
      description: ID Manager port
      default: 8090
    groups:
      description: stage list
      required: True
      suboptions:
        name:
          description: name of group
          required: True
        filter:
          description: filter python expression for the interface
          type: dict
          default: "True"
    interface:
      description: name of interface
      required: True
    class_name:
      description: class name for IDM_IFFILE_ environment variable
      required: True
    host_name_property:
      description: property name used as inventory hostname
      required: True
    properties:
      description: filter for the interface
      default: []
      type: list
      elements: string
    system_account:
      description: system account name for api access
      default: IDM_AUTO_BUILDER
    cache:
      description: use cache for data from ID IDManager
      default: False
'''

EXAMPLES = r'''
plugin: idm_inventory
interface: hostProvisioningIf
host_name_property: FQDN
class_name: host
groups:
- name: fixedip
  filter: "IPAddressType in ['ManualSettingFixedIP', 'DHCPBasedFixedIP']"
- name: usedhcp
  filter: "IPAddressType in ['DHCPAssignedIP', 'DHCPBasedFixedIP']"
- name: trunk
  filter: "ConnectMode == 'TrunkMode'"
- name: floor
  filter: "Type == 'SW'"
'''


class InventoryModule(BaseInventoryPlugin, Cacheable):

  NAME = 'idm_inventory'  # used internally by Ansible, it should match the file name but not required

  def __init__(self):
    super(InventoryModule, self).__init__()
    self.sites = []

  def verify_file(self, path):
    ''' return true/false if this is possibly a valid file for this plugin to consume '''
    valid = False
    if super(InventoryModule, self).verify_file(path):
      # base class verifies that file exists and is readable by current user
      if path.endswith(('.yaml', '.yml')):
        valid = True
    return valid

  def parse(self, inventory, loader, path, cache=True):
    super(InventoryModule, self).parse(inventory, loader, path, cache)
    # self.load_cache_plugin()
    self._read_config_data(path)
    groups = self.get_option('groups')
    for group in groups:
      if 'name' not in group:
        raise AnsibleParserError(f'name is not defined in group: {group}')
      self.inventory.add_group(group['name'])
    hosts_list = self.call_idm()
    host_name_property = self.get_option('host_name_property')
    for host in hosts_list:
      if host_name_property not in host:
        raise AnsibleParserError(f'host name property {host_name_property} is not defined in host: {host}')
      host_name = host.get(host_name_property)
      self.inventory.add_host(host_name, group='all')
      for k, v in host.items():
        self.inventory.set_variable(host_name, k, v)
      for group in groups:
        try:
          in_group = eval(group.get('filter', 'True'), host)
        except SyntaxError as se:
          raise AnsibleParserError(f'filter property of group {json.dumps(group)} cause error: {str(se)} at offset{se.offset}')
        if in_group:
          self.inventory.add_host(host_name, group=group['name'])

  def call_idm(self):
    interface = self.get_option('interface')
    if interface is None:
      raise AnsibleParserError(f'interface property is required')
    class_name = self.get_option('class_name')
    if class_name is None:
      raise AnsibleParserError(f'class_name property is required')
    url = 'http://' + self.get_option('host') + ':' + str(self.get_option('port')) + '/IDManager/' + interface
    results = None
    cache_key = self.get_cache_key(url)
    # get the user's cache option to see if we should save the cache if it is changing
    user_cache_setting = self.get_option('cache')
    # read if the user has caching enabled and the cache isn't being refreshed
    attempt_to_read_cache = user_cache_setting and self.use_cache
    # attempt to read the cache if inventory isn't being refreshed and the user has caching enabled
    if attempt_to_read_cache:
      try:
        results = self._cache[cache_key]
        need_to_fetch = False
      except KeyError:
        # occurs if the cache_key is not in the cache or if the cache_key expired
        # we need to fetch the URL now
        need_to_fetch = True
    else:
        # not reading from cache so do fetch
        need_to_fetch = True
    if need_to_fetch:
      temp_prov_file = os.environ.get('IDM_IFFILE_' + class_name)
      if temp_prov_file:
        self.display.v("Load from: " + temp_prov_file)
        with open(temp_prov_file, encoding='utf-8') as prov_file:
          raw_data = prov_file.read()
      else:
        self.display.v("Fetching: " + url)
        headers = {'Accept': 'application/json charset=utf-8', 'HTTP_SYSTEMACCOUNT': self.get_option('system_account')}
        try:
          response = open_url(url, method='GET', headers=headers, timeout=1800)
        except (ConnectionError, ValueError) as e:
          raise AnsibleError(f'ID Mangaer API ConnecitonError/ValueError error: {e}')
        except urllib_error.HTTPError as e:
          raise AnsibleError(f'ID Mangaer API HTTP error: {e}')
        except urllib_error.URLError as e:
          raise AnsibleError(f'ID Mangaer API Request failed: {e}')
        except socket.error as e:
          raise AnsibleError(f'ID Mangaer API Request Connection failure: {e}')
        except httplib.BadStatusLine as e:
          raise AnsibleError(f'ID Mangaer API Request Connection failure: connection was closed before a valid response was received: {e}')
        except Exception as e:
          raise AnsibleError(f'ID Mangaer API Request An unknown error occurred: {e}')
        try:
          raw_data = to_text(response.read(), errors='surrogate_or_strict')
        except UnicodeError:
          raise AnsibleError("Incorrect encoding of fetched payload from ID Manager API.")

      try:
        results = json.loads(raw_data)
      except ValueError:
        raise AnsibleError("Incorrect JSON payload: %s" % raw_data)

      # put result in cache if enabled
      if user_cache_setting:
        self._cache[cache_key] = results
    return results


# def _byteify(data, ignore_dicts=False):
#   # if this is a unicode string, return its string representation
#   if isinstance(data, str):
#     return data.encode('utf-8')
#   # if this is a list of values, return list of byteified values
#   if isinstance(data, list):
#     return [_byteify(item, ignore_dicts=True) for item in data]
#   # if this is a dictionary, return dictionary of byteified keys and values
#   # but only if we haven't already byteified it
#   if isinstance(data, dict) and not ignore_dicts:
#     return {
#         _byteify(key, ignore_dicts=True): _byteify(value, ignore_dicts=True)
#         for key, value in data.items()
#     }
#   # if it's anything else, return it in its original form
#   return data
