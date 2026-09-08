"""Training-only atmosphere and calendar-block uncertainty for review replay."""
import numpy as np
import pandas as pd


def training_surface_conditions(sample, train_indices):
    train=sample.iloc[train_indices]
    return dict(temperature_k=float(train["temperature_c"].median()+273.15),
                pressure_pa=float(train["pressure_hpa"].median()*100),
                dew_point_c=float(train["dew_point_c"].median()))


def calendar_block_interval(truth, prediction, reference, denominators, timestamps,
                            block_days=7, seed=609050, replicates=2000):
    """Paired percentile interval resampling full calendar blocks across stations."""
    timestamps=pd.to_datetime(pd.Series(timestamps)).reset_index(drop=True)
    labels=((timestamps-timestamps.min()).dt.total_seconds()/(86400*block_days)).astype(int).to_numpy()
    unique=np.unique(labels)
    counts=np.array([(labels==key).sum() for key in unique])
    errors=(np.asarray(prediction)-truth)**2
    baseline=(np.asarray(reference)-truth)**2
    sums=np.stack([errors[labels==key].sum(0) for key in unique])
    reference_sums=np.stack([baseline[labels==key].sum(0) for key in unique])
    rng=np.random.default_rng(seed)
    differences=[]
    for _ in range(replicates):
        sample=rng.integers(0,len(unique),len(unique))
        n=counts[sample].sum()
        candidate=np.mean(np.sqrt(sums[sample].sum(0)/n)/denominators)
        comparator=np.mean(np.sqrt(reference_sums[sample].sum(0)/n)/denominators)
        differences.append(candidate-comparator)
    low,high=np.quantile(differences,[.025,.975])
    return dict(block_days=block_days,blocks=len(unique),ci_low=float(low),ci_high=float(high))
