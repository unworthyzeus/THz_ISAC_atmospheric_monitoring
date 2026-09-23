"""Joint VOC, fine-PM and coarse-PM estimation with spectral-fit checks.

The unconstrained estimator preserves identifiability diagnostics. Negative
estimates are retained: clipping must not manufacture successful retrieval.
"""
from dataclasses import dataclass
import numpy as np
from scipy.linalg import solve_triangular
from scipy.stats import chi2
from scipy.optimize import nnls
from .attainable_estimation import efficient_linear_estimator, LinearEstimator


@dataclass(frozen=True)
class JointRetrieval:
    design: np.ndarray
    nuisance: np.ndarray
    covariance: np.ndarray
    estimator: LinearEstimator
    target_names: tuple[str, ...]

    def estimate(self, attenuation_db):
        observed = np.asarray(attenuation_db, dtype=float)
        if observed.shape[-1] != len(self.design) or not np.isfinite(observed).all():
            raise ValueError('Observations must be finite and match the frequency dimension.')
        return observed @ self.estimator.operator.T

    def spectral_fit(self, attenuation_db):
        """Full-model whitened residual and Gaussian lack-of-fit p-value.

        A good fit alone is not a detection; it must accompany target error
        bars. Very weak species can produce a good residual fit by noise alone.
        """
        y = np.asarray(attenuation_db, dtype=float)
        if y.ndim != 1 or y.shape != (len(self.design),) or not np.isfinite(y).all():
            raise ValueError('One finite spectrum is required.')
        chol = np.linalg.cholesky(self.covariance)
        white_y = solve_triangular(chol, y, lower=True)
        full = solve_triangular(chol, np.column_stack((self.design, self.nuisance)), lower=True)
        norms = np.linalg.norm(full, axis=0)
        full = full[:, norms > 0] / norms[norms > 0]
        u, s, _ = np.linalg.svd(full, full_matrices=False)
        rank = int(np.sum(s > s[0]*1e-12))
        residual = white_y - u[:, :rank] @ (u[:, :rank].T @ white_y)
        statistic = float(residual @ residual)
        dof = len(y)-rank
        if dof <= 0:
            raise ValueError('No residual degrees of freedom remain.')
        return dict(chi_square=statistic, degrees_of_freedom=dof,
                    p_value=float(chi2.sf(statistic, dof)))

    def reported_pm_covariance(self):
        """Covariance of PM2.5 and PM10, including fine/coarse cross covariance."""
        transform = np.array([[1.,0.],[1.,1.]])
        return transform @ self.estimator.covariance[-2:,-2:] @ transform.T

    def estimate_nonnegative(self, attenuation_db):
        """Nonnegative target fit with unconstrained nuisance coefficients.

        This estimate is biased near zero and does not inherit the Gaussian
        covariance bound. It is provided as a separate diagnostic, never as a
        replacement for the identifiability and error-bar calculation.
        """
        y = np.asarray(attenuation_db, dtype=float)
        if y.ndim != 1 or y.shape != (len(self.design),) or not np.isfinite(y).all():
            raise ValueError('One finite spectrum is required.')
        chol = np.linalg.cholesky(self.covariance)
        white_d = solve_triangular(chol,self.design,lower=True)
        white_n = solve_triangular(chol,self.nuisance,lower=True)
        white_y = solve_triangular(chol,y,lower=True)
        norms = np.linalg.norm(white_n,axis=0)
        normalized = white_n[:,norms>0]/norms[norms>0]
        u,s,_ = np.linalg.svd(normalized,full_matrices=False)
        rank = int(np.sum(s>s[0]*1e-12)) if len(s) else 0
        q = u[:,:rank]
        projected = white_d-q@(q.T@white_d)
        response = white_y-q@(q.T@white_y)
        scales = np.linalg.norm(projected,axis=0)
        estimate,_ = nnls(projected/scales,response,maxiter=100*len(scales))
        return estimate/scales


def make_joint_retrieval(voc_design, pm_design, nuisance, covariance, voc_names):
    """Estimate VOCs and independent fine/coarse PM masses simultaneously."""
    voc = np.asarray(voc_design, dtype=float)
    pm = np.asarray(pm_design, dtype=float)
    nuisance = np.asarray(nuisance, dtype=float)
    if voc.ndim != 2 or pm.shape != (len(voc), 2) or voc.shape[1] != len(voc_names):
        raise ValueError('VOC columns and exactly two PM mode columns are required.')
    if len(set(voc_names)) != len(voc_names) or not len(voc_names):
        raise ValueError('VOC names must be nonempty and unique.')
    design = np.column_stack((voc, pm))
    estimator = efficient_linear_estimator(design, nuisance, covariance)
    return JointRetrieval(design, nuisance, np.asarray(covariance), estimator,
                          tuple(voc_names)+('PM2.5', 'PMcoarse'))


def fine_coarse_to_pm25_pm10(estimates):
    values = np.asarray(estimates, dtype=float)
    if values.shape[-1] < 2 or not np.isfinite(values).all():
        raise ValueError('Finite estimates with two final PM columns required.')
    return np.stack((values[..., -2], values[..., -2]+values[..., -1]), axis=-1)
