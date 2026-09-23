"""Rank-aware retrieval, exact complex-amplitude fitting and decision limits."""
from dataclasses import dataclass
import numpy as np
from scipy.optimize import least_squares
from scipy.stats import norm
from scipy.linalg import solve_triangular
from .attainable_estimation import efficient_linear_estimator


def identifiability(design,nuisance,covariance,rtol=1e-10):
    """Report information remaining after calibration/interferent projection.

    Weak normalized singular vectors are reported rather than made informative
    by a prior. Original column norms preserve the absolute sensitivity scale.
    """
    d=np.asarray(design,dtype=float);n=np.asarray(nuisance,dtype=float);c=np.asarray(covariance,dtype=float)
    if d.ndim!=2 or n.ndim!=2 or n.shape[0]!=len(d) or c.shape!=(len(d),len(d)) or not all(np.isfinite(x).all() for x in (d,n,c)) or not np.allclose(c,c.T) or not 0<rtol<1:
        raise ValueError('Invalid identifiability inputs')
    chol=np.linalg.cholesky(c)
    wd=solve_triangular(chol,d,lower=True);wn=solve_triangular(chol,n,lower=True)
    scales=np.linalg.norm(wn,axis=0);wn=wn[:,scales>0]/scales[scales>0]
    u,s,_=np.linalg.svd(wn,full_matrices=False);rank=int(np.sum(s>s[0]*rtol)) if len(s) else 0
    q=u[:,:rank];p=wd-q@(q.T@wd)
    norms=np.linalg.norm(p,axis=0);original=np.linalg.norm(wd,axis=0)
    retention=np.divide(norms,original,out=np.zeros_like(norms),where=original>0)
    scaled=p/np.where(norms>0,norms,1)
    _,s,vh=np.linalg.svd(scaled,full_matrices=False)
    target_rank=int(np.sum(s>s[0]*rtol)) if len(s) else 0
    lost=np.any(retention<rtol)
    return dict(identifiable=bool(target_rank==d.shape[1] and not lost),
                target_rank=target_rank,nuisance_rank=rank,retained_information_fraction=retention**2,
                singular_values=s,weakest_normalized_combination=vh[-1],
                whitened_column_norms=norms,condition_number=float(s[0]/s[-1]) if s[-1]>0 else float('inf'))


@dataclass(frozen=True)
class ComplexFit:
    concentrations: np.ndarray
    calibration: np.ndarray
    success: bool
    cost: float
    evaluations: int
    active_bounds: np.ndarray
    jacobian_singular_values: np.ndarray


def fit_complex_amplitude(observed,design,nuisance,sigma_complex,*,
                          concentration_scale,upper_concentration,initial=None):
    """Fit exact Beer-Lambert complex pilot means with real Gaussian components.

    sigma_complex is sqrt(E|noise|^2). Observations are phase-referenced by the
    communication receiver. Fits retain their bounds/rank diagnostic and never
    inherit an unconstrained Gaussian confidence interval. A bound is a domain
    restriction, not evidence that a concentration was measured.
    """
    y=np.asarray(observed,dtype=complex);d=np.asarray(design,dtype=float);n=np.asarray(nuisance,dtype=float)
    sigma=np.broadcast_to(np.asarray(sigma_complex,dtype=float),y.shape)
    scale=np.asarray(concentration_scale,dtype=float);upper=np.asarray(upper_concentration,dtype=float)
    if y.ndim!=1 or d.ndim!=2 or n.ndim!=2 or len(d)!=len(y) or len(n)!=len(y) or scale.shape!=(d.shape[1],) or upper.shape!=scale.shape or not all(np.isfinite(a).all() for a in (y,d,n,sigma,scale,upper)) or np.any(sigma<=0) or np.any(scale<=0) or np.any(upper<=0):
        raise ValueError('Invalid complex fit inputs')
    ns=np.linalg.norm(n,axis=0);n=n[:,ns>0];ns=ns[ns>0];basis=n/ns
    k=d.shape[1];matrix=np.column_stack((d*scale,basis))
    c0=np.zeros(k) if initial is None else np.asarray(initial,dtype=float)
    if c0.shape!=(k,) or np.any(c0<0) or np.any(c0>upper):
        raise ValueError('Initial concentration outside bounds')
    x0=np.r_[c0/scale,np.zeros(basis.shape[1])]
    limit=np.r_[upper/scale,np.full(basis.shape[1],np.inf)]
    lower=np.r_[np.zeros(k),np.full(basis.shape[1],-np.inf)]
    factor=np.log(10)/20; sd=sigma/np.sqrt(2)
    def mean(x):
        exponent=-factor*(matrix@x)
        # Strict floating-point domain protection, far beyond the physical
        # attenuation in the declared concentration domain.
        return np.exp(np.clip(exponent,-700,300))
    def residual(x):
        delta=(mean(x)-y)/sd
        return np.r_[delta.real,delta.imag]
    def jac(x):
        j=-factor*mean(x)[:,None]*matrix/sd[:,None]
        return np.vstack((j,np.zeros_like(j)))
    # Starting exactly at a lower bound can trigger a premature trust-region
    # stop; give positive variables a small interior start in scaled units.
    x0[:k]=np.clip(x0[:k],1e-5,np.maximum(1e-5,limit[:k]-1e-5))
    result=least_squares(residual,x0,jac=jac,bounds=(lower,limit),x_scale='jac',
                         ftol=1e-10,xtol=1e-10,gtol=1e-9,max_nfev=1000)
    sv=np.linalg.svd(result.jac,compute_uv=False)
    return ComplexFit(result.x[:k]*scale,result.x[k:]/ns,bool(result.success),
                      float(result.cost),result.nfev,result.active_mask[:k],sv)


def decision_limits(standard_error,*,false_positive_rate=.01,power=.95,
                    family_size=1,bias_bound=0.):
    """Critical level and detection limit for Gaussian signed estimates.

    For unknown deterministic bias in [-b,b], the null critical level gains b
    and the concentration detection limit gains 2b, covering opposite worst
    cases. Bonferroni controls the requested family-wise false-positive rate.
    These limits require fixed known covariance, not fitted/noisy error bars.
    """
    sd=np.asarray(standard_error,dtype=float);b=np.broadcast_to(np.asarray(bias_bound,dtype=float),sd.shape)
    if not np.isfinite(sd).all() or not np.isfinite(b).all() or np.any(sd<=0) or np.any(b<0) or not 0<false_positive_rate<.5 or not .5<power<1 or isinstance(family_size,bool) or int(family_size)!=family_size or family_size<1:
        raise ValueError('Invalid decision-limit inputs')
    z=norm.isf(false_positive_rate/family_size)
    return dict(critical_level=z*sd+b,detection_limit=(z+norm.ppf(power))*sd+2*b,
                per_target_alpha=false_positive_rate/family_size,power=power,
                family_size=int(family_size),bias_bound=b)


def profile_complex_concentration(observed,design,nuisance,sigma_complex,*,
                                  target_index,grid,concentration_scale,upper_concentration):
    """Refit all other concentrations/calibration at each fixed target value.

    Returns likelihood costs without imposing an asymptotic chi-square cutoff
    at a nonnegative boundary. Flat profiles or minima at the imposed domain
    boundary cannot establish a measured concentration or finite interval.
    """
    d=np.asarray(design,dtype=float);values=np.asarray(grid,dtype=float)
    upper=np.asarray(upper_concentration,dtype=float);scale=np.asarray(concentration_scale,dtype=float)
    if d.ndim!=2 or not 0<=target_index<d.shape[1] or values.ndim!=1 or not len(values) or not np.isfinite(values).all() or np.any(values<0) or np.any(values>upper[target_index]):
        raise ValueError('Invalid profile grid or target')
    free=np.arange(d.shape[1])!=target_index
    costs=[];success=[];previous=None
    for concentration in values:
        fixed_mean=np.exp(-np.log(10)/20*d[:,target_index]*concentration)
        if np.any(fixed_mean<1e-100):raise ValueError('Profile grid exceeds the numerical transmission domain')
        result=fit_complex_amplitude(np.asarray(observed)/fixed_mean,d[:,free],nuisance,
                   np.asarray(sigma_complex)/fixed_mean,concentration_scale=scale[free],
                   upper_concentration=upper[free],initial=previous)
        previous=result.concentrations
        costs.append(result.cost);success.append(result.success)
    costs=np.array(costs)
    return dict(concentration=values,cost=costs,deviance_from_grid_minimum=2*(costs-costs.min()),
                success=np.array(success),minimum_at_grid_boundary=bool(np.argmin(costs) in [0,len(costs)-1]))


def ug_m3_to_ppm(concentration,molar_mass_g_mol,temperature_k,pressure_pa):
    if min(molar_mass_g_mol,temperature_k,pressure_pa)<=0 or not np.isfinite([molar_mass_g_mol,temperature_k,pressure_pa]).all():
        raise ValueError('Positive finite thermodynamic conversion inputs required')
    # ug/m3 -> mol/m3 -> mole fraction -> ppm. The factors 1e-6 cancel.
    return np.asarray(concentration)*8.314462618*temperature_k/(molar_mass_g_mol*pressure_pa)
