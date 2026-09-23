import sys
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from thz_isac.retrieval_metrics import detection_metrics,concentration_errors


def test_detection_denominators_and_undefined_precision():
    result=detection_metrics([4,3,0,0],[3,0,0,0],2)
    assert (result['tp'],result['fp'],result['fn'],result['tn'])==(2,1,2,3)
    assert result['precision_pct']==pytest.approx(200/3)
    assert result['recall_pct']==50
    assert result['false_positive_rate_pct']==25
    empty=detection_metrics([0,0],[0,0],2)
    assert empty['precision_pct'] is None and empty['recall_pct']==0


def test_percentage_errors_use_truth_and_are_undefined_at_zero():
    result=concentration_errors([8,12],10)
    assert result['mae_ug_m3']==2 and result['rmse_pct_of_truth']==20
    assert result['within_20pct_of_truth_pct']==100
    zero=concentration_errors([-1,1],0)
    assert zero['rmse_ug_m3']==1 and zero['mae_pct_of_truth'] is None
    assert zero['negative_estimate_pct']==50
