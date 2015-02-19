# -*- coding: utf-8 -*-
"""
CLI Tool for Paessler's PRTG (http://www.paessler.com/)
"""

import argparse
import os
import logging
from prtg.client import Client
from prettytable import PrettyTable


def load_config():

    endpoint = None
    username = None
    password = None

    try:
        endpoint = os.environ['PRTGENDPOINT']
        username = os.environ['PRTGUSERNAME']
        password = os.environ['PRTGPASSWORD']
    except KeyError as e:
        print('Unable to load environment variable: {}'.format(e))
        exit(1)

    return endpoint, username, password


class CliResponse(object):

    def __init__(self, response, mode='pretty', sort_by=None):
        self.mode = mode
        self.sort_by = sort_by
        self.response = response

        columns = set()

        for item in self.response:
            for key, value in item.__dict__.items():
                columns.add(key)
                if isinstance(value, list):
                    item.__setattr__(key, ' '.join(value))
                if isinstance(value, int):
                    item.__setattr__(key, str(value))

        self.columns = list(columns)
        self.columns.sort()

    def _csv(self):

        out = ','.join(self.columns) + '\n'
        _lst = list()

        for resp in self.response:
            _lst.append(','.join([resp.__getattribute__(x) for x in self.columns]))
        _lst.sort()

        return out + '\n'.join(_lst)

    def _pretty(self):

        p = PrettyTable(self.columns)

        for resp in self.response:
            p.add_row([resp.__getattribute__(x) for x in self.columns])

        return p.get_string(sortby=self.sort_by)

    def __str__(self):
        if self.mode == 'pretty':
            return self._pretty()
        if self.mode == 'csv':
            return self._csv()


def get_parents_filter(response):
    parent_ids = [str(x.parentid) for x in response]
    return {'filter_objid': '&filter_objid='.join(parent_ids)}


def get_table_output(client, content, filter_string=None, bulk_filter=None, columns=None):
    q = client.table(content=content, filter_string=filter_string, bulk_filter=bulk_filter, columns=columns)
    client.query(q)
    return q.response


def modify_property(prop, value, target):
    target.__setattr__(prop, value)


def tag_targets(targets, new_tags):
    for target in targets:
        modify_property('tags', new_tags.split(','), target)


def get_args():
    parser = argparse.ArgumentParser(description='PRTG Command Line Interface')
    parser.add_argument('command', help='command', choices=['ls', 'status', 'refresh', 'update'])
    parser.add_argument('-c', '--content', default='devices', help='content (devices or sensors)')
    parser.add_argument('-l', '--level', help='Logging level', default='INFO')
    parser.add_argument('-f', '--format', help='Display format', default='pretty')
    parser.add_argument('-s', '--sort', help='Sort by column', default='objid')
    parser.add_argument('-p', '--parents', help='Lookup devices by sensors', action='store_true')
    parser.add_argument('-r', '--regex', help='Filter by regular expression', default=None)
    parser.add_argument('-a', '--attribute', help='Specify the attribute to match', default=None)
    parser.add_argument('-u', '--update', help='Update the specified attribute', default=None)
    parser.add_argument('--commit', help='Commit changes to PRTG', default=None)
    return parser.parse_args()


def main():
    """
    Parse commandline arguments for PRTG-CLI.
    :return: None
    """

    args = get_args()

    logging.basicConfig(level='DEBUG')

    endpoint, username, password = load_config()

    client = Client(endpoint=endpoint, username=username, password=password)

    if args.command == 'refresh':
        logging.warning('Refreshing PRTG content cache..')
        client.refresh(content='devices')
        client.refresh(content='sensors')

    if args.command == 'ls':
        content = client.content(args.content, parents=args.parents, regex=args.regex, attribute=args.attribute)
        resp = CliResponse(content, mode=args.format, sort_by=args.sort)
        print(resp)

    if args.command == 'update':
        attribute, value = args.update.split('=')
        content = client.content(args.content, parents=args.parents, regex=args.regex, attribute=args.attribute)
        client.update(content=content, attribute=attribute, value=value)

    if args.command == 'commit':
        pass

    if args.command == 'status':
        status = client.status()
        resp = CliResponse(status, mode=args.format)
        print(resp)


if __name__ == '__main__':
    main()