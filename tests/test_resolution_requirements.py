from pathlib import Path
import sys
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from run_noise_requirements_resolution import diagonal_floors


def test_projected_information_matches_full_joint_inverse():
    rng=np.random.default_rng(610020)
    design=rng.normal(size=(40,4)); nuisance=rng.normal(size=(40,3)); variance=np.linspace(.1,2,40)
    full=np.column_stack((design,nuisance)); info=full.T@(full/variance[:,None])
    expected=np.sqrt(np.diag(np.linalg.inv(info))[:4])
    observed=diagonal_floors(design,nuisance,variance)
    np.testing.assert_allclose(observed,expected,rtol=1e-12)
    assert np.all(diagonal_floors(design,nuisance,variance+.01)>=observed)
    np.testing.assert_allclose(diagonal_floors(design,nuisance,variance*4),observed*2,rtol=1e-12)
