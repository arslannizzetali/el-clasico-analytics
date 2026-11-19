"""Structured logging (standard library only, so the reference pipeline still needs nothing installed).

    from clasico.log import get_logger
    log = get_logger('load_db')
    log.info('loaded match', extra={'match_id': 3750201, 'events': 3612})

Two formats, chosen with LOG_FORMAT:
  text (default)  2026-11-19T17:40:02Z INFO load_db loaded match match_id=3750201 events=3612
  json            {"ts": "2026-11-19T17:40:02Z", "level": "INFO", "logger": "load_db", "msg": "loaded match", "match_id": 3750201, ...}

Logs go to stderr; stdout stays free for data. LOG_LEVEL sets the level (default INFO).
"""
import json
import logging
import os
import sys
import time

# attributes every LogRecord has; anything else on a record came from `extra=` and is a structured field
_STANDARD = set(vars(logging.LogRecord('', 0, '', 0, '', (), None))) | {'message', 'asctime', 'taskName'}


def fields(record):
    return {k: v for k, v in vars(record).items() if k not in _STANDARD}


class _Formatter(logging.Formatter):
    converter = time.gmtime

    def __init__(self, as_json):
        super().__init__()
        self.as_json = as_json

    def format(self, record):
        ts = self.formatTime(record, '%Y-%m-%dT%H:%M:%SZ')
        extra = fields(record)
        if self.as_json:
            out = {'ts': ts, 'level': record.levelname, 'logger': record.name, 'msg': record.getMessage(), **extra}
            if record.exc_info:
                out['exc'] = self.formatException(record.exc_info)
            return json.dumps(out, ensure_ascii=False, default=str)
        kv = ' '.join(f'{k}={v}' for k, v in extra.items())
        line = f'{ts} {record.levelname} {record.name} {record.getMessage()}' + (' ' + kv if kv else '')
        return line + ('\n' + self.formatException(record.exc_info) if record.exc_info else '')


def get_logger(name):
    log = logging.getLogger('clasico.' + name)
    root = logging.getLogger('clasico')
    if not root.handlers:
        h = logging.StreamHandler(sys.stderr)
        h.setFormatter(_Formatter(os.environ.get('LOG_FORMAT', 'text').lower() == 'json'))
        root.addHandler(h)
        root.setLevel(os.environ.get('LOG_LEVEL', 'INFO').upper())
        root.propagate = False
    return log
