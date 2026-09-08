"""Attainable linear Gaussian estimates and deterministic calibration sensitivity.

Covariance is fixed and known in this conditional model. Target rank is checked
after nuisance projection; an unidentifiable target is never assigned zero error.
"""
from dataclasses import dataclass
import numpy as np
from scipy.linalg import solve_triangular

@dataclass(frozen=True)
class LinearEstimator:
    operator: np.ndarray
    covariance: np.ndarray
    nuisance_rank: int
    target_condition: float

def efficient_linear_estimator(design, nuisance, covariance, rtol=1e-12):
    """Return H such that H D=I and H N=0, minimizing H Sigma H.T."""
    d=np.asarray(design,dtype=float); n=np.asarray(nuisance,dtype=float)
    sigma=np.asarray(covariance,dtype=float)
    if d.ndim!=2 or n.ndim!=2 or n.shape[0]!=d.shape[0] or sigma.shape!=(len(d),len(d)):
        raise ValueError('Incompatible design, nuisance, or covariance shapes')
    if not all(np.isfinite(a).all() for a in [d,n,sigma]) or not np.allclose(sigma,sigma.T):
        raise ValueError('Finite arrays and symmetric covariance are required')
    if not 0 < rtol < 1: raise ValueError('Invalid rank tolerance')
    chol=np.linalg.cholesky(sigma)
    wd=solve_triangular(chol,d,lower=True)
    wn=solve_triangular(chol,n,lower=True)
    norms=np.linalg.norm(wn,axis=0)
    wn=wn[:,norms>0]/norms[norms>0]
    u,s,_=np.linalg.svd(wn,full_matrices=False)
    rank=int(np.sum(s>rtol*s[0])) if len(s) else 0
    basis=u[:,:rank]
    projected=wd-basis@(basis.T@wd)
    scale=np.linalg.norm(projected,axis=0)
    if np.any(scale<=rtol*np.linalg.norm(wd,axis=0)):
        raise ValueError('Target is unidentifiable after nuisance elimination')
    u,s,vh=np.linalg.svd(projected/scale,full_matrices=False)
    if len(s)<d.shape[1] or s[-1]<=rtol*s[0]:
        raise ValueError('Target is unidentifiable after nuisance elimination')
    # Pseudoinverse by SVD avoids squaring the target condition number.
    left=(vh.T/s)@u.T
    left=(left-(left@basis)@basis.T)/scale[:,None]
    operator=solve_triangular(chol.T,left.T,lower=False).T
    cov=operator@sigma@operator.T
    return LinearEstimator(operator,(cov+cov.T)/2,rank,float(s[0]/s[-1]))

def bias_and_rmse(estimator, mean_error, true_covariance=None):
    """Exact risk for an additive deterministic forward-model discrepancy."""
    bias=estimator.operator@np.asarray(mean_error,dtype=float)
    cov=estimator.covariance if true_covariance is None else estimator.operator@true_covariance@estimator.operator.T
    return bias,np.sqrt(np.diag(cov)+bias*bias)

def worst_case_calibration_rmse(estimator, maximum_error_db):
    """Per-target worst case for |b_i| <= epsilon; maxima may use different b."""
    if not np.isfinite(maximum_error_db) or maximum_error_db<0:
        raise ValueError('Calibration amplitude must be finite and nonnegative')
    bias_bound=maximum_error_db*np.abs(estimator.operator).sum(axis=1)
    return np.sqrt(np.diag(estimator.covariance)+bias_bound*bias_bound)

def calibration_allowance(estimator, rmse_targets):
    """Return per-probe deterministic error allowances, or NaN if noise already fails."""
    target=np.asarray(rmse_targets,dtype=float)
    if np.any(target<=0) or not np.isfinite(target).all(): raise ValueError('Positive targets required')
    margin=target*target-np.diag(estimator.covariance)
    return np.sqrt(np.maximum(margin,0))/np.abs(estimator.operator).sum(axis=1)*np.where(margin>=0,1,np.nan)
