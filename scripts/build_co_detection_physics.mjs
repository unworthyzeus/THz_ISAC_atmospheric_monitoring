import fs from 'node:fs/promises';
import path from 'node:path';
import {pathToFileURL,fileURLToPath} from 'node:url';

const ROOT=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const BUILD=path.join(ROOT,'tmp/co_detection_physics_deck');
const OUT=path.join(ROOT,'output/presentations');
const SKILL='C:/Users/guill/.codex/plugins/cache/openai-primary-runtime/presentations/26.1013.11914/skills/presentations';
const MODULES='C:/Users/guill/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules';
const PYTHON='C:/Users/guill/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe';
process.env.RUNTIME_NODE_MODULES=MODULES;
const {Presentation,PresentationFile,FileBlob}=await import(pathToFileURL(path.join(MODULES,'@oai/artifact-tool/dist/artifact_tool.mjs')));
const {finalizePresentation,applyPresentationChartFont,resolvePresentationFont}=await import(pathToFileURL(path.join(SKILL,'container_tools/artifact_tool_utils.mjs')));
const evidence=JSON.parse(await fs.readFile(path.join(ROOT,'results/co_detection_physics_2026_10_15/evidence.json'),'utf8'));
const FONT=resolvePresentationFont({fontFamily:'Georgia',availableFonts:['Georgia']});
const C={paper:'#F4F0E8',ink:'#242421',rust:'#B4472B',muted:'#6E6A61',rule:'#D5CEC1',light:'#F5F1E9',copper:'#D89474',olive:'#69725D'};
const p=Presentation.create({slideSize:{width:1280,height:720}});
const pages=[],chartOwners=[],tableOwners=[];
const sources={
  hitran:'https://hitran.org/docs/definitions-and-units/',
  beer:'https://hitran.org/docs/cross-sections-definitions/',
  dipole:'https://cccbdb.nist.gov/diplistx.asp',
  rotor:'https://www.nist.gov/pml/diatomic-spectral-database/diatomic-spectral-database-1s-ground-state-molecules',
  coherence:'https://ocw.mit.edu/courses/5-35-introduction-to-experimental-chemistry-fall-2012/18a908091e0258ba553794ac1cd0a517_MIT5_35F12_Module_1LS2.pdf',
  dephasing:'https://ocw.mit.edu/courses/5-74-introductory-quantum-mechanics-ii-spring-2009/c9108a344550e61973b5ecb4379cdf1e_MIT5_74s09_lec09.pdf',
  broadening:'https://physics.nist.gov/Pubs/AtSpec/node20.html',
  mats:'https://pages.nist.gov/MATS/MATS%20Summary.html',
  continuum:'https://hitran.org/mtckd/',
  cia:'https://hitran.org/cia/',
  itu:'https://www.itu.int/dms_pubrec/itu-r/rec/p/R-REC-P.676-13-202208-I!!PDF-E.pdf',
  jpl:'https://spec.jpl.nasa.gov/ftp/pub/catalog/c028001.cat',
  local:'https://github.com/unworthyzeus/THz_ISAC_atmospheric_monitoring/blob/50393b2/docs/59_restart_observability_2026_10_14.md',
  numbers:'https://github.com/unworthyzeus/THz_ISAC_atmospheric_monitoring/blob/50393b2/results/restart_2026_10_14/co_line_examples.csv',
  oldcurve:'https://github.com/unworthyzeus/THz_ISAC_atmospheric_monitoring/blob/50393b2/scripts/prepare_zenith_compact_slides.py',
};
function text(s,value,x,y,w,h,size=26,color=C.ink,bold=false,extra={}){
  const b=s.shapes.add({geometry:'textbox',name:value.slice(0,70),position:{left:x,top:y,width:w,height:h},fill:'none',line:{fill:'none',width:0}});
  b.text=value;b.text.style={typeface:FONT,fontSize:size,color,bold,wrap:'square',autoFit:'none',insets:0,verticalAlignment:'top',...extra};return b;
}
function equation(s,value,x,y,size=43,color=C.ink){
  let cursor=x;
  for(const part of value.split(/([_^]\{[^}]+\}|[_^][A-Za-z0-9])/g).filter(Boolean)){
    const sub=part.startsWith('_'),sup=part.startsWith('^'),script=sub||sup,literal=script?part.slice(1).replace(/[{}]/g,''):part,pt=script?size*.61:size;
    const w=[...literal].reduce((a,c)=>a+(evidence.font_widths_at_100px[c]??58),0)*pt/100+2;
    text(s,literal,cursor,y+(sub?size*.48:sup?-size*.08:0),w+4,size*1.55,pt,color,false,{wrap:'none'});cursor+=w;
  }
}
function page(title,{dark=false,footer=''}={}){
  const s=p.slides.add();s.background.fill=dark?C.ink:C.paper;
  text(s,title,64,43,1152,111,44,dark?C.light:C.ink);
  if(footer)text(s,footer,64,668,1090,32,16,dark?'#C6BFB3':C.muted);
  text(s,String(p.slides.items.length).padStart(2,'0'),1170,668,48,28,17,dark?'#C6BFB3':C.muted,false,{alignment:'right'});
  pages.push({title,script:'',notes:'',sources:[]});return s;
}
function notes(s,script,detail,keys=[]){
  const r=pages[p.slides.items.indexOf(s)];r.script=script;r.notes=detail;r.sources=keys.map(k=>({label:k,url:sources[k]}));
  s.speakerNotes.textFrame.setText('Speaking script\n'+script+'\n\nScientific notes\n'+detail+'\n\nSources\n'+r.sources.map(r=>r.label+': '+r.url).join('\n'));
}
function table(s,values,x,y,w,h,widths,size=25){
  const tb=s.tables.add({rows:values.length,columns:values[0].length,left:x,top:y,width:w,height:h,columnWidths:widths.map(v=>v*w),values});
  tb.borders.assign({fill:C.rule,width:.7});
  tb.cells.block({row:0,column:0,rowCount:values.length,columnCount:values[0].length}).assign({textStyle:{typeface:FONT,fontSize:size,color:C.ink},margins:{left:15,right:15,top:10,bottom:10},anchor:'center'});
  for(let r=0;r<values.length;r++){tb.rows[r].height=h/values.length;for(let c=0;c<values[0].length;c++){
    tb.getCell(r,c).fill=r===0?C.ink:C.paper;
    tb.getCell(r,c).text.style={typeface:FONT,fontSize:size,color:r===0?C.light:C.ink,bold:r===0};
  }}tableOwners.push(p.slides.items.indexOf(s)+1);return tb;
}
function chart(s,series,x,y,w,h,xAxis,yAxis,legend=false){
  const ch=s.charts.add('scatter',{position:{left:x,top:y,width:w,height:h},
    series:series.map(r=>({name:r.name,xValues:r.x.map(v=>Number(v.toPrecision(14))),values:r.y.map(v=>Number(v.toPrecision(14))),line:{fill:r.color??C.rust,width:3},marker:{symbol:'none'}})),
    scatterOptions:{style:'line'},hasLegend:legend,legend:{position:'bottom',overlay:false,textStyle:{fontSize:19,fill:C.ink}},
    xAxis:{line:{fill:C.muted,width:1},textStyle:{fontSize:20,fill:C.ink},numberFormatCode:'0',...xAxis},
    yAxis:{line:{fill:C.muted,width:1},textStyle:{fontSize:20,fill:C.ink},majorGridlines:{fill:C.rule,width:.7},...yAxis},
    chartFill:C.paper,plotAreaFill:C.paper,chartLine:{fill:'none',width:0},plotAreaLine:{fill:'none',width:0}});
  applyPresentationChartFont(ch,{fontFamily:FONT});chartOwners.push(p.slides.items.indexOf(s)+1);return ch;
}

// 1. Preserve the requested aesthetic while changing the question.
{
  const s=p.slides.add();s.background.fill=C.ink;
  s.images.add({blob:new Uint8Array(await fs.readFile(path.join(OUT,'co_observability_assets/spectral_cover.png'))),contentType:'image/png',alt:'Decorative abstract light bands; no measured spectrum',fit:'cover',position:{left:0,top:0,width:1280,height:720}});
  text(s,'Can we\ndetect CO?',64,177,760,248,86,C.light);
  text(s,'Why molecular absorption has this shape\nand what the channel can reveal',70,457,850,95,29,'#D5CBBB');
  text(s,'60–1000 GHz  |  No receiver noise',70,610,850,40,24,'#D5CBBB');
  text(s,'15 October 2026',70,657,650,27,17,'#C3B9AA');
  pages.push({title:'Can we detect CO?',script:'',notes:'',sources:[]});
  notes(s,'This presentation answers two questions: can we detect CO through the channel, and why is its absorption a smooth curve rather than a set of sharp bands? We begin with the physical mechanism, then connect it to the signal we would have to measure.',
    'The active case is CO in h(f,l) from 60 to 1000 GHz, initially without receiver noise. The decorative cover image is reused from the previous presentation and represents no measured data. Quantitative examples use the saved HITRAN and ITU calculation.', ['local']);
}

// 2. Answer first, with the conditions beside the answer.
{
  const s=page('Can we detect it? The answer depends on what is known');
  text(s,'Yes, in the exact model',64,183,1120,70,54,C.rust);
  text(s,'CO produces a nonzero spectral change. A matched reference\nlets us recover its added absorption.',66,280,1130,108,33);
  text(s,'With an unrestricted unknown atmosphere, the split is not unique.',66,437,1110,90,31);
  text(s,'A practical detection limit still needs measured precision\nand a model of calibration and atmospheric errors.',66,562,1115,85,27,C.muted);
  notes(s,'Yes: in the ideal case, CO changes the channel and a perfectly matched reference lets us recover its added absorption. But if the atmosphere is completely unknown, the same observation can have several explanations. We have not yet established a practical detection limit.',
    'This is conditional observability, not a hardware sensitivity result. It assumes a nonzero response, exact spectral and atmospheric knowledge, exact calibration and adequate numerical precision. The chosen concentration is an input to the example, not a minimum detectable concentration.', ['local']);
}

// 3. Energy levels explain centers; the dipole explains coupling.
{
  const s=page('The electric field can excite CO rotation',{footer:'CO ground vibrational state. Rigid rotor approximation; catalog frequencies include corrections.'});
  text(s,'CO has a permanent electric dipole.\nThe wave couples to its rotational states.',64,178,1130,88,31);
  equation(s,'E_J = h_P B J(J + 1)',64,311,39);
  equation(s,'h_P f_0 = E_{J+1} − E_J',64,401,39);
  text(s,'Allowed absorption: J → J + 1',64,515,470,85,28,C.rust);
  table(s,[['Transition','Center frequency'],['0 → 1','115.271 GHz'],['1 → 2','230.538 GHz'],['2 → 3','345.796 GHz']],642,301,574,290,[.42,.58],25);
  notes(s,'CO has a permanent electric dipole, so the wave’s electric field can drive changes in its rotational state. The energy difference sets the resonance frequency, and the allowed transitions give the sequence of line centers. This explains where the peaks occur, but not yet their width.',
    'The electric dipole interaction is minus the dot product of dipole and field. NIST lists a nonzero CO ground state dipole. Here h_P is Planck constant, distinct from channel h, and B is in Hz. The rigid rotor is an approximation; centrifugal distortion shifts accurate frequencies. This is driven absorption in the weak field regime, not a literal classical molecule rotating at every incident frequency.', ['dipole','rotor','jpl']);
}

// 4. Use the physical width to obtain the corresponding coherence scale.
{
  const s=page('Collisions interrupt the molecular phase',{footer:'Effective coherence times inferred from the first CO line’s air broadened width at 296 K.'});
  text(s,'Nearby molecules perturb the transition\nand destroy phase coherence.',64,179,430,131,29);
  equation(s,'A(t) = exp(−t / T_2)',64,329,34);
  text(s,'Shorter coherence time\nmeans a broader resonance.',64,433,430,105,29,C.rust);
  text(s,'At 1 atm: T₂ ≈ 66 ps',64,565,430,43,25,C.muted);
  chart(s,[{name:'1 atm',x:evidence.coherence.time_ps,y:evidence.coherence.one_atm},{name:'0.1 atm',x:evidence.coherence.time_ps,y:evidence.coherence.point_one_atm,color:C.ink}],520,173,697,458,
    {min:0,max:400,majorUnit:100,title:'Time (ps)'},{min:0,max:1,majorUnit:.25,title:'Normalized coherence',numberFormatCode:'0.00'},true);
  notes(s,'Collisions perturb the molecular environment and interrupt the phase of its response to the field. A response that loses coherence quickly cannot have an infinitely sharp frequency. In the simple Lorentz model, the first CO line at one atmosphere corresponds to an effective coherence time of about 66 picoseconds.',
    'A(t) is an exponential coherence envelope, not a measurement of the instantaneous electric field. The Lorentz HWHM in Hz obeys gamma = 1/(2 pi T2). The plotted T2 values are inferred from the HITRAN air width and linear pressure scaling. T2 is not generally the mean time between collisions or the population lifetime; phase can be lost without population relaxation. No independent time domain experiment is claimed.', ['dephasing','coherence','hitran']);
}

// 5. Thermal motion produces a different broadening mechanism.
{
  const s=page('Thermal motion gives different Doppler shifts',{footer:'First CO line at 115.271 GHz and 296 K. The horizontal axis is in MHz.'});
  equation(s,'Δf ≈ f_0 v / c',64,191,43);
  text(s,'Molecules have different velocities along the beam.',64,296,435,105,29);
  text(s,'Thermal motion produces a Gaussian frequency profile.',64,436,435,110,29,C.rust);
  text(s,'Doppler full width: 0.268 MHz',64,581,450,43,24,C.muted);
  chart(s,[{name:'Doppler profile',x:evidence.doppler.offset_mhz,y:evidence.doppler.density_per_mhz}],521,180,695,420,
    {min:-.6,max:.6,majorUnit:.3,title:'Frequency offset (MHz)',numberFormatCode:'0.0'},
    {min:0,max:4,majorUnit:1,title:'Normalized profile (1/MHz)',numberFormatCode:'0.0'});
  notes(s,'Even at one temperature, molecules have different velocities along the beam, so they see slightly different frequencies through the Doppler effect. The thermal velocity distribution produces a Gaussian profile. For this CO transition at 296 kelvin, its full width is about 0.268 megahertz.',
    'The nonrelativistic shift uses the velocity component along the ray; its sign depends on the chosen direction. The Gaussian standard deviation is f0 sqrt(k_B T/m)/c. The displayed curve is normalized in MHz and uses the main CO isotopologue mass, not an invented width. Random thermal motion is part of the gas physics, even when receiver noise is excluded.', ['broadening','mats']);
}

// 6. Show how the two physical mechanisms combine.
{
  const s=page('At atmospheric pressure, collisions set most of the width',{footer:'Same integrated line area. This comparison isolates broadening, not equal ppm samples.'});
  text(s,'Voigt profile = Lorentz * Gaussian',64,169,1110,58,32,C.rust);
  text(s,'Pressure broadening: 4.815 GHz\nDoppler broadening: 0.000268 GHz',64,284,445,116,27);
  text(s,'For this line at 296 K and 1 atm,\nthe pressure width is about\n18,000 times larger.',64,444,435,135,28);
  chart(s,[{name:'1 atm',x:evidence.profiles.frequency_ghz,y:evidence.profiles.one_atm},{name:'0.1 atm',x:evidence.profiles.frequency_ghz,y:evidence.profiles.point_one_atm,color:C.ink}],521,249,695,382,
    {min:105,max:125,majorUnit:5,title:'Frequency (GHz)'},{min:0,max:1.4,majorUnit:.35,title:'Normalized profile (1/GHz)',numberFormatCode:'0.00'},true);
  notes(s,'The Voigt profile combines Lorentz broadening from collisions with Gaussian broadening from thermal motion. Here, pressure broadening is about eighteen thousand times larger than the Doppler width, so collisions dominate. Increasing pressure spreads the same normalized line area over a wider frequency range.',
    'The asterisk denotes convolution, not pointwise multiplication. These are FWHM comparisons for the first line at 296 K; they do not apply universally to all species, pressures or frequencies. Pressure also shifts the center slightly. More accurate line profiles can be required for precision retrievals, especially outside isolated line cores.', ['hitran','mats']);
}

// 7. Reproduce and explain the exact attached curve without adopting its old claims.
{
  const s=page('Why the curve in your image is smooth',{footer:'Reconstructed historical CH₃CN model curve. It is not a CO spectrum or a measured result.'});
  text(s,'The original calculation adds\nCH₃CN line contributions along\nan atmospheric path.',64,176,438,150,29);
  text(s,'Broad wings overlap. Different\npressures along the path also\nchange their widths.',64,367,438,150,29,C.rust);
  text(s,'A smooth shape alone does not\nprove a separate continuum.',64,553,438,78,25,C.muted);
  chart(s,[{name:'Original modeled extra loss',x:evidence.historical_curve.frequency_ghz,y:evidence.historical_curve.extra_loss_db}],522,174,695,445,
    {min:230,max:240,majorUnit:2,title:'Frequency (GHz)'},{min:0,max:.05,majorUnit:.01,title:'Extra loss (dB)',numberFormatCode:'0.00'});
  notes(s,'The curve in the original image was calculated for acetonitrile, not CO. It adds broadened line contributions through an atmosphere whose pressure and temperature change with height, so the result can look smooth across a small frequency window. That smooth appearance does not by itself prove continuum absorption or identify the gas.',
    'The plotted numbers reproduce gas_db_per_ug_m3 times the saved true_q_ug_m3 from the historical example. They are used solely to explain the supplied image. The generating calculation uses Voigt line cross sections integrated over altitude. No transition by transition decomposition is presented, and no old detection threshold or performance claim is reused. True continuum terms such as water continuum and collision induced absorption are separate model contributions.', ['oldcurve','local','continuum','cia']);
}

// 8. Connect microscopic absorption to the channel with consistent conventions.
{
  const s=page('Three physical steps connect a molecule to the channel');
  text(s,'1  Sum the spectral lines',64,177,430,65,29,C.rust);
  equation(s,'σ(f) = Σ_j S_j V_j(f − f_j)',512,174,36);
  text(s,'Line strength × normalized profile',514,237,700,45,24,C.muted);
  text(s,'2  Accumulate along the path',64,333,430,70,29,C.rust);
  equation(s,'τ_c(f,l) = ∫ n_c(s) σ(f;s) ds',512,325,36);
  text(s,'Integrate density × cross section from 0 to l',514,389,700,45,24,C.muted);
  text(s,'3  Attenuate the field',64,494,430,70,29,C.rust);
  equation(s,'|a_c| = exp(−τ_c / 2)',512,481,40);
  text(s,'Power transmission is exp(−τc).',514,551,700,45,24,C.muted);
  notes(s,'We first add the individual molecular lines to obtain the absorption cross section. We then multiply by molecular density and integrate along the path to obtain optical depth. Beer-Lambert converts optical depth into transmission: the exponent is minus tau for power and minus tau over two for channel amplitude.',
    'The path integral runs from 0 to l. S and V must use the same frequency or wavenumber convention and V must be normalized in that variable. The implementation evaluates HITRAN quantities in wavenumber units. This is a dilute gas, weak probe absorption model. Under fixed local temperature and pressure, tau_c = sigma(f) N_c(l). Background gas loss, geometry and instrument response multiply the chemical field transmission.', ['beer','local','hitran']);
}

// 9. The numerical CO signature follows real line parameters.
{
  const s=page('CO provides a sequence of spectral features',{footer:'Predicted CO loss: 1 ppm over 20 m, 296 K and 1 atm. Main isotopologue. Exact model.'});
  chart(s,[{name:'CO loss',x:evidence.spectrum.frequency_ghz,y:evidence.spectrum.loss_mdb}],64,162,1152,426,
    {min:60,max:1000,majorUnit:100,title:'Frequency (GHz)'},{min:0,max:1.2,majorUnit:.3,title:'Extra CO loss (mdB)',numberFormatCode:'0.0'});
  text(s,'Eight main ground state lines in this band. Heights depend on populations, strengths and widths.',64,611,1152,47,24,C.muted);
  notes(s,'The CO model produces eight main rotational features between 60 and 1000 gigahertz. Their heights differ because transition strengths, level populations and linewidths differ. We should compare the whole spectral pattern with the background, rather than assume that the tallest peak is automatically the best sensing band.',
    'This curve reuses the 1 ppm, 20 m scenario, all 146 retained HITRAN main isotopologue transitions and the saved reference temperature of 296 K. A millidecibel equals 0.001 dB. The graph is not measured data and its higher frequency peaks do not account for receiver performance or large background loss. Minor isotopologues add further features.', ['numbers','jpl','mats']);
}

// 10. Make the observation explicit, rather than only displaying a coefficient.
{
  const s=page('Observe the chemical loss through a channel ratio',{dark:true});
  text(s,'Measure h(f,l). Obtain a matched reference h₀(f,l).',70,165,1130,55,29,C.light);
  equation(s,'|a_c| = |h| / |h_0|',70,268,65,C.light);
  equation(s,'τ_c = −2 ln(|h| / |h_0|)',70,409,53,C.copper);
  text(s,'The reference must preserve geometry, background atmosphere\nand instrument response. It excludes the added CO.',74,561,1125,91,27,C.light);
  notes(s,'We measure the channel at each frequency and path length, then compare it with a matched reference without the added CO. Dividing their magnitudes removes the shared channel factors, and the logarithm gives the extra CO optical depth. If the reference contains ambient CO, we retrieve the enhancement above that reference.',
    'The calibrated magnitude model is |h| = |g h_fs| exp[-(tau_m+tau_c)/2]. A matched reference cancels g, h_fs and tau_m. The result is chemical magnitude transmission, not a complete reconstruction of molecular dispersion or phase. An exactly known physical background can replace a reference measurement only to the accuracy of its assumptions.', ['local','beer']);
}

// 11. Respect the user's h(f,l) model and distinguish length from concentration.
{
  const s=page('Path length changes the gas column that the wave crosses',{footer:'h(f,l): frequency × atmospheric path length. Nested paths through one stationary medium.'});
  chart(s,evidence.paths.series.map((r,i)=>({name:r.center_ghz.toFixed(3)+' GHz',x:evidence.paths.length_m,y:r.loss_udb,color:[C.ink,C.rust,C.olive][i]})),64,162,1152,432,
    {min:0,max:200,majorUnit:40,title:'Atmospheric path length (m)'},{min:0,max:90,majorUnit:30,title:'Extra CO loss (µdB)',numberFormatCode:'0'},true);
  text(s,'CO between 20 and 40 m: loss grows inside the cloud, then stops growing.',64,611,1152,44,25,C.muted);
  notes(s,'Changing the path length tells us how much of the gas cloud the wave has crossed. Here the extra CO loss increases only between 20 and 40 metres, then becomes constant. The integrated signal gives a gas column; concentration also requires the cloud length or additional spatial information.',
    'The saved matrix has different frequencies and actual path lengths, not repeated observations of one fixed link. For nested paths through a stationary medium, changes of optical depth with l reveal newly traversed segments. Receivers all beyond the cloud see the same added column. Geometric and atmospheric loss still grow outside the cloud. This does not constitute tomography.', ['local','numbers']);
}

// 12. Quantify the response without inventing a hardware threshold.
{
  const s=page('The predicted signal is small, even when it is identifiable',{footer:'1 ppm added CO over 20 m. Atmospheric path 200 m, 296 K, 1 atm, water partial pressure 1000 Pa.'});
  text(s,'Relative drop in channel amplitude, before receiver errors',64,164,1152,53,29,C.rust);
  const rows=[0,2,4,7].map(i=>{const r=evidence.examples[i];return [r.center_ghz.toFixed(3)+' GHz',r.relative_amplitude_drop_ppm.toFixed(2)+' ppm',r.background_db_at_200m.toFixed(2)+' dB'];});
  table(s,[['Frequency','Amplitude change','Atmospheric loss'],...rows],64,252,1152,320,[.30,.36,.34],27);
  text(s,'These ppm describe amplitude change, not gas concentration.\nA larger chemical peak can come with much greater background loss.',64,594,1152,65,25,C.muted);
  notes(s,'At 115 gigahertz, the amplitude change in this example is only about 0.33 parts per million. It grows at higher CO lines, but some of those frequencies also suffer much greater atmospheric loss. These numbers tell us the signal scale an instrument would have to resolve; they do not demonstrate that an instrument can resolve it.',
    'Relative amplitude drop is 10^6 times (1 - |h|/|h0|), distinct from the input 1 ppm molecular mole fraction. Atmospheric losses exclude geometric loss. Rows are evaluated at unshifted catalog centers. The 576 GHz row illustrates nearly 100 dB of modeled atmospheric loss across 200 m, so an exact ratio in arithmetic does not prove a measurable received signal. No gain, power, bandwidth or calibration specification is chosen.', ['numbers','itu']);
}

// 13. Add a quantified sensitivity example, not a claimed detection benchmark.
{
  const s=page('A small atmospheric mismatch can dominate the CO loss',{footer:'Chosen sensitivity example at 345.796 GHz. Fixed 296 K and 1 atm. No receiver noise.'});
  text(s,'1 ppm CO across 20 m',64,182,550,54,30,C.muted);
  text(s,'0.0000797 dB',64,258,1100,87,61,C.rust);
  text(s,'Water partial pressure changes from 1000 to 1010 Pa across 200 m',64,382,1148,78,29,C.muted);
  text(s,'0.0187 dB',64,468,1100,87,61);
  text(s,'About 235 × larger. Their spectral shapes may still allow separation.',64,591,1152,63,28,C.rust);
  notes(s,'At the 345.8 gigahertz CO line, a one percent increase in water partial pressure over the full path changes the loss about 235 times more than our CO cloud does. This is a chosen sensitivity example, not a measured humidity error. It shows why we must model the background, while different spectral shapes may still allow the two effects to be separated.',
    'Computed as 0.2 km times [gamma(1010 Pa water) - gamma(1000 Pa water)] using ITU P.676 at fixed total pressure and temperature. The residual is 0.0186961339 dB; the CO contribution is 0.0000796602409 dB. The 1% change refers to water partial pressure, not one percentage point of relative humidity. This is a deterministic perturbation, not a distribution, threshold or proof of nonidentifiability.', ['itu','numbers','local']);
}

// 14. State precisely what information makes the inverse problem soluble.
{
  const s=page('CO must be distinguishable from atmospheric changes');
  equation(s,'r(f,l) = τ_m(f,l) + τ_c(f,l)',64,180,43);
  text(s,'Unknown, unrestricted atmosphere',64,307,530,64,29,C.rust);
  text(s,'Many splits of the same total loss\nproduce the same channel.',64,400,530,124,31);
  text(s,'Constrained atmosphere',684,307,532,64,29,C.rust);
  text(s,'Fit the frequency pattern jointly.\nCO must add a response that the\nallowed background cannot reproduce.',684,400,532,153,29);
  text(s,'We need temperature, pressure, humidity, reference CO and instrument response.',64,604,1152,49,25,C.muted);
  notes(s,'With a completely free atmospheric spectrum, there are many ways to divide the total loss between air and CO. If we constrain the atmosphere to known physical parameters, we can instead compare their effects across frequency. CO is distinguishable only when its response cannot be reproduced by the allowed background changes.',
    'After known geometry and gain are removed, r=-2 ln|h/(g h_fs)|. The transformation tau_m to tau_m+q and tau_c to tau_c-q leaves r unchanged whenever both remain admissible. For a local parameterized model, the CO response must lie outside the span of the atmospheric and instrumental derivative responses. Multiple frequencies help only with appropriate constraints; the sensitivity calculation on slide 13 is not a joint retrieval test.', ['local']);
}

// 15. Close with the answer and an experiment that can resolve what is unknown.
{
  const s=page('What we can conclude now',{dark:true});
  text(s,'CO is observable in the ideal matched case.',70,179,1120,110,46,C.light);
  text(s,'Its smooth spectrum follows from molecular transitions,\nfinite coherence and thermal motion.',74,343,1115,118,35,C.copper);
  text(s,'To claim practical detection, establish the reference accuracy\nand test whether the CO response survives the allowed errors.',74,541,1115,109,29,C.light);
  notes(s,'Our answer is yes under the stated ideal assumptions: the added CO absorption is observable through the reference ratio. Its smooth spectral shape is caused by finite molecular coherence and thermal motion around discrete transitions. The next step is to quantify reference accuracy and test whether CO remains distinguishable before making a practical detection claim.',
    'The next controlled test needs a known gas column, matched reference acquisitions and measured instrumental stability. Modeling should then vary specified atmospheric parameters and examine response independence or retrieval errors. Other chemicals can be assessed individually after CO, then in mixtures. Species without an in band distinguishable response cannot be identified by this absorption measurement alone; catalog absence is not proof of zero physical absorption.', ['local']);
}

// 16. Derive the continuous line shape explicitly for discussion.
{
  const s=page('Appendix: the law behind the smooth line');
  text(s,'Exponentially decaying molecular coherence',64,173,1130,44,27,C.rust);
  equation(s,'C(t) = exp(−t / T_2) exp(i 2π f_0 t)',64,237,39);
  text(s,'Its frequency response has a Lorentz absorption profile',64,342,1130,44,27,C.rust);
  equation(s,'L(Δf) = γ / [π(Δf^{2} + γ^{2})]',64,403,44);
  equation(s,'γ = 1 / (2π T_2)',64,501,38);
  text(s,'Finite coherence gives finite width. Doppler shifts convolve this line with a Gaussian.\nAn infinitely sharp ideal transition would be a delta peak, not a rectangular band.',64,601,1152,63,24,C.muted);
  notes(s,'The continuous profile follows directly from the frequency response of a decaying molecular coherence. An exponential decay produces a Lorentzian, whose width grows as the coherence time becomes shorter. Adding the distribution of Doppler shifts gives the Voigt profile, without introducing receiver noise.',
    'For t >= 0, the real part of the integral of exp(-t/T2) exp[i2 pi Delta f t] is T2/[1+(2 pi Delta f T2)^2]. Normalization gives the displayed L with HWHM gamma. This is an isolated resonance approximation near the line; a full causal molecular response also includes dispersion and may require line mixing and more accurate far wing treatment. Energy conservation is not abandoned: this is the response of moving, interacting molecules, not infinitely long lived isolated levels.', ['coherence','dephasing','mats']);
}

// 17. Put the supporting primary references in the deck.
{
  const s=page('Sources and numerical evidence');
  const refs=[
    ['NIST molecular data','CO dipole and rotational selection rules',sources.rotor],
    ['MIT spectroscopy','Coherence, dephasing and line shape',sources.coherence],
    ['HITRAN and NIST MATS','Line parameters, Doppler and collision profiles',sources.hitran],
    ['JPL CO catalog','Independent line positions',sources.jpl],
    ['ITU P.676, Annex 1','Atmospheric attenuation through 1000 GHz',sources.itu],
    ['Project calculation','Assumptions, spectra and channel matrices',sources.local],
  ];
  refs.forEach(([label,detail,url],i)=>{const y=171+i*72;const b=text(s,label,64,y,430,44,27,C.rust);b.text.get(label).link={uri:url,isExternal:true};text(s,detail,527,y+2,689,50,24);});
  text(s,'Scientific qualifications and additional source links are included in the speaker notes.',64,626,1152,35,23,C.muted);
  notes(s,'The molecular explanation is supported by NIST and MIT spectroscopy references. The numbers use HITRAN line parameters, JPL line positions and an ITU atmospheric model, with the assumptions recorded in the project. They are model predictions, not field measurements.',
    'New sources were checked on October 15, 2026. The numerical source files were acquired for the October 14 restart. New calculations, source hashes and limitations are in results/co_detection_physics_2026_10_15 and scripts/prepare_co_detection_physics.py. The first CO example remains the common source of the channel and gas column. This deck and its speaking script do not claim validation in a measurement instrument.', ['dipole','rotor','coherence','dephasing','hitran','mats','broadening','jpl','itu','beer','continuum','cia','local','numbers','oldcurve']);
}

await fs.mkdir(BUILD,{recursive:true});await fs.mkdir(OUT,{recursive:true});
await fs.writeFile(path.join(BUILD,'slides.json'),JSON.stringify(pages,null,2)+'\n');
await fs.writeFile(path.join(OUT,'co_detection_physics_notes.md'),pages.map((s,i)=>`## ${i+1}. ${s.title}\n\n${s.script}\n\n${s.notes}\n\n${s.sources.map(r=>`- [${r.label}](${r.url})`).join('\n')}`).join('\n\n')+'\n');
const candidate=path.join(BUILD,'candidate.pptx');
await(await PresentationFile.exportPptx(p)).save(candidate);
const finalPath=path.join(OUT,process.env.CO_PHYSICS_DECK_NAME??'co_detection_physics_v2.pptx');
const result=await finalizePresentation({workspaceDir:ROOT,candidatePath:candidate,finalPath,pythonExecutable:PYTHON,
  explicitTotalSlideCount:pages.length,requiredNativeTableOwnerSlides:tableOwners,requiredNativeChartOwnerSlides:chartOwners,
  integrityValidatorPath:path.join(SKILL,'container_tools/inspect_presentation_package_integrity.py'),
  layoutValidatorPath:path.join(SKILL,'container_tools/inspect_presentation_layout_geometry.py'),
  layoutArgs:['--expected-slide-size-emu','12192000,6858000','--validate-heading-fit',...tableOwners.flatMap(n=>['--require-native-table-slide',String(n)])],
  fontPolicy:{basis:'design',families:[FONT]},materializeLiteralChartWorkbooks:true,verifyArtifactToolImport:true,
  receiptPath:path.join(BUILD,path.basename(finalPath)+'.validation.json')});
const deck=await PresentationFile.importPptx(await FileBlob.load(result.finalPath));
const renderDir=path.join(BUILD,'renders');await fs.mkdir(renderDir,{recursive:true});
for(let i=0;i<deck.slides.items.length;i++){
  const blob=await deck.export({slide:deck.slides.items[i],format:'png',scale:1.5});
  await fs.writeFile(path.join(renderDir,`slide-${String(i+1).padStart(2,'0')}.png`),new Uint8Array(await blob.arrayBuffer()));
  console.log(`Rendered slide ${i+1}/${pages.length}`);
}
console.log(JSON.stringify({pptx:result.finalPath,slides:pages.length,nativeCharts:chartOwners,nativeTables:tableOwners}));
