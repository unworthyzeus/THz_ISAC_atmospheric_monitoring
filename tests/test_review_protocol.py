import numpy as np
import pandas as pd
from thz_isac.review_protocol import training_surface_conditions, calendar_block_interval


def test_future_weather_cannot_change_reference_atmosphere():
    frame=pd.DataFrame(dict(temperature_c=[10,20,30],pressure_hpa=[1000,1010,1020],dew_point_c=[1,2,3]))
    expected=training_surface_conditions(frame,[0,1])
    frame.loc[2]=[-100,10000,1000]
    assert training_surface_conditions(frame,[0,1])==expected


def test_replicated_station_rows_do_not_create_independent_blocks():
    times=pd.date_range("2020-01-01",periods=84)
    truth=np.zeros((84,1))
    pred=np.linspace(.1,1,84)[:,None]
    ref=np.ones((84,1))
    a=calendar_block_interval(truth,pred,ref,np.ones(1),times,replicates=100)
    b=calendar_block_interval(np.repeat(truth,3,0),np.repeat(pred,3,0),np.repeat(ref,3,0),
        np.ones(1),np.repeat(times,3),replicates=100)
    np.testing.assert_allclose([a["ci_low"],a["ci_high"]],[b["ci_low"],b["ci_high"]],atol=1e-14)
