"""Writing outputs. JSON files sent to the dashboard are {rows, meta}: meta carries the code that produced
the rows, so the dashboard can show how every number was computed."""
import json
import os

from . import ROOT, SOURCE


def _text(path):
    with open(path, encoding='utf-8') as fh:
        return fh.read()


def code_meta(script_path):
    files = [script_path, os.path.join(ROOT, 'clasico', 'events.py')]
    meta = [{'label': os.path.relpath(f, ROOT), 'value': _text(f), 'type': 'code', 'lang': 'python'} for f in files]
    return meta + [{'label': 'Input', 'value': SOURCE}]


def read_json(path):
    with open(path, encoding='utf-8') as fh:
        return json.load(fh)


def write_json(path, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as fh:
        json.dump(obj, fh, ensure_ascii=False)


def write_rows(path, rows, script_path):
    write_json(path, {'rows': rows, 'meta': code_meta(script_path)})


def read_rows(path):
    d = read_json(path)
    return d['rows'] if isinstance(d, dict) else d
