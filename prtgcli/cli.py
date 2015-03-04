# -*- coding: utf-8 -*-
"""
CLI Tool for Paessler's PRTG (http://www.paessler.com/)
"""

import argparse
import os
import logging
import yaml

from prtg.client import Client
from prtg.models import Query, NameMatch
from prettytable import PrettyTable


def load_config():

    endpoint = os.getenv('PRTGENDPOINT', 'http://192.168.59.103')
    username = os.getenv('PRTGUSERNAME', 'prtgadmin')
    password = os.getenv('PRTGPASSWORD', 'prtgadmin')
    return endpoint, username, password


def load_rules(rule_path):
    return yaml.load(open(rule_path).read())['rules']


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
        # TODO: Better filtering
        self.columns = [x for x in self.columns if not any([x == 'active', x == 'type'])]
        self.columns.sort()

    def _csv(self):

        out = ','.join(self.columns) + '\n'
        _lst = list()

        for resp in self.response:
            try:
                _lst.append(','.join([resp.__getattribute__(x) for x in self.columns]))
            except AttributeError or TypeError:
                pass
        _lst.sort()

        return out + '\n'.join(_lst)

    def _pretty(self):

        p = PrettyTable(self.columns)

        for resp in self.response:
            try:
                p.add_row([resp.__getattribute__(x) for x in self.columns])
            except AttributeError or TypeError:
                pass

        return p.get_string(sortby=self.sort_by)

    def __str__(self):
        if self.mode == 'pretty':
            return self._pretty()
        if self.mode == 'csv':
            return self._csv()


def apply_rules(client, rules, devices):

    def update_list_value(prop, value):
        a = device.__getattribute__(prop)
        return ' '.join(a) + ' ' + ' '.join(value)

    def get_value():
        if rule['update']:
            v = update_list_value(rule['prop'], rule['value'])
        else:
            v = ' '.join(rule['value'])
        return v

    queries = list()
    for device in devices:
        for rule in rules:
            query = Query(
                client, target='setobjectproperty', objid=device.objid, name=rule['attribute'], value=get_value()
            )
            if NameMatch(device, **rule).evaluate():
                queries.append(query)



def get_args():
    parser = argparse.ArgumentParser(description='PRTG Command Line Interface')
    parser.add_argument('command', help='command', choices=['ls', 'status', 'apply'])
    parser.add_argument('-c', '--content', default='devices', help='content (devices or sensors)')
    parser.add_argument('-l', '--level', help='Logging level', default='INFO')
    parser.add_argument('-f', '--format', help='Display format', default='pretty')
    parser.add_argument('-r', '--rules', help='Modify objects based on rule set', default='../rules.yaml')
    return parser.parse_args()


def main():
    """
    Parse commandline arguments for PRTG-CLI.
    :return: None
    """

    args = get_args()

    logging.basicConfig(level=args.level)

    endpoint, username, password = load_config()

    client = Client(endpoint=endpoint, username=username, password=password)

    if args.command == 'ls':
        query = Query(client=client, target='table', content=args.content)
        print(CliResponse(client.query(query), mode=args.format))

    if args.command == 'status':  # TODO: Fix.
        query = Query(client=client, target='getstatus')
        client.query(query)
        print(CliResponse(client.query(query), mode=args.format))

    if args.command == 'apply':
        rules = load_rules(args.rules)
        query = Query(client=client, target='table', content='devices')
        devices = client.query(query)
        apply_rules(client, rules, devices)


if __name__ == '__main__':
    main()