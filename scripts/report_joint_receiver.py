"""Render full time/calibration tables, low recall and nominal 95% controls."""
import json
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import LogNorm
from joint_receiver_support import ROOT,OUT,TARGETS
NAMES={'H2CO':'Formaldehyde','CH3OH':'Methanol','CH3CN':'Acetonitrile','CH3Cl':'Chloromethane','HCOOH':'Formic acid',
       'PM2.5':'Fine PM','PMcoarse':'Coarse PM','PM10':'Total PM10'}


def main():
    v=json.loads((OUT/'verification.json').read_text())
    if v['status']!='passed': raise RuntimeError('Verify before reporting')
    r=pd.read_csv(OUT/'response_metrics.csv');s=pd.read_csv(OUT/'sensitivity.csv')
    core=r[(r.plan=='selected')&(r.profile=='standard')]
    base=core[(core.total_s==20)&(core.residual_std_db==.0001)]
    low=base[(base.control=='low')&(base.concentration_ug_m3==1)].set_index('target')
    floors=base[base.control=='response95'].set_index('target')
    gas=TARGETS[:5];times=[2.,20.,100.];sigmas=[0.,.0001,.001]
    global_table=pd.read_csv(OUT/'global_comparison.csv')
    global_rows=[];global_tex=[]
    for n in TARGETS:
        group=global_table[global_table.target==n];valid=group[group.status=='computed']
        available=valid.response_lod95_ug_m3.notna().sum()
        lo,hi=valid.predicted_recall_pct.min(),valid.predicted_recall_pct.max()
        reference=valid.reference_concentration_ug_m3.iloc[0]
        global_rows.append(f'| {n} | {reference:g} | {len(valid)} | {len(group)-len(valid)} | {lo:.3f}–{hi:.3f}% | {valid.predicted_relative_rmse_pct.min():.3g}–{valid.predicted_relative_rmse_pct.max():.3g}% | {available} |')
        global_tex.append(f'{n.replace("PMcoarse","Coarse PM")} & {reference:g} & {lo:.3f}--{hi:.3f} & {available} \\\\')
    fig,axes=plt.subplots(2,2,figsize=(10,7),layout='constrained')
    for i,nf in enumerate([6.,17.]):
        for j,n in enumerate(['PM2.5','PM10']):
            ax=axes[i,j]
            for label in ['uniform','selected']:
                for profile in ['standard','igra_01']:
                    sub=global_table[(global_table.target==n)&(global_table.noise_figure_db==nf)&(global_table.plan==label)&(global_table.profile==profile)&(global_table.total_s==20)&(global_table.residual_std_db==.0001)].sort_values('elevation_deg')
                    ax.plot(sub.elevation_deg,sub.predicted_relative_rmse_pct,marker='o',linestyle='-' if label=='selected' else '--',label=f'{label}, {"January" if profile=="igra_01" else "standard"}')
            ax.set(yscale='log',xticks=[30,45,60,90],xlabel='Elevation (degrees)',ylabel='Predicted relative RMSE (%)',title=f'{n}, receiver noise figure {nf:g} dB')
            ax.grid(alpha=.25);ax.legend(fontsize=8)
            if nf==17:ax.text(.02,.60,'Standard atmosphere at 30°: rejected',transform=ax.transAxes,fontsize=8,bbox=dict(facecolor='white',edgecolor='none',alpha=.9))
    fig.suptitle('PM2.5 and PM10 in the common multivariable comparison\n20 s total, assumed 0.0001 dB residual, 23 dBm; conditional predictions',fontsize=12)
    fig.savefig(OUT/'global_pm_comparison.png',dpi=180);plt.close(fig)
    def choose(target,t,sigma,control='low',concentration=1.):
        frame=core[(core.target==target)&(core.total_s==t)&(core.residual_std_db==sigma)&(core.control==control)]
        if control=='low': frame=frame[np.isclose(frame.concentration_ug_m3,concentration)]
        return frame.iloc[0]
    summary='\n'.join(f"| {NAMES[n]} | {low.loc[n].recall_pct:.2f}% | {low.loc[n].miss_rate_pct:.2f}% | {floors.loc[n].concentration_ug_m3:.3f} | {floors.loc[n].recall_pct:.2f}% | {floors.loc[n].recall_ci95_lower_pct:.2f}–{floors.loc[n].recall_ci95_upper_pct:.2f}% |" for n in gas)
    def grid(kind):
        rows=[]
        for t in times:
            for sigma in sigmas:
                values=[]
                for n in gas:
                    row=choose(n,t,sigma,control=kind)
                    values.append(f'{row.recall_pct:.2f}%' if kind=='low' else f'{row.concentration_ug_m3:.3f}')
                rows.append(f'| {t:.0f} | {sigma:g} | '+' | '.join(values)+' |')
        return '\n'.join(rows)
    pmrows=[]
    for t in times:
        for sigma in sigmas:
            values=[choose(n,t,sigma,concentration=c) for n,c in [('PM2.5',15.),('PMcoarse',45.),('PM10',45.)]]
            pmrows.append(f'| {t:.0f} | {sigma:g} | '+' | '.join(f'{row.recall_pct:.2f}%' for row in values)+' | None within the evaluated domain |')
    trade=json.loads((OUT/'communication_tradeoff.json').read_text())
    budget=pd.read_csv(OUT/'calibration_requirements.csv')
    c20=budget[(budget.target=='CH3CN')&(budget.total_s==20)&(budget.concentration_ug_m3==1)].iloc[0]
    uniform=r[(r.plan=='uniform')&(r.profile=='standard')&(r.control=='low')&(r.target=='CH3CN')&(r.concentration_ug_m3==1)].iloc[0]
    january=r[(r.plan=='selected')&(r.profile=='igra_01')&(r.control=='low')&(r.target=='CH3CN')&(r.concentration_ug_m3==1)].iloc[0]
    # All panels use the same 0..100 scale and display even the weakest rates.
    fig,axes=plt.subplots(2,4,figsize=(13,6.7),layout='constrained')
    for ax,n in zip(axes.flat,TARGETS):
        concentration=1. if n in gas else 15. if n=='PM2.5' else 45.
        values=np.array([[choose(n,t,sigma,concentration=concentration).recall_pct for sigma in sigmas] for t in times])
        im=ax.imshow(values,vmin=0,vmax=100,cmap='viridis',aspect='auto')
        ax.set(title=f'{NAMES[n]}: {concentration:g} µg/m³',xticks=range(3),xticklabels=['0','0.0001','0.001'],yticks=range(3),yticklabels=['2','20','100'],xlabel='Residual std (dB)',ylabel='Total time (s)')
        for i in range(3):
            for j in range(3): ax.text(j,i,f'{values[i,j]:.2f}%',ha='center',va='center',color='black' if values[i,j]>60 else 'white',fontsize=9)
    fig.colorbar(im,ax=axes,label='Simulated recall (%)',shrink=.8)
    fig.suptitle('Selected five-VOC receiver: time and calibration jointly determine recall\nStandard atmosphere, 45°, matched reference; calibration is assumed, not measured',fontsize=12)
    fig.savefig(OUT/'recall_time_calibration.png',dpi=180);plt.close(fig)
    fig,axes=plt.subplots(2,3,figsize=(11,6.5),layout='constrained')
    for ax,n in zip(axes.flat,gas):
        values=np.array([[choose(n,t,sigma,control='response95').concentration_ug_m3 for sigma in sigmas] for t in times])
        ax.imshow(values,norm=LogNorm(vmin=.3,vmax=120),cmap='YlOrRd',aspect='auto')
        ax.set(title=NAMES[n],xticks=range(3),xticklabels=['0','0.0001','0.001'],yticks=range(3),yticklabels=['2','20','100'],xlabel='Residual std (dB)',ylabel='Total time (s)')
        for i in range(3):
            for j in range(3): ax.text(j,i,f'{values[i,j]:.3g}',ha='center',va='center',color='white' if values[i,j]>35 else 'black')
    axes.flat[-1].axis('off');axes.flat[-1].text(.5,.5,'PM2.5, coarse PM and PM10\n\nNo valid 95% response limit\nwithin the evaluated absorption domain\nfor any of these nine conditions.',ha='center',va='center',transform=axes.flat[-1].transAxes)
    fig.suptitle('Concentration for nominal 95% detection power (µg/m³)\nSelected design; standard 45°; each cell uses its own time and calibration assumption',fontsize=12)
    fig.savefig(OUT/'limits_time_calibration.png',dpi=180);plt.close(fig)
    # A compact full metrics appendix keeps the low and 95% comparisons visible
    # for each gas rather than showing a favorable species alone.
    details=[]
    for n in gas:
        text=f'### {NAMES[n]} ({n})\n\n| Total s | Residual dB | Recall at 1 µg/m³ | Recall at 5 µg/m³ | Recall at 10 µg/m³ | 95% response concentration µg/m³ | Actual recall there | Relative RMSE there |\n|---|---|---:|---:|---:|---:|---:|---:|\n'
        for t in times:
            for sigma in sigmas:
                lows=[choose(n,t,sigma,concentration=c).recall_pct for c in [1.,5.,10.]];f=choose(n,t,sigma,control='response95')
                text+=f'| {t:.0f} | {sigma:g} | {lows[0]:.2f}% | {lows[1]:.2f}% | {lows[2]:.2f}% | {f.concentration_ug_m3:.3f} | {f.recall_pct:.2f}% | {f.relative_rmse_pct:.2f}% |\n'
        details.append(text)
    content=f'''# Joint receiver design: low recall and 95% limits across time and calibration

The new design improves all five VOC information limits under the exact standard-atmosphere calculation. **At 20 s total and an assumed 0.0001 dB differential residual, acetonitrile at 1 µg/m³ has {low.loc['CH3CN'].recall_pct:.2f}% simulated recall**, exact 95% interval {low.loc['CH3CN'].recall_ci95_lower_pct:.2f}–{low.loc['CH3CN'].recall_ci95_upper_pct:.2f}%. The fresh uniform-design comparison is {uniform.recall_pct:.2f}%. Both jointly fit five VOCs and two PM masses with the same resources and eight-output false-alarm family. **Calibration accuracy and hardware performance remain unmeasured.**

## What changed and why

The previous uniform hopping plan was not selected against the five-gas inverse problem. A deterministic coordinate-exchange screen now selects sixteen nonoverlapping blocks within 220–330 GHz using only the standard 45-degree design case. Its criterion improves the worst relative uncertainty among five gases while keeping PM and gain/background/interferent nuisance effects in the fit. Three deterministic starts are retained; no global optimum is claimed.

The coarse center approximation only selects a candidate. Exact Voigt spectra, Mie extinction, refracted paths and atmospheric emission were recomputed at every selected tone before evaluating it. January weather and fresh random responses did not select frequencies. Uniform and selected schedules have one RF chain, sixteen 16 MHz blocks, 1 MHz tone spacing, 23 dBm transmitting power, 6 dB receiver noise figure, identical CP/pilot overhead, both reference/sample acquisitions and 1 ms settling per hop. Frame rounding is charged at every duration.

The primary comparison below uses standard atmosphere at 45 degrees and matched reference weather. Every duration is **reference plus sample**, split equally. Residuals are zero mean correlated dB errors with a 10 GHz correlation length, drawn once per acquisition. The residual does not average away with payload symbols. Zero is an ideal extra-residual benchmark, not zero thermal noise.

## Low concentration and nominal 95% response side by side

This table uses **20 s total, 0.0001 dB assumed residual** throughout. It must not be read as a time-independent or calibration-independent detection limit. Each positive class and null class contains 10,000 trials.

| Target | Recall at 1 µg/m³ | Missed at 1 µg/m³ | Nominal 95% response concentration (µg/m³) | Actual simulated recall there | Exact 95% recall interval there |
|---|---:|---:|---:|---:|---:|
{summary}

The primary family false-alarm frequency is {low.loc['CH3CN'].family_false_alarm_pct:.2f}%, under the fixed 1% budget. The 95% target is solved with positive-signal noise variance before simulation. Actual fractions near 95% remain unrounded to that target. A 95% detection rate is also not a 5% concentration error: relative RMSE at these limits is about 21% in this model.

## Complete time and calibration comparison

**Simulated recall at 1 µg/m³.** All five VOCs remain unknown parameters in every fit. Other target abundances are zero in these single-target positive controls; separate simultaneous mixture controls are retained in the CSV.

| Total reference + sample (s) | Residual std (dB) | H2CO | CH3OH | CH3CN | CH3Cl | HCOOH |
|---:|---:|---:|---:|---:|---:|---:|
{grid('low')}

**Concentration required for nominal 95% response power, in µg/m³.** Each cell uses the time and calibration in its row. Finite simulation power checks, intervals and ppm conversions are retained separately.

| Total reference + sample (s) | Residual std (dB) | H2CO | CH3OH | CH3CN | CH3Cl | HCOOH |
|---:|---:|---:|---:|---:|---:|---:|
{grid('response95')}

![Recall over time and calibration](../results/joint_receiver_revision/recall_time_calibration.png)

![Conditional 95 percent limits](../results/joint_receiver_revision/limits_time_calibration.png)

For example, the local acetonitrile requirement for 95% power at 1 µg/m³ and 20 s is residual standard deviation no larger than approximately {c20.max_random_std_db_for_local_95pct:.6f} dB under this covariance model. The [acceptance table](../results/joint_receiver_revision/calibration_requirements.csv) repeats this inversion for all targets and times and adds a separate bound on persistent signed bias in the presence of the assumed 0.0001 dB random residual. These are requirements, not demonstrated stability.

## PM must use the same time/calibration comparison

Here fine PM is tested at 15 µg/m³, coarse PM at 45 µg/m³ and PM10 at 45 µg/m³. PM10 is injected with the declared 49:41 fine/coarse mixture ratio and estimated with its full covariance contrast. These are comparison concentrations, not a compliance assessment. Additional 49 and 90 µg/m³ controls and the original public 49/41 mixture are retained in the full table.

| Total s | Residual std dB | Fine PM recall at 15 µg/m³ | Coarse PM recall at 45 µg/m³ | PM10 recall at 45 µg/m³ | Valid 95% response concentration |
|---:|---:|---:|---:|---:|---|
{chr(10).join(pmrows)}

PM recall remains at approximately the false-alarm scale. No finite 95% response solution lies within the ≤1 dB added-absorption domain for these nine conditions. Very large local information scales remain in the sensitivity CSV only as diagnostics; they are not valid high-concentration sensing claims. The failed PM1/fine/coarse separation and unmeasured composition are explained in the [species and methods guide](50_species_methods_and_percentage_guide.md).

## Global comparison: all VOCs, PM2.5 and PM10 under the same variables

The [common global CSV](../results/joint_receiver_revision/global_comparison.csv) contains **2,304 rows across 288 operating conditions**, with all eight outputs present in every condition. It crosses two band plans, two atmospheres (standard and January), four elevations (30, 45, 60, 90 degrees), three total times (2, 20, 100 s), three assumed residuals (0, 0.0001, 0.001 dB), and two receiver noise figures (6, 17 dB). Power is fixed at 23 dBm; residual correlation length is 10 GHz and reference weather is matched. These are conditional predictions using positive-response noise variance; the separate Monte Carlo table supplies simulated frequencies and binomial intervals. There are no field measurements in either table.

Each output has 270 computed conditions and 18 rejected conditions. A rejected condition is unavailable, not a zero recall or a successful limit. Ranges below are envelopes over different conditions, not uncertainty intervals or a typical deployment. Gas and PM reference concentrations differ and therefore their percentages must not be interpreted as a same-concentration species ranking.

| Output | Reference µg/m³ | Computed conditions | Rejected conditions | Predicted recall range | Predicted relative RMSE range | Conditions with valid 95% response limit |
|---|---:|---:|---:|---:|---:|---:|
{chr(10).join(global_rows)}

PM10 is always the fine plus coarse mass contrast with cross covariance; its positive control has fine mass fraction 49/90. PM2.5 and PM10 have no valid 95% response limit anywhere in this tested grid. The complete CSV provides the exact conditions, misses, concentration error, limit validity, SNR and resource fields for each row. The figure below shows a declared 20 s/0.0001 dB slice; the CSV also contains the other time/calibration combinations.

![PM2.5 and PM10 across atmosphere, elevation, bands and receiver noise](../results/joint_receiver_revision/global_pm_comparison.png)

## Independent-condition checks and remaining failures

At 20 s/0.0001 dB and matched January weather, selected-design acetonitrile recall at 1 µg/m³ is {january.recall_pct:.2f}% (exact interval {january.recall_ci95_lower_pct:.2f}–{january.recall_ci95_upper_pct:.2f}%). This is a conditional weather control, not a population or field guarantee. The four tested elevations are 30, 45, 60 and 90 degrees; the full sensitivity table recomputes both schedules across them. The separate January-background mismatch applied to a frozen standard operator still produces bias; matched-weather success does not solve unknown weather.

Changing residual frequency correlation changes the limits even at the same standard deviation. Independent unknown hop gains fail numerical target separation, the 17 dB noise-figure stress degrades gas performance, and the unamplified converter fails the SNR gate. These outcomes are in [stress sensitivity](../results/joint_receiver_revision/stress_sensitivity.csv).

Sixteen fresh moving raw coded-frame spot checks cover every selected center; passive sensing preserves decoded output under the bounded existing synchronization model. The selected schedule nevertheless loses **{trade['gaussian_rate_loss_vs_best_tested_fixed_pct']:.2f}%** of the Gaussian-input information-rate benchmark relative to the best fixed block among the tested schedules at equal instantaneous bandwidth and power. This includes frequency choice and scheduling, whereas the earlier 1.382% figure isolated scheduling counts. Neither is QPSK coded throughput or a measured hardware rate. A globally optimized communication baseline could be stronger. The original zero-capacity-degradation ambition is therefore not established for the architecture.

## Detailed per-VOC percentage tables

All tables below use the selected design, standard atmosphere, 45 degrees and matched reference. Every row has its own time and calibration assumption. The [full CSV](../results/joint_receiver_revision/response_metrics.csv) additionally provides miss rate, per-target false alarms, specificity, exact binomial intervals, precision/F1 at 50% test prevalence, balanced accuracy, signed bias, absolute/relative RMSE, negative estimates and surface-equivalent gas ppm.

{chr(10).join(details)}

## Verification, interpretation and reproduction

The retained [verification](../results/joint_receiver_revision/verification.json) replays {v['checks']:,} checks over {v['metric_rows']} percentage/error rows, {v['sensitivity_rows']} sensitivity rows and {v['global_comparison_rows']} common global rows. There are twelve response cases, including all nine primary time/calibration combinations. These checks verify numerical/reporting consistency, not physical truth. Results preserve low recalls, failed PM limits, source hashes and resource costs.

Run `python scripts/select_joint_receiver.py`, `python scripts/compute_joint_receiver_physics.py`, `python scripts/evaluate_joint_receiver.py`, `python scripts/stress_joint_receiver.py`, `python scripts/global_joint_receiver_comparison.py`, `python scripts/verify_joint_receiver.py`, and `python scripts/report_joint_receiver.py`. Use one BLAS thread per physics worker. The selection must remain frozen before evaluating the held-out conditions and response draws. Existing snapshots remain historical; the new deliverable manifest records this revision.

The [complete audit](49_completion_audit_and_fixes.md) lists every identified remaining issue and its completion criterion. The main unresolved items are achievable RF/calibration performance, useful PM information, full receiver dynamics/reference conditions, unknown weather/profiles/baseline, independent paired measurements and environmental applicability.
'''
    (ROOT/'docs/51_joint_design_time_calibration_results.md').write_text(content,encoding='utf-8')
    texrows=[]
    for t in times:
        for sigma in sigmas:
            vals=' & '.join(f'{choose(n,t,sigma,control="response95").concentration_ug_m3:.2f}' for n in gas)
            texrows.append(f'{t:.0f} & {sigma:g} & {vals} \\\\')
    tex=r'''\section{Five-gas band selection and time/calibration limits}
The frozen uniform schedule was revised using a five-gas joint design criterion, retaining both PM masses and all gain/background/interferent nuisance terms. A standard-atmosphere coordinate-exchange screen chose sixteen blocks; exact physical spectra were then recomputed. Neither January weather nor the new response samples selected the bands. Resources remain one sequential RF chain, sixteen 16 MHz blocks, identical pilots/CP, 23 dBm active power, 6 dB noise figure, matched reference, charged settling and equal reference/sample time. A global optimum is not claimed.

At 20 s total and an \emph{assumed}, unmeasured 0.0001 dB residual, selected-design acetonitrile recall at 1 \ugm\ is RECALL\% (exact 95\% interval LOW--HIGH\%), versus OLD\% for the fresh uniform-design control. The family false-alarm frequency is FAMILY\%. Every result jointly fits five gases and fine/coarse PM. The nominal 95\% response concentrations change with both time and calibration (Table~\ref{tab:joint-time-cal}); they solve the positive-signal variance equation before Monte Carlo evaluation. PM has no valid 95\% response solution within the evaluated $\leq1$ dB absorption domain in any listed condition.

\begin{table}[t]
\centering\scriptsize
\caption{Nominal 95\% response concentration (\ugm), selected five-gas design, standard atmosphere at $45^\circ$, matched reference. Total time includes reference and sample; $\sigma$ is assumed residual standard deviation in dB. PM limits remain unavailable in the evaluated domain.}
\label{tab:joint-time-cal}
\begin{tabular}{rrrrrrr}\toprule
Time (s) & $\sigma$ & H$_2$CO & CH$_3$OH & CH$_3$CN & CH$_3$Cl & HCOOH\\\midrule
ROWS
\bottomrule\end{tabular}
\end{table}

The retained percentage tables report 1, 5 and 10 \ugm\ VOC recall, low-concentration PM recall, misses, false alarms, exact binomial intervals, relative bias/RMSE and precision/F1 under an explicitly artificial 50\% prevalence. A nominal 95\% detection point is not a 5\% concentration-error point: relative RMSE is approximately 21\% there. Zero observed misses do not imply zero population failure probability. Persistent residual covariance is drawn once per acquisition and does not diminish once per payload symbol.

Formaldehyde, methanol, acetonitrile, chloromethane and formic acid are distinct molecular targets; CO/O$_3$/SO$_2$/NO$_2$ remain interferents. PM2.5 and coarse PM are disjoint modeled masses, while PM10 is their sum with cross covariance. The proposed PM1 subdivision remains numerically rejected. Under the assumed material model, smooth Rayleigh absorption is largely removed by gain-slope fitting and leading scattering shapes are nearly shared among size modes. Full Mie calculations do not restore practically useful mass information in these cases.

Fresh moving raw-frame spot checks at each selected frequency preserve decoded packets, but the schedule loses LOSS\% of the Gaussian-input rate benchmark relative to the best tested fixed block at equal bandwidth and power. This architecture comparison is distinct from passive observation preserving an already scheduled modem and from coded QPSK throughput. Unknown weather, relative hop gains, realistic timing/oscillator effects, material calibration and independent concentration truth remain open. The results are conditional computational improvements, not validated atmospheric sensor performance.

The common global comparison includes all five VOCs, PM2.5, coarse PM and PM10 in every condition: two band plans, two atmospheres, four elevations, three durations, three calibration residuals and two noise figures (6 and 17 dB), at fixed 23 dBm power. Of 288 conditions, 270 pass and 18 are explicitly rejected for all outputs. Table~\ref{tab:global-all} summarizes the 2304 retained rows. PM10 includes fine/coarse cross covariance. No valid 95\% PM limit exists in this grid. These conditional predictions include positive-response variance; their ranges are operating-condition envelopes, not confidence intervals or measured performance.

\begin{table}[t]
\centering\scriptsize
\caption{Common global comparison. Reference concentration $c$ is in \ugm; recall is predicted percent across valid conditions. $N_{95}$ counts conditions with a response limit inside the evaluated absorption domain. Each output has 270 computed and 18 rejected conditions.}
\label{tab:global-all}
\begin{tabular}{lrrr}\toprule
Output & $c$ & Recall range (\%) & $N_{95}$\\\midrule
GLOBALTABLE
\bottomrule\end{tabular}
\end{table}
'''
    tex=tex.replace('GLOBALTABLE','\n'.join(global_tex))
    replacements=dict(RECALL=f"{low.loc['CH3CN'].recall_pct:.2f}",LOW=f"{low.loc['CH3CN'].recall_ci95_lower_pct:.2f}",HIGH=f"{low.loc['CH3CN'].recall_ci95_upper_pct:.2f}",OLD=f'{uniform.recall_pct:.2f}',FAMILY=f"{low.loc['CH3CN'].family_false_alarm_pct:.2f}",LOSS=f"{trade['gaussian_rate_loss_vs_best_tested_fixed_pct']:.2f}",ROWS='\n'.join(texrows))
    for key,value in sorted(replacements.items(),key=lambda v:-len(v[0])):tex=tex.replace(key,value)
    (ROOT/'paper/joint_receiver_revision.tex').write_text(tex,encoding='utf-8')
    print('Saved full condition tables, percentage figures and manuscript section')


if __name__=='__main__':main()
