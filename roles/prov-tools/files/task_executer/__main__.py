#!/usr/bin/env python3

import connexion

from task_executer import encoder


def main():
    app = connexion.App(__name__, specification_dir='./models/openapi/')
    app.app.json_encoder = encoder.JSONEncoder
    app.add_api('openapi.yaml',
                arguments={'title': 'Custom Task Executer'},
                pythonic_params=True)
    app.run(port=8099)


if __name__ == '__main__':
    main()
