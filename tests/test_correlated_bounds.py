import numpy as np
from thz_isac.correlated_bounds import correlated_floors


def test_common_correlated_noise_can_help_after_offset_removal():
    design=np.array([[1.],[-1.]])
    nuisance=np.ones((2,1));variance=np.ones(2)
    independent,_,_=correlated_floors(design,nuisance,variance,np.sqrt(.4),np.eye(2))
    correlated,_,_=correlated_floors(design,nuisance,variance,np.sqrt(.4),np.ones((2,2)))
    np.testing.assert_allclose(independent,np.sqrt(.5),rtol=1e-12)
    np.testing.assert_allclose(correlated,np.sqrt(.3),rtol=1e-12)
