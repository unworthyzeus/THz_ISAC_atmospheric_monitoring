"""Detection and concentration-error metrics with explicit denominators."""
import numpy as np
from scipy.stats import norm


def _samples(values):
    a=np.asarray(values,dtype=float)
    if a.ndim!=1 or not len(a) or not np.isfinite(a).all():
        raise ValueError('A finite nonempty sample vector is required.')
    return a


def wilson_percent(successes,total,confidence=.95):
    if total<=0: return (None,None)
    z=norm.ppf((1+confidence)/2); fraction=successes/total
    center=(fraction+z*z/(2*total))/(1+z*z/total)
    half=z*np.sqrt(fraction*(1-fraction)/total+z*z/(4*total*total))/(1+z*z/total)
    return 100*(center-half),100*(center+half)


def detection_metrics(positive_scores,null_scores,threshold):
    positive=_samples(positive_scores); null=_samples(null_scores)
    if not np.isfinite(threshold): raise ValueError('Finite threshold required.')
    tp=int(np.sum(positive>=threshold)); fp=int(np.sum(null>=threshold))
    fn=len(positive)-tp; tn=len(null)-fp
    precision=tp/(tp+fp) if tp+fp else None
    recall=tp/len(positive); fpr=fp/len(null)
    return dict(tp=tp,fp=fp,fn=fn,tn=tn,positive_draws=len(positive),null_draws=len(null),
        precision_pct=None if precision is None else 100*precision,recall_pct=100*recall,
        false_positive_rate_pct=100*fpr,specificity_pct=100*(1-fpr),
        accuracy_pct=100*(tp+tn)/(len(positive)+len(null)),
        f1_pct=100*2*tp/(2*tp+fp+fn),
        precision_ci95_pct=wilson_percent(tp,tp+fp),recall_ci95_pct=wilson_percent(tp,len(positive)),
        false_positive_ci95_pct=wilson_percent(fp,len(null)),
        evaluated_positive_prevalence_pct=100*len(positive)/(len(positive)+len(null)))


def concentration_errors(estimates,truth):
    values=_samples(estimates)
    if not np.isfinite(truth) or truth<0: raise ValueError('Nonnegative finite truth required.')
    delta=values-truth; absolute=np.abs(delta)
    mae=float(absolute.mean()); rmse=float(np.sqrt(np.mean(delta**2)))
    return dict(truth_ug_m3=float(truth),bias_ug_m3=float(delta.mean()),mae_ug_m3=mae,rmse_ug_m3=rmse,
        p95_absolute_error_ug_m3=float(np.quantile(absolute,.95)),
        mae_pct_of_truth=100*mae/truth if truth>0 else None,
        rmse_pct_of_truth=100*rmse/truth if truth>0 else None,
        within_20pct_of_truth_pct=float(100*np.mean(absolute<=.2*truth)) if truth>0 else None,
        negative_estimate_pct=float(100*np.mean(values<0)))
