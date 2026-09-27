"""Percentage reporting must distinguish detection, false alarms and error."""
from pathlib import Path
import sys
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from evaluate_joint_receiver import percentage_metrics


def test_zero_recall_keeps_misses_and_a_nonzero_confidence_upper_bound():
    result=percentage_metrics(np.zeros(100),np.zeros(100),1.,2.)
    assert result['recall_pct']==0 and result['miss_rate_pct']==100
    assert result['recall_ci95_upper_pct']>0
    assert result['balanced_accuracy_pct']==50
    assert result['relative_rmse_pct']==100
    assert np.isnan(result['precision_at_50pct_prevalence_pct'])


def test_detection_precision_is_not_concentration_accuracy():
    result=percentage_metrics(np.full(100,3.),np.r_[np.zeros(90),np.full(10,3.)],1.,2.)
    assert result['recall_pct']==100 and result['false_alarm_pct']==10
    assert np.isclose(result['precision_at_50pct_prevalence_pct'],10000/110)
    assert result['relative_bias_pct']==50 and result['relative_rmse_pct']==50
    assert result['recall_ci95_lower_pct']<100


def test_miss_rate_and_negative_estimates_are_not_hidden():
    result=percentage_metrics(np.array([-2.,0.,2.,4.]),np.array([0.,0.,0.,4.]),1.,2.)
    assert result['recall_pct']==50 and result['miss_rate_pct']==50
    assert result['negative_estimate_pct']==25
    assert result['specificity_pct']==75
    assert result['relative_rmse_pct']>100
