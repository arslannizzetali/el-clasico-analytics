"""El Clásico taktik analizi: StatsBomb açık verisinden ortak yardımcılar."""
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(ROOT, 'data', 'raw')
PROCESSED = os.path.join(ROOT, 'data', 'processed')
TEAMS = ('Barcelona', 'Real Madrid')
OPP = {'Real Madrid': 'Barcelona', 'Barcelona': 'Real Madrid'}
SOURCE = 'StatsBomb Open Data (github.com/statsbomb/open-data), La Liga 2005/06-2020/21, 29 Real Madrid-Barcelona maçı'
