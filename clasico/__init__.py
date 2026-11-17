"""El Clásico tactical analysis: shared helpers for StatsBomb open data."""
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(ROOT, 'data', 'raw')
PROCESSED = os.path.join(ROOT, 'data', 'processed')
TEAMS = ('Barcelona', 'Real Madrid')
OPP = {'Real Madrid': 'Barcelona', 'Barcelona': 'Real Madrid'}
PERIODS = ('2005-09', '2009-13', '2013-17', '2017-21')
# Second grouping of the matches: Barcelona's coach on the day, in chronological order {StatsBomb name: label}
BARCELONA_COACHES = {
    'Frank Rijkaard': 'Rijkaard', 'Pep Guardiola': 'Guardiola', 'Tito Vilanova': 'Vilanova',
    'Gerardo Martino': 'Martino', 'Luis Enrique': 'Luis Enrique', 'Ernesto Valverde': 'Valverde',
    'Quique Setién': 'Setién', 'Ronald Koeman': 'Koeman',
}
COACH_GROUPS = tuple(BARCELONA_COACHES.values())
SOURCE = 'StatsBomb Open Data (github.com/statsbomb/open-data), La Liga 2005/06-2020/21, 29 Real Madrid - Barcelona matches'
