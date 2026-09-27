"""Run the full THz tests, compile the manuscript and inspect PDF geometry."""
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT.parents[1]/'00_research_portfolio/scripts'))
import validate_revision_0908 as validation
validation.OUT=ROOT/'results/no2_three_routes/validation'
if __name__=='__main__':validation.main()
