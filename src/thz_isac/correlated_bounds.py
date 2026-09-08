"""Efficient linear information with declared correlated residual errors."""
import numpy as np
from scipy.linalg import solve_triangular


def correlated_floors(design,nuisance,variance,residual_std,correlation):
    variance=np.asarray(variance,dtype=float)
    correlation=np.asarray(correlation,dtype=float)
    if correlation.shape!=(len(variance),len(variance)) or not np.allclose(correlation,correlation.T):
        raise ValueError("A symmetric correlation matrix is required")
    if (variance<=0).any() or not np.allclose(np.diag(correlation),1):
        raise ValueError("Positive marginal variances and unit correlation diagonal are required")
    if np.linalg.eigvalsh(correlation).min() < -1e-9:
        raise ValueError("Residual correlation must be positive semidefinite")
    if (variance<residual_std**2-1e-12).any():
        raise ValueError("Residual variance exceeds the total marginal variance")
    sd=np.sqrt(variance)
    normalized=np.eye(len(variance))+residual_std**2*(correlation-np.eye(len(variance)))/np.outer(sd,sd)
    chol=np.linalg.cholesky(normalized)
    d=solve_triangular(chol,np.asarray(design)/sd[:,None],lower=True)
    n=solve_triangular(chol,np.asarray(nuisance)/sd[:,None],lower=True)
    norms=np.linalg.norm(n,axis=0);n=n[:,norms>0]/norms[norms>0]
    u,s,_=np.linalg.svd(n,full_matrices=False)
    rank=int(np.sum(s>1e-12*s[0])) if len(s) else 0
    residual=d-u[:,:rank]@(u[:,:rank].T@d)
    fisher=residual.T@residual
    if np.linalg.matrix_rank(fisher)!=fisher.shape[0]:
        raise ValueError("Target information is rank deficient")
    covariance=np.linalg.inv(fisher)
    return np.sqrt(np.diag(covariance)),rank,float(np.linalg.cond(fisher))
