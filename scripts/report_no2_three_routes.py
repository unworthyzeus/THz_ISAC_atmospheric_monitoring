"""Generate source-linked research notes, manuscript section and figures."""
from pathlib import Path
import sys
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from repair_support import Run,digest


def main():
    out=ROOT/'results/no2_three_routes';run=Run(out/'report',dict(scope='Display recorded verified results; no new model fitting.'),__file__)
    design=pd.read_csv(out/'design/summary.csv');stress=pd.read_csv(out/'evaluation/summary.csv')
    table=design[design.duration_s==100].set_index('case')
    a=np.load(out/'physical/inputs.npz');ops=np.load(out/'design/operators.npz')
    cases=['coarse_equal_box','coarse_dwell_box','fine_equal_box','fine_dwell_box',
        'fine_dwell_polynomial','fine_dwell_poly_residual','fine_dwell_diff_stable','fine_dwell_diff_poly_residual']
    labels=['71 / equal / box','71 / optimized / box','424 / equal / box','424 / optimized / box',
        '424 / optimized / polynomial','424 / optimized / poly + residual',
        '424 / differential / stable','424 / differential / poly + residual']
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':9,'axes.spines.top':False,'axes.spines.right':False,
                         'pdf.fonttype':42,'axes.labelsize':9})
    fig,(ax,bx)=plt.subplots(1,2,figsize=(10.8,3.9),gridspec_kw={'width_ratios':[1.22,1]})
    y=np.arange(len(cases));total=table.loc[cases,'design_rmse'].to_numpy();noise=table.loc[cases,'noise_sd'].to_numpy()
    ax.hlines(y,noise,total,color='#9aaab8',linewidth=2)
    ax.scatter(noise,y,color='#86a9bf',s=24,label='Noise SD',zorder=3)
    ax.scatter(total,y,color='#174865',s=31,label='Worst RMSE',zorder=4)
    for x,k in zip(total,y):ax.annotate(f'{x:.2f}',(x,k),xytext=(5,0),textcoords='offset points',va='center',fontsize=8)
    ax.axvline(1,color='#b44932',ls=':',lw=1.2)
    ax.set_yticks(y,labels);ax.invert_yaxis();ax.set_xlim(0,4.0)
    ax.set_xlabel('Error / 25 micrograms per cubic metre')
    ax.set_title('Conditional error at 100 s total acquisition',loc='left',fontweight='bold',fontsize=10)
    ax.legend(loc='lower center',bbox_to_anchor=(.5,-.30),ncol=2,frameon=False,fontsize=8)
    f=a['frequency'];key='fine_dwell_poly_residual|100s';count=ops[key+'|counts'];fraction=count/count.sum()
    # Do not join across rejected low-SNR windows as if an interpolated
    # spectrum had been evaluated there.
    breaks=np.flatnonzero(np.diff(f)>.26)+1
    for k,indices in enumerate(np.split(np.arange(len(f)),breaks)):
        bx.plot(f[indices],a['design'][indices,3]*1e4,color='#969696',lw=1.1,
                label='NO2 sensitivity' if k==0 else None)
    bx.set_xlabel('Frequency (GHz)');bx.set_ylabel('NO2 attenuation per 25 micrograms/m³ (×10⁻⁴ dB)',fontsize=8)
    cx=bx.twinx();selected=fraction>1e-4
    cx.vlines(f[selected],0,100*fraction[selected],color='#126f85',lw=1.8)
    cx.scatter(f[selected],100*fraction[selected],color='#126f85',s=12)
    cx.set_ylabel('Allocated integration (%)',color='#126f85',fontsize=8);cx.spines['top'].set_visible(False)
    bx.set_title('Frequencies and dwell are designed jointly',loc='left',fontweight='bold',fontsize=10)
    bx.legend(loc='lower center',bbox_to_anchor=(.5,-.30),frameon=False,fontsize=8)
    fig.tight_layout(w_pad=2)
    fig.savefig(run.output/'no2_routes.pdf',bbox_inches='tight');fig.savefig(run.output/'no2_routes.png',dpi=170,bbox_inches='tight');plt.close(fig)
    spectral=pd.DataFrame(dict(frequency_ghz=f,NO2_db_per_25_ug_m3=a['design'][:,3],
        pilots=count,dwell_s=count*1e-6,fraction=fraction,operator=ops[key+'|h']))
    spectral.to_csv(run.output/'frequency_schedule_100s.csv',index=False)
    def value(name):return f"{table.loc[name,'design_rmse']:.3f}"
    rows='\n'.join(f"{label} & {value(name)}\\\\" for name,label in zip(cases,
        ['71, equal, box','71, optimized, box','424, equal, box','424, optimized, box',
         '424, polynomial','424, polynomial + residual','424, change, stable calibration','424, change, polynomial + residual']))
    section=r'''\section{Three NO$_2$ interventions with charged acquisition}
The I2R proposal motivates layered HITRAN modeling, statistical ratiometric inversion and sensitivity analysis; it supplies no repeated receiver calibration records. We therefore distinguish physical inputs, mathematical error models and missing calibration evidence. A laboratory THz study illustrates why reference repeatability and frequency tuning require separate characterization~\cite{bjarnason2008}; its methyl-chloride apparatus does not calibrate our NO$_2$ receiver.

\subsection{Differencing and structured calibration}
Temporal subtraction gives
\[
y_1-y_0=D(\theta_1-\theta_0)+N(\beta_1-\beta_0)
+(b_1-b_0)+(n_1-n_0).
\]
Identical persistent instrumental error cancels. Independent per-reading error boxes of radius $\epsilon$ instead leave a box of radius $2\epsilon$. Concentration changes are the estimand; absolute concentration additionally needs a baseline estimate and its covariance. Independent readings with equal noise have doubled variance at equal per-reading dwell. At equal \emph{total} acquisition time, halving the budget of each reading gives four times the variance before extra retuning. We use $2\operatorname{conv}\{\pm b_s\}$ for atmospheric difference error, so the design does not assume atmospheric cancellation.

Spectral differencing alone is a coordinate change on the offset-free observation space. Propagating the full contrast covariance gives a NO$_2$ GLS variance ratio of 1.000000000005 relative to the original observations with an unknown offset. Treating shared-reference contrasts as independent would create a spurious gain.

For structured calibration write $b_{\rm cal}=S\gamma+u$, $|\gamma_k|\le1$ and $\|u\|_\infty\le\epsilon_r$. The exact support contribution is $\|S^Th\|_1+\epsilon_r\|h\|_1$. Our exploratory $S$ contains degree-zero, one and two Legendre modes on 260--400 GHz, each scaled by $(\epsilon-\epsilon_r)/3$. This set is a subset of the original radius-$\epsilon$ box. It represents stronger assumptions, not measured improvement in an instrument. The constant mode is already canceled by $N$. We retain $\epsilon=10^{-4}$ dB with residual zero or $10^{-5}$ dB, and implement a separate chronological reference-sweep characterization tool. No receiver recordings are available to run that characterization.

\subsection{New frequencies and jointly optimized dwell}
We evaluate a 0.25 GHz candidate grid together with all 71 prior band probes, directly recomputing the 24-layer Voigt spectra and all 54 design discrepancies. Retaining new probes with nominal SNR at least 5 dB at $-1$ dBm leaves 424 frequencies. All coefficients and scenario choices precede the new stress evaluation. With per-second noise coefficient $a_i$, eliminating continuous dwell under $\sum_i t_i=T_a$ gives
\begin{equation}
\min_{t_i\ge0,\,\sum t_i=T_a}\sum_i\frac{a_i h_i^2}{t_i}
=\frac{\big(\sum_i|h_i|\sqrt{a_i}\big)^2}{T_a},
\qquad t_i\propto|h_i|\sqrt{a_i}.
\end{equation}
The zero-weight terms use zero dwell in this relaxation. Combining its square root with atmospheric and calibration support functions yields a convex target-specific design. The NO$_2$ row cancels the other three gas responses and the original nuisance spectra; it does not guarantee simultaneous four-gas precision.

All primary comparisons use one active $-1$ dBm tone, 1 $\mu$s pilots, 10 or 100 s total charged acquisition and an assumed 1 ms retuning time. One or two sorted sweeps cost respectively $m-1$ or $2(m-1)$ retunings. We round to integer pilots, visit every retained frequency at least once, preserve the jointly optimized operator and recompute its achieved risk. The largest rounding increment in RMSE is 0.000338. Integer optimality is not claimed. Fixed-allocation reoptimization attempts with inaccurate solver status were rejected and archived. The final 30 configurations pass independent arithmetic and constraint checks.

\begin{figure*}[t]\centering
\includegraphics[width=.99\textwidth]{../results/no2_three_routes/report/no2_routes.pdf}
\caption{NO$_2$ design comparisons with explicit time and calibration assumptions. Left: one-spectrum absolute retrieval and two-spectrum change retrieval use the same total acquisition budget, but different estimands and error sets. Right: the mixed polynomial/residual design assigns time to both signal and control frequencies. All results use modeled attenuation and nominal coherent noise.}
\end{figure*}
\begin{table}[t]\centering\scriptsize
\caption{Worst design RMSE at 100 s charged acquisition, divided by 25 \ugm. The original box has radius $10^{-4}$ dB; the mixed absolute model retains $10^{-5}$ dB arbitrary residual.}
\begin{tabular}{lr}\toprule
Probes, allocation and error model & RMSE\\\midrule
''' + rows + r'''
\bottomrule\end{tabular}
\end{table}

Most of the gain comes from dwell allocation: the coarse equal/optimized box errors are 3.513 and 2.501. Fine equal dwell gives 3.509, while fine optimized dwell gives 2.340. A separate rational dual check gives a noise-free box floor of 1.923285 on the 424 probes, compared with 2.055634 on the 71 probes. Both exceed one. The new frequencies improve this represented-model floor but do not eliminate it.

Under the declared pure polynomial error model the fine design reaches 1.283 at 100 s; retaining the arbitrary $10^{-5}$ dB residual gives 1.363. Holding each 100 s operator and its allocation proportions fixed, 181.798 and 248.809 s respectively suffice numerically to reach the unit design target, after charging integer pilots and retuning. These are constructive times for those particular designs, not minimum-time bounds. The latter case radiates 0.1973 J. Stable-calibration differential retrieval requires 3902.121 s for its frozen design and conservative atmospheric-difference envelope. Such long acquisitions additionally require unverified stationarity and geometry control. Narrowing the calibration set cannot be presented as evidence that this stability has been achieved.

\subsection{New modeled states and real meteorological changes}
We freeze all operators before evaluating 16 new assumed temperature/pressure/height states using real test-period concentrations and 24 same-station pairs separated by one recorded hour. Both endpoints lie after the existing validation cutoff. The pair experiment uses the recorded temperature, pressure and dew point, with the same assumed 1.5 km pollutant profile. It repeats a fixed 45-degree slant geometry; these are not synchronized satellite overpasses or measured radio data. Acquisition time excludes the hour between epochs and initial setup. The previously used public concentration records are not a new independent population sample.

At 100 s, the mixed structured fine design has worst RMSE 1.291 on the 16 new states under nominal covariance (1.306 with modeled state-dependent noise). On the hourly meteorological pairs, absolute atmospheric bias reaches 3.201, beyond the design envelope. Stable-calibration differencing reduces the corresponding worst change bias to 0.411, but its nominal noise SD rises to 2.399. Its worst pair RMSE is 2.434, versus 3.597 for the mixed structured absolute estimator; neither reaches one and their estimands differ.

Eleven of 24 weather pairs place at least one visited tone below the 5 dB design regime. Substituting the modeled weather-dependent covariance produces worst errors of 26.280 for mixed structured absolute retrieval and 47.243 for stable differential retrieval. These numbers are extrapolated diagnostics where the coherent approximation may fail, not validated performance predictions. The loss of the nominal SNR regime itself prevents claiming robust field retrieval. Measured spectral drift, realistic geometry and calibration across humidity changes remain necessary.
'''
    (ROOT/'paper/no2_three_routes.tex').write_text(section,encoding='utf-8')
    note='''# NO2 differential, calibration and frequency design

## What was done and why

**SOURCE STATEMENT:** The available I2R document is a two-page proposal. It asks for layered atmospheric modeling, HITRAN line shapes, simulated CSI, ratiometric/optimization inversion and sensitivity bounds. It contains no repeated receiver calibration dataset. [I2R proposal](../references/proposals/I2R_proposal_THz_ISAC.pdf), physical pp. 1–2, Tasks 1–4.

**RESULT:** Implemented and evaluated all three requested computational routes: temporal and spectral differences; a structured calibration uncertainty model and a real-record characterization interface; and directly recalculated fine-grid frequency/dwell design. The 30 primary designs have fixed 10/100 s charged acquisition budgets, one active −1 dBm tone, integer 1 μs pilots and assumed 1 ms retuning. All 71 original band probes remain in the 424-point fine candidate set. [Frozen protocol](../results/no2_three_routes/design/protocol.json), [implementation](../src/thz_isac/no2_design.py), [physical provenance](../results/no2_three_routes/physical/manifest.json).

## Results

| Design at 100 s | Worst design RMSE / 25 μg/m³ |
| --- | ---: |
'''+ '\n'.join(f'| {label} | {value(name)} |' for name,label in zip(cases,labels))+'''

**RESULT:** These are achieved conditional risks, not measured concentration errors. The equal-dwell fine grid alone makes little difference; optimizing dwell makes the main improvement. Fine-grid independent spectral error of ±0.0001 dB still has an exact represented-LP noise-free lower bound of 1.923285, above the unit target. [All 30 results](../results/no2_three_routes/design/summary.csv), [resources](../results/no2_three_routes/design/resources.csv), [floor certificates](../results/no2_three_routes/requirements/floor_certificates.json), [independent checks](../results/no2_three_routes/verification/checks.json).

**SELF-DERIVED:** Differencing cancels only identical persistent calibration. Independent radius-ε errors leave a radius-2ε difference error. At equal total time, two independent half-budget readings give four times the noise variance. They estimate concentration changes; an absolute estimate requires a baseline and its uncertainty. Complete spectral differencing with the full induced covariance leaves GLS information unchanged when the original offset is already a nuisance. [Derivation](../paper/no2_three_routes.tex), [spectral control](../results/no2_three_routes/design/spectral_difference_control.json), [analytic tests](../tests/test_no2_design.py).

**RESULT / INFERENCE:** Declaring calibration to lie in smooth polynomial modes is a stronger assumption. Each mode receives one third of the pointwise budget remaining after a residual box; the total set is a subset of the original box. The mixed model requires the arbitrary residual to be bounded by 0.00001 dB, which has not been measured. With the frozen 100 s operators, pure polynomial and mixed calibration reach the design target at sufficient acquisition times of 181.798 and 248.809 s. These are constructive conditional times, not minimum necessary times. The mixed case radiates 0.1973 J; receiver electrical power is excluded. [Time calculation and traces](../results/no2_three_routes/requirements/fixed_design_time.csv), [uncertainty-set definition](../paper/no2_three_routes.tex).

**RESULT:** The mixed structured fine design gives worst error 1.291 on 16 new modeled states at 100 s with nominal covariance. For the 24 hourly real-weather pairs, its worst absolute atmospheric bias is 3.201, while the stable-calibration differential estimator has worst change bias 0.411. Its noise SD is 2.399 and pair RMSE is 2.434, so canceling atmospheric drift does not restore feasibility at this budget. The absolute and change estimates are distinct targets. [Complete evaluation](../results/no2_three_routes/evaluation/summary.csv), [pair metadata](../results/no2_three_routes/evaluation/pair_metadata.csv), [model-state metadata](../results/no2_three_routes/evaluation/new_state_metadata.csv).

**RESULT / LIMITATION:** Eleven of 24 pairs have a visited frequency below 5 dB under modeled real weather. The nominal design regime therefore fails in part of this stress set. The weather-dependent covariance replay reaches 26.280 for mixed structured absolute retrieval and 47.243 for stable differences, but those magnitudes extrapolate the coherent approximation and are not validated performance predictions. The physical model uses observed surface weather with assumed profiles and a repeated fixed slant geometry, not synchronized THz observations. [Evaluation protocol](../results/no2_three_routes/evaluation/protocol.json), [full per-state outcomes](../results/no2_three_routes/evaluation/errors.csv).

## Calibration characterization and remaining evidence

**SOURCE STATEMENT:** Bjarnason et al. use separate sample and reference spectra and propagate both noise contributions; their apparatus also exhibits source repeatability and tuning limitations. Its gas, band and laboratory hardware differ from this proposal. It supports measuring these effects, not transferring a drift amplitude or polynomial model to our receiver. [NIST primary PDF](https://tsapps.nist.gov/publication/get_pdf.cfm?pub_id=32980), physical p. 2, Eqs. 4–6; pp. 5–6, Section 5.A and Fig. 4; p. 8, tuning-repeatability discussion.

**IMPLEMENTATION:** The characterization CLI accepts actual repeated reference measurements as a long CSV with `time`, `frequency_ghz`, `error_db`. Error means observed minus known reference. It rejects missing or duplicate frequency/time samples, uses chronological 60/20/20 percent timestamp splits, fits a training-only mean spectrum and fixed-degree polynomial basis, and reports heldout residual and joint-envelope coverage. Training maxima are descriptive and do not guarantee future coverage. A reference's own uncertainty must be recorded and propagated; none is supplied here. [CLI](../scripts/characterize_receiver_calibration.py), [implementation and tests](../tests/test_no2_design.py).

```powershell
python scripts/characterize_receiver_calibration.py C:/path/to/reference_sweeps.csv --output results/measured_receiver_calibration --degree 2
```

**INFERENCE / NEXT STEP:** With HITRAN and I2R alone, route 2 can specify and test calibration requirements but cannot establish measured drift. The most promising tested computational direction is jointly optimized dwell with a justified small structured residual. It still needs receiver measurements, a humidity-aware acquisition rule, geometry control and synchronized concentration/column truth. Temporal differencing is useful for relative change and bias cancellation, with an explicit noise and reference cost. [Current manuscript analysis](../paper/no2_three_routes.tex), [measured-data requirements](continuation_measurement_protocol.md).

## Verification, provenance and failed attempts

**RESULT:** An independent verifier recomputes 30 design rows, 1952 stress outcomes, every target/nuisance identity, integer allocation and energy budget, and both exact rational dual certificates. Eight new analytic tests cover covariance, dwell, drift structure and calibration split leakage. Initial import-environment and fixed-allocation solver failures were retained; the final design consistently evaluates the jointly optimized operator after dwell rounding. No stress outcome selected the estimator or uncertainty model. An evaluation started prematurely after the first failed design run was stopped before error outcomes were computed or inspected, then restarted after all designs passed. [Verification](../results/no2_three_routes/verification/checks.json), [initial attempts](../results/no2_three_routes/attempts/initial_design/explanation.json), [final discretization decision](../results/no2_three_routes/attempts/whitened_fixed_reoptimization/explanation.json).

CPU, software versions, runtime, sampled memory and input/output hashes are recorded in separate physical/design/evaluation/requirements/verification manifests. The incoming manuscript and documentation were copied before editing. [Before snapshot](../results/no2_three_routes/before), [frequency schedule](../results/no2_three_routes/report/frequency_schedule_100s.csv), [figure](../results/no2_three_routes/report/no2_routes.pdf).
'''
    (ROOT/'docs/no2_three_routes.md').write_text(note,encoding='utf-8')
    run.finish(extra={'input_hashes':{str(p):digest(p) for p in [out/'design/summary.csv',out/'evaluation/summary.csv',out/'design/operators.npz']},
        'manuscript_section_sha256':digest(ROOT/'paper/no2_three_routes.tex'),'research_note_sha256':digest(ROOT/'docs/no2_three_routes.md')})


if __name__=='__main__':main()
