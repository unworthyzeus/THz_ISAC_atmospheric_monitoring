"""Exact represented-coefficient dual bounds for persistent bias floors."""
from fractions import Fraction
import numpy as np
from scipy.optimize import linprog


def persistent_bias_floor(design, nuisance, bias_columns, epsilon_db, target):
    """Lower-bound min_h max_s |h b_s| + epsilon ||h||_1, with H D=I, H N=0.

    A rational dual-feasibility check applies to the normalized binary LP inputs.
    Physical coefficient generation and model uncertainty are not certified here.
    """
    d=np.asarray(design,float); n=np.asarray(nuisance,float); b=np.asarray(bias_columns,float)
    if epsilon_db<=0 or not np.isfinite(epsilon_db):raise ValueError('Positive calibration radius required')
    m=len(d); constraints=np.column_stack((d,n));scale=np.linalg.norm(constraints,axis=0)
    keep=scale>0;constraints=constraints[:,keep]/scale[keep]
    rhs=np.zeros(d.shape[1]+n.shape[1]);rhs[target]=1;rhs=rhs[keep]/scale[keep]
    aeq=np.column_stack((constraints.T,-constraints.T,np.zeros(constraints.shape[1])))
    aub=np.vstack((np.column_stack((b.T,-b.T,-np.ones(b.shape[1]))),
                   np.column_stack((-b.T,b.T,-np.ones(b.shape[1])))))
    cost=np.r_[np.full(2*m,epsilon_db),1.]
    solved=linprog(cost,A_ub=aub,b_ub=np.zeros(len(aub)),A_eq=aeq,b_eq=rhs,
        bounds=(0,None),method='highs',options={'dual_feasibility_tolerance':1e-9,'primal_feasibility_tolerance':1e-9})
    if not solved.success:raise RuntimeError(solved.message)
    fraction=lambda value:Fraction.from_float(float(value))
    lam=[fraction(value) for value in solved.eqlin.marginals]
    mu=[min(Fraction(0),fraction(value)) for value in solved.ineqlin.marginals]
    # Uniform down-scaling makes every dual inequality exact because c_i>0.
    factor=Fraction(1)
    for column,c in enumerate(cost):
        lhs=sum((fraction(value)*weight for value,weight in zip(aeq[:,column],lam) if value),Fraction(0))
        lhs+=sum((fraction(value)*weight for value,weight in zip(aub[:,column],mu) if value),Fraction(0))
        factor=max(factor,lhs/fraction(c))
    lower=sum((fraction(value)*weight for value,weight in zip(rhs,lam)),Fraction(0))/factor
    h=solved.x[:m]-solved.x[m:2*m]
    achieved=float(np.max(abs(h@b))+epsilon_db*abs(h).sum())
    value=float(np.nextafter(float(lower),-np.inf))
    return dict(lower_bound=value,lower_fraction=str(lower),primal_bias=achieved,
        dual_scale_fraction=str(factor),operator=h,identity_error=float(np.max(abs(aeq@solved.x-rhs))),
        primal_dual_gap=achieved-value,
        equality_dual_fractions=[str(x/factor) for x in lam],
        inequality_dual_fractions=[str(x/factor) for x in mu],
        lp_equalities=aeq,lp_rhs=rhs,lp_inequalities=aub,lp_cost=cost)
