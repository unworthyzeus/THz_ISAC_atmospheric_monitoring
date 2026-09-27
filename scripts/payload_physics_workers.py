"""Independent layer workers for the unchanged Voigt forward calculation."""
import sys
from pathlib import Path
import pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'src'))
from thz_isac.physical_spectroscopy import molecular_cross_section_cm2_per_molecule, DB_PER_NEPER


def initialize(source, frequency):
    global LINES, FREQUENCY
    table = pd.read_csv(source)
    LINES = {name: group for name, group in table.groupby('molecule')}
    FREQUENCY = frequency


def evaluate(task):
    name, index, temperature, pressure, density = task
    cross = molecular_cross_section_cm2_per_molecule(LINES[name], FREQUENCY, name,
        temperature_k=temperature, pressure_pa=pressure)
    return index, DB_PER_NEPER*cross*density*100
