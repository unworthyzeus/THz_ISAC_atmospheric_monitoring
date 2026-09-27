import numpy as np
from thz_isac.calibration_floor import persistent_bias_floor


def test_exact_one_observation_floor():
    result=persistent_bias_floor(np.ones((1,1)),np.empty((1,0)),np.array([[.5]]),.25,0)
    assert abs(result['primal_bias']-.75)<1e-10
    assert .749999999<result['lower_bound']<=.75


def test_nuisance_elimination_gives_known_two_observation_floor():
    # h=(1,-1) is forced by target response and offset cancellation.
    result=persistent_bias_floor(np.array([[1.],[0.]]),np.ones((2,1)),np.zeros((2,1)),.1,0)
    np.testing.assert_allclose(result['operator'],[1.,-1.],atol=1e-9)
    assert .19999999<result['lower_bound']<=.20000001
