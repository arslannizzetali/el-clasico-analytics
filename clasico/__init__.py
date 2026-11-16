"""El Clásico tactical analysis: shared helpers for StatsBomb open data."""
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(ROOT, 'data', 'raw')
PROCESSED = os.path.join(ROOT, 'data', 'processed')
TEAMS = ('Barcelona', 'Real Madrid')
OPP = {'Real Madrid': 'Barcelona', 'Barcelona': 'Real Madrid'}
PERIODS = ('2005-09', '2009-13', '2013-17', '2017-21')
SOURCE = 'StatsBomb Open Data (github.com/statsbomb/open-data), La Liga 2005/06-2020/21, 29 Real Madrid - Barcelona matches'
