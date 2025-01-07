# coding: utf-8

from __future__ import absolute_import
import unittest

from flask import json
from six import BytesIO

from task_executer.models.request_body import RequestBody  # noqa: E501
from task_executer.models.response_body import ResponseBody  # noqa: E501
from task_executer.test import BaseTestCase


class TestTaskController(BaseTestCase):
    """TaskController integration test stubs"""

    def test_execute_task(self):
        """Test case for execute_task

        タスクを実行する
        """
        request_body = {}
        headers = { 
            'Accept': 'application/json',
            'Content-Type': 'application/json',
        }
        response = self.client.open(
            '/v1/execute_task',
            method='POST',
            headers=headers,
            data=json.dumps(request_body),
            content_type='application/json')
        self.assert200(response,
                       'Response body is : ' + response.data.decode('utf-8'))


if __name__ == '__main__':
    unittest.main()
