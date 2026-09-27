"""Conditional NO2 design with explicit calibration structure and acquisition cost."""
from dataclasses import dataclass
import cvxpy as cp
import numpy as np


@dataclass(frozen=True)
class TargetDesign:
    operator: np.ndarray
    risk: float
    noise_sd: float
    atmospheric_bias: float
    calibration_bias: float
    status: str
    identity_error: float
    continuous_dwell_s: np.ndarray | None


def polynomial_calibration(frequency, total_bound, residual_bound):
    """A declared subset of a spectral box, not a fitted receiver error model.

    Three Legendre modes each get one third of the remaining pointwise budget.
    Returned columns already include their coefficient bounds; |gamma_k|<=1.
    """
    f = np.asarray(frequency, float)
    if f.ndim != 1 or len(f) < 2 or np.ptp(f) <= 0 or not np.isfinite(f).all():
        raise ValueError('A finite, nonconstant frequency grid is required')
    if not 0 <= residual_bound <= total_bound or not np.isfinite(total_bound):
        raise ValueError('Require 0 <= residual bound <= total bound')
    x = 2 * (f - 260.) / 140. - 1
    if np.max(abs(x)) > 1 + 1e-12:
        raise ValueError('The declared polynomial basis covers 260 to 400 GHz')
    return np.column_stack([np.ones(len(f)), x, (3*x*x-1)/2]) * ((total_bound-residual_bound)/3)


def risk_components(h, variance, bias, modes, residual_bound):
    h = np.asarray(h, float)
    noise = float(np.sqrt((h*h) @ variance))
    atmosphere = float(np.max(abs(h @ bias), initial=0.))
    calibration = float(np.sum(abs(h @ modes)) + residual_bound*np.sum(abs(h)))
    return float(np.hypot(noise, atmosphere+calibration)), noise, atmosphere, calibration


def solve_target(design, nuisance, bias, modes, residual_bound, *, target=3,
                 variance=None, thermal_per_second=None, available_s=None):
    """Minimize the exact envelope risk for one unbiased target.

    Supply either fixed diagonal variance or continuous dwell coefficients a_i
    with var(y_i)=a_i/t_i. Eliminating dwell gives (sum |h_i| sqrt(a_i))^2/T.
    Atmospheric uncertainty is conv{+/-b_s}; calibration modes have independent
    unit coefficient bounds plus a residual box. No uncertainty is learned here.
    """
    d, n, b, s = [np.asarray(a, float) for a in (design, nuisance, bias, modes)]
    m = len(d)
    if d.ndim != 2 or any(a.ndim != 2 or len(a) != m for a in (n,b,s)):
        raise ValueError('Incompatible input dimensions')
    if not all(np.isfinite(a).all() for a in (d,n,b,s)) or not 0 <= target < d.shape[1]:
        raise ValueError('Finite inputs and an existing target are required')
    if not np.isfinite(residual_bound) or residual_bound < 0:
        raise ValueError('A finite nonnegative residual bound is required')
    if (variance is None) == (thermal_per_second is None):
        raise ValueError('Supply exactly one acquisition variance model')
    weights = np.asarray(variance if variance is not None else thermal_per_second, float)
    if weights.shape != (m,) or np.any(weights <= 0) or not np.isfinite(weights).all():
        raise ValueError('Positive finite noise coefficients are required')
    if variance is None and (available_s is None or available_s <= 0 or not np.isfinite(available_s)):
        raise ValueError('A finite positive dwell budget is required')
    # Whiten a fixed allocation before constructing the equality coordinates.
    # Sparse continuous designs rounded to one pilot at unused tones otherwise
    # produce large variance ratios and poorly scaled fixed-allocation cones.
    coordinate = 1/np.sqrt(weights) if variance is not None else np.ones(m)
    a = np.column_stack([d, n])*coordinate[:,None]; norms = np.linalg.norm(a, axis=0)
    rhs = np.zeros(a.shape[1]); rhs[target] = 1
    keep = norms > 0
    u, singular, vh = np.linalg.svd(a[:,keep]/norms[keep], full_matrices=False)
    rank = int(np.sum(singular > singular[0]*1e-12))
    rhs = rhs[keep]/norms[keep]
    if np.max(abs(vh[rank:] @ rhs), initial=0) > 1e-8*max(1, np.linalg.norm(rhs)):
        raise ValueError('The target is not identifiable')
    q = (vh[:rank] @ rhs)/singular[:rank]
    scale = np.linalg.norm(q)
    if scale == 0: raise ValueError('Degenerate target constraint')
    x = cp.Variable(m)
    h = cp.multiply(coordinate,scale*x)
    atmosphere = cp.Variable(nonneg=True)
    total_bias = cp.Variable(nonneg=True)
    constraints = [u[:,:rank].T @ x == q/scale]
    if b.shape[1]: constraints += [cp.abs(b.T @ h) <= atmosphere]
    else: constraints += [atmosphere == 0]
    calibration = residual_bound*cp.norm1(h)
    if s.shape[1]: calibration += cp.norm1(s.T @ h)
    constraints += [atmosphere + calibration <= total_bias]
    if variance is not None:
        noise = scale*cp.norm(x,2)
    else:
        noise = cp.norm1(cp.multiply(np.sqrt(weights),h))/np.sqrt(available_s)
    problem = cp.Problem(cp.Minimize(cp.norm(cp.hstack([noise,total_bias]),2)), constraints)
    problem.solve(solver='CLARABEL', tol_gap_abs=1e-9, tol_gap_rel=1e-9,
                  tol_feas=1e-9, max_iter=500)
    if problem.status != cp.OPTIMAL:
        raise RuntimeError(f'Unaccepted optimization status: {problem.status}')
    result = coordinate*scale*np.asarray(x.value)
    expected = np.eye(d.shape[1])[target]
    error = max(float(np.max(abs(result@d-expected))),
                float(np.max(abs(result@n)/np.maximum(np.linalg.norm(n,axis=0),1e-300),initial=0)))
    if error > 1e-7: raise RuntimeError(f'Constraint residual {error} exceeds tolerance')
    dwell = None
    if variance is None:
        weighted = abs(result)*np.sqrt(weights)
        dwell = available_s*weighted/weighted.sum()
        # Zero-weight observations need zero dwell and contribute zero variance.
        used_variance = np.divide(weights,dwell,out=np.zeros(m),where=dwell>0)
    else: used_variance = weights
    risk,noise_sd,ab,cb = risk_components(result,used_variance,b,s,residual_bound)
    return TargetDesign(result,risk,noise_sd,ab,cb,problem.status,error,dwell)


def integer_dwell(weights, duration_s, *, sweeps=1, pilot_s=1e-6, retune_s=0.):
    """Allocate full pilots per tone per sweep, charging every sweep's switches.

    All supplied frequencies are visited, including nearly zero continuous
    weights. This avoids an uncharged post hoc support selection. Largest
    remainders assign leftover pilots deterministically; equal sweeps have the
    same allocation. Start setup and inter-sweep waiting are excluded explicitly.
    """
    w = np.asarray(weights,float)
    if w.ndim != 1 or not len(w) or np.any(w<0) or not np.isfinite(w).all() or w.sum()<=0:
        raise ValueError('Finite nonnegative weights with positive sum are required')
    if sweeps not in (1,2) or duration_s <= 0 or pilot_s <= 0 or retune_s < 0:
        raise ValueError('Invalid acquisition parameters')
    if not np.isfinite([duration_s,pilot_s,retune_s]).all(): raise ValueError('Nonfinite timing')
    switches = sweeps*(len(w)-1)
    usable = duration_s-switches*retune_s
    total_per_sweep = int(np.floor((usable+1e-12)/(sweeps*pilot_s)))
    if total_per_sweep < len(w): raise ValueError('Budget cannot visit every frequency')
    ideal = (total_per_sweep-len(w))*w/w.sum()
    count = np.floor(ideal).astype(np.int64)+1
    leftover = total_per_sweep-int(count.sum())
    order = np.argsort(-(ideal-np.floor(ideal)),kind='stable')
    count[order[:leftover]] += 1
    dwell = count*pilot_s
    charged = sweeps*dwell.sum()+switches*retune_s
    if charged > duration_s+1e-9: raise RuntimeError('Acquisition exceeds budget')
    return count, dict(sweeps=sweeps,switches=switches,pilot_s=pilot_s,retune_s=retune_s,
                      integration_s=float(sweeps*dwell.sum()),charged_s=float(charged),
                      unused_s=float(max(0,duration_s-charged)))


def temporal_difference_variance(reference_variance, sample_variance, cross_covariance=None):
    """Cov(y1-y0), retaining cross covariance when supplied."""
    v0,v1 = np.asarray(reference_variance,float),np.asarray(sample_variance,float)
    if v0.ndim != 2 or v0.shape != v1.shape or v0.shape[0] != v0.shape[1]:
        raise ValueError('Matching square covariance matrices are required')
    cross = np.zeros_like(v0) if cross_covariance is None else np.asarray(cross_covariance,float)
    if cross.shape != v0.shape or not all(np.isfinite(a).all() for a in [v0,v1,cross]):
        raise ValueError('Invalid covariance inputs')
    joint = np.block([[v0,cross],[cross.T,v1]])
    if not np.allclose(joint,joint.T) or np.linalg.eigvalsh(joint).min() < -1e-10*max(1,np.linalg.norm(joint)):
        raise ValueError('Joint covariance must be positive semidefinite')
    return v0+v1-cross-cross.T


def characterize_calibration(frame, *, degree=2, train_fraction=.6, validation_fraction=.2):
    """Characterize actual repeated reference sweeps without using test to fit.

    Required long columns: time, frequency_ghz, error_db (observed minus known
    reference). Returns training-centered polynomial residuals and empirical
    heldout coverage. Training maximum residual is a descriptive envelope,
    never a calibrated population guarantee. No interpolation or imputation.
    """
    import pandas as pd
    from thz_isac.evaluation_protocol import chronological_timestamp_split
    required = ['time','frequency_ghz','error_db']
    if not set(required).issubset(frame.columns): raise ValueError(f'Required columns: {required}')
    data=frame[required].copy(); data['time']=pd.to_datetime(data['time'],errors='raise')
    if data.duplicated(['time','frequency_ghz']).any(): raise ValueError('Duplicate time/frequency records')
    wide=data.pivot(index='time',columns='frequency_ghz',values='error_db').sort_index().sort_index(axis=1)
    values=wide.to_numpy(float);f=wide.columns.to_numpy(float)
    if not np.isfinite(values).all() or not np.isfinite(f).all() or np.ptp(f)<=0:
        raise ValueError('Every sweep must contain the same complete frequency grid')
    if degree < 0 or int(degree)!=degree or degree+1>=len(f): raise ValueError('Invalid polynomial degree')
    split=chronological_timestamp_split(pd.DataFrame({'datetime':wide.index}),train_fraction,validation_fraction)
    center=values[split.train].mean(0)
    x=2*(f-f.min())/np.ptp(f)-1
    basis=np.polynomial.legendre.legvander(x,degree)
    coefficients=np.linalg.lstsq(basis,(values-center).T,rcond=None)[0].T
    residual=values-center-coefficients@basis.T
    bounds=np.max(abs(coefficients[split.train]),axis=0)
    epsilon=float(np.max(abs(residual[split.train])))
    rows=[]
    for label,index in [('train',split.train),('validation',split.validation),('test',split.test)]:
        rows.append(dict(split=label,n_sweeps=len(index),residual_max_db=float(np.max(abs(residual[index]))),
                         residual_coverage=float(np.mean(np.max(abs(residual[index]),axis=1)<=epsilon)),
                         joint_coverage=float(np.mean((np.max(abs(residual[index]),axis=1)<=epsilon)&
                             np.all(abs(coefficients[index])<=bounds,axis=1)))))
    return dict(frequency=f,center_db=center,basis=basis,coefficients=coefficients,residual_db=residual,
                training_coefficient_bounds=bounds,training_residual_bound_db=epsilon,summary=rows,
                train_end=str(split.train_end),validation_end=str(split.validation_end))
