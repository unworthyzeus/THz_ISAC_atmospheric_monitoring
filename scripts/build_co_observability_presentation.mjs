import fs from 'node:fs/promises';
import path from 'node:path';
import {pathToFileURL, fileURLToPath} from 'node:url';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const BUILD = path.join(ROOT, 'tmp/co_observability_deck');
const OUT = path.join(ROOT, 'output/presentations');
const SKILL = 'C:/Users/guill/.codex/plugins/cache/openai-primary-runtime/presentations/26.1013.11914/skills/presentations';
const MODULES = 'C:/Users/guill/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules';
const PYTHON = 'C:/Users/guill/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe';
process.env.RUNTIME_NODE_MODULES = MODULES;
const {Presentation, PresentationFile, FileBlob} = await import(pathToFileURL(path.join(MODULES, '@oai/artifact-tool/dist/artifact_tool.mjs')));
const {finalizePresentation, applyPresentationChartFont, resolvePresentationFont} = await import(pathToFileURL(path.join(SKILL, 'container_tools/artifact_tool_utils.mjs')));
const evidence = JSON.parse(await fs.readFile(path.join(BUILD, 'evidence.json'), 'utf8'));
const FONT = resolvePresentationFont({fontFamily:'Georgia', availableFonts:['Georgia']});
const C = {paper:'#F4F0E8', ink:'#242421', rust:'#B4472B', muted:'#6E6A61', rule:'#D5CEC1', pale:'#E9E1D5', light:'#F5F1E9', olive:'#69725D'};
const p = Presentation.create({slideSize:{width:1280,height:720}});
const pages = [], chartOwners = [], tableOwners = [];
const sources = {
  hitran:'https://hitran.org/docs/definitions-and-units/',
  beer:'https://hitran.org/docs/cross-sections-definitions/',
  hapi:'https://hitran.org/hapi/',
  jpl:'https://spec.jpl.nasa.gov/ftp/pub/catalog/c028001.cat',
  itu:'https://www.itu.int/dms_pubrec/itu-r/rec/p/R-REC-P.676-13-202208-I!!PDF-E.pdf',
  nist:'https://physics.nist.gov/Pubs/AtSpec/node20.html',
  rotor:'https://www.nist.gov/pml/diatomic-spectral-database/diatomic-spectral-database-1s-ground-state-molecules',
  continuum:'https://hitran.org/mtckd/',
  cia:'https://hitran.org/cia/',
  local:'https://github.com/unworthyzeus/THz_ISAC_atmospheric_monitoring/blob/50393b2/docs/59_restart_observability_2026_10_14.md',
  numbers:'https://github.com/unworthyzeus/THz_ISAC_atmospheric_monitoring/blob/50393b2/results/restart_2026_10_14/co_line_examples.csv',
};

function text(s, value, x, y, w, h, size=26, color=C.ink, bold=false, more={}) {
  const box=s.shapes.add({geometry:'textbox',name: typeof value==='string'?value.slice(0,60):'Text',position:{left:x,top:y,width:w,height:h},fill:'none',line:{fill:'none',width:0}});
  box.text=value;
  box.text.style={typeface:FONT,fontSize:size,color,bold,wrap:'square',autoFit:'none',insets:0,verticalAlignment:'top',...more};
  return box;
}
function width(value,size) {
  return [...value].reduce((sum,char)=>sum+(evidence.font_widths_at_100px[char]??58),0)*size/100;
}
// Native editable text pieces keep real subscripts without equation screenshots.
function equation(s, value, x, y, size=44, color=C.ink) {
  const parts = value.split(/(_\{[^}]+\}|_[A-Za-z0-9])/g).filter(Boolean);
  let cursor=x;
  for(const part of parts) {
    const sub=part.startsWith('_');
    const literal=sub?part.slice(1).replace(/[{}]/g,''):part;
    const pt=sub?size*.61:size;
    const w=width(literal,pt)+2;
    text(s,literal,cursor,y+(sub?size*.48:0),w,size*1.55,pt,color,false,{wrap:'none'});
    cursor+=w;
  }
  return cursor-x;
}
function page(title,{dark=false,footer=''}={}) {
  const s=p.slides.add();
  s.background.fill=dark?C.ink:C.paper;
  const number=p.slides.items.length;
  text(s,title,64,42,1152,105,46,dark?C.light:C.ink);
  if(footer)text(s,footer,64,668,1090,32,16,dark?'#C6BFB3':C.muted);
  text(s,String(number).padStart(2,'0'),1170,668,48,28,17,dark?'#C6BFB3':C.muted,false,{alignment:'right'});
  pages.push({title,notes:'',sources:[]});
  return s;
}
function notes(s, body, keys=[]) {
  const record=pages[p.slides.items.indexOf(s)];
  record.notes=body;
  record.sources=keys.map(key=>({label:key,url:sources[key]}));
  s.speakerNotes.textFrame.setText(body+'\n\nSources\n'+record.sources.map(ref=>ref.label+': '+ref.url).join('\n'));
}
function table(s, values, x,y,w,h, widths, size=24, header=true) {
  const tb=s.tables.add({rows:values.length,columns:values[0].length,left:x,top:y,width:w,height:h,columnWidths:widths.map(v=>v*w),values});
  tb.borders.assign({fill:C.rule,width:.7});
  tb.cells.block({row:0,column:0,rowCount:values.length,columnCount:values[0].length}).assign({textStyle:{typeface:FONT,fontSize:size,color:C.ink},margins:{left:16,right:16,top:12,bottom:10},anchor:'center'});
  for(let r=0;r<values.length;r++){
    tb.rows[r].height=h/values.length;
    for(let col=0;col<values[0].length;col++){
      tb.getCell(r,col).fill=header&&r===0?C.ink:C.paper;
      tb.getCell(r,col).text.style={typeface:FONT,fontSize:size,color:header&&r===0?C.light:C.ink,bold:header&&r===0};
    }
  }
  tableOwners.push(p.slides.items.indexOf(s)+1);
  return tb;
}
function chart(s, series, x,y,w,h, xAxis, yAxis, legend=false) {
  const config={position:{left:x,top:y,width:w,height:h},series:series.map((r,i)=>({name:r.name,xValues:r.x.map(v=>Number(v.toPrecision(14))),values:r.y.map(v=>Number(v.toPrecision(14))),line:{fill:r.color??C.rust,width:r.lineWidth??3},marker:{symbol:'none'}})),
    scatterOptions:{style:'line'},hasLegend:legend,legend:{position:'bottom',overlay:false,textStyle:{fontSize:19,fill:C.ink}},
    xAxis:{line:{fill:C.muted,width:1},textStyle:{fontSize:20,fill:C.ink},numberFormatCode:'0',...xAxis},
    yAxis:{line:{fill:C.muted,width:1},textStyle:{fontSize:20,fill:C.ink},majorGridlines:{fill:C.rule,width:.7},...yAxis},
    chartFill:C.paper,plotAreaFill:C.paper,chartLine:{fill:'none',width:0},plotAreaLine:{fill:'none',width:0}};
  const ch=s.charts.add('scatter',config);
  applyPresentationChartFont(ch,{fontFamily:FONT});
  chartOwners.push(p.slides.items.indexOf(s)+1);
  return ch;
}

// 1. The cover is deliberately quiet and uses only one abstract image.
{
  const s=p.slides.add();s.background.fill=C.ink;
  s.images.add({blob:new Uint8Array(await fs.readFile(path.join(OUT,'co_observability_assets/spectral_cover.png'))),contentType:'image/png',alt:'Abstract light bands used as a decorative cover image',fit:'cover',position:{left:0,top:0,width:1280,height:720}});
  text(s,'Observing CO\nin the channel',64,190,780,230,76,C.light);
  text(s,'Absorption, atmospheric separation\nand the role of path length',69,442,720,92,29,'#D5CBBB');
  text(s,'60–1000 GHz',69,605,460,42,25,'#D5CBBB');
  text(s,'14 October 2026',69,653,460,30,18,'#C3B9AA');
  pages.push({title:'Observing CO in the channel',notes:'',sources:[]});
  notes(s,'The study restarts with a single gas, CO, over 60 to 1000 GHz. We study the frequency and path length dependence of the channel, initially with no receiver noise. The immediate objective is to identify what information allows us to attribute part of the measured loss to CO. The cover uses a decorative abstract illustration of light bands. It carries no measured spectral information.', ['local']);
}

// 2. The matrix gives the measurement an explicit meaning.
{
  const s=page('The channel is a frequency × length matrix');
  equation(s,'H_{ij} = h(f_i, l_j)',64,180,43);
  text(s,'f samples frequency\nl samples atmospheric path length',64,283,430,110,27);
  text(s,'Each new column needs a different path length.',64,449,420,115,30,C.rust);
  table(s,[['','l₁','l₂','l₃'],['f₁','h₁₁','h₁₂','h₁₃'],['f₂','h₂₁','h₂₂','h₂₃'],['f₃','h₃₁','h₃₂','h₃₃']],554,184,650,300,[.16,.28,.28,.28],30);
  text(s,'Current case: one gas, no receiver noise\nLater: other gases, mixtures, then angle',554,520,650,104,26);
  notes(s,'H has frequency along its rows and atmospheric path length along its columns. The table shows indices, not invented channel values. Repeating observations at the same geometry does not create independent path length samples. Nested paths through the same stationary medium might come from known receiver positions or a controlled variable path setup. The total transmitter to receiver distance d may differ from the atmospheric distance l. They coincide in the homogeneous terrestrial numerical example. A future angular coordinate would give h(f,l,theta). We begin by studying magnitudes because the immediate question concerns absorption.', ['local']);
}

// 3. The amplitude convention prevents a factor of two error.
{
  const s=page('Geometry and absorption contribute to one channel');
  equation(s,'|h| = |h_{fs}| exp(−τ_m / 2) exp(−τ_c / 2)',64,185,43);
  table(s,[['Term','Meaning'],['hFS','Geometric amplitude gain, dependent on frequency and distance'],['τm','Optical depth of the background atmosphere'],['τc','Additional optical depth due to the chemical cloud']],64,310,1152,272,[.19,.81],26);
  text(s,'Amplitude transmission: exp(−τ / 2)       Power transmission: exp(−τ)',64,609,1152,46,25,C.rust);
  notes(s,'We assume the instrument response is known, corrected or matched between acquisitions. With that convention, the magnitude is the product of geometric amplitude gain and the two exponential absorption factors. The omitted full complex channel also contains propagation phase and molecular dispersion. Each tau is a dimensionless integral of a power absorption coefficient alpha, in 1/m, over path length. Beer–Lambert gives power transmission exp(-tau). Since power is proportional to squared magnitude, the channel amplitude uses exp(-tau/2). For unit gain far field antennas, |h_fs|=c0/(4 pi f d). A positive free space path loss is the reciprocal power gain, not an amplitude multiplier. The table uses compact plain text names for the subscripts.', ['beer','local']);
}

// 4. Central observable.
{
  const s=page('A matched reference isolates the chemical loss',{dark:true});
  text(s,'h₀: the same channel without the added CO',74,151,1100,42,25,'#C6BFB3');
  equation(s,'|a_c| = |h| / |h_0|',70,205,66,C.light);
  equation(s,'τ_c = −2 ln(|h| / |h_0|)',70,352,55,'#D89474');
  text(s,'The reference preserves geometry, atmosphere\nand instrument response.',74,515,1100,95,30,C.light);
  notes(s,'Define h0 with the same geometry, instrument response and background atmospheric optical depth, but without the additional target gas column. Dividing h by h0 cancels the shared multiplicative factors. The magnitude ratio is exp(-tau_c/2), so -2 times its natural logarithm gives the chemical optical depth. In decibels, extra loss is -20 log10(|h|/|h0|)=(10/ln10) tau_c. If h0 contains ambient CO, the retrieved quantity is the CO enhancement relative to that reference. An absolute column requires knowledge of the reference CO. A model can supply h0 only to the accuracy of its atmospheric and instrument assumptions.', ['beer','local']);
}

// 5. A constructive ambiguity is more useful than a generic warning.
{
  const s=page('An unknown atmosphere leaves the split ambiguous');
  equation(s,'r = −2 ln(|h| / |h_{fs}|) = τ_m + τ_c',64,179,42);
  text(s,'Two decompositions',64,296,1100,44,26,C.muted);
  equation(s,'τ_m + τ_c',92,365,48);
  equation(s,'(τ_m + q) + (τ_c − q)',92,449,48);
  text(s,'Both produce the same channel.',718,367,490,100,35,C.rust);
  text(s,'Separation needs a matched reference or distinguishable model responses.',64,579,1140,70,28);
  notes(s,'After known geometry and calibration are removed, the observation gives the sum of optical depths. Any admissible q transferred from one component to the other leaves the measurement unchanged. The altered components must remain within their allowed physical models and nonnegativity constraints. This is a mathematical construction, not a claim that any chosen q belongs to a realistic humidity model. It proves nonuniqueness when the background is unrestricted. More frequencies and zero receiver noise do not eliminate an unrestricted functional ambiguity. A parameterized atmosphere can permit separation when changes in CO generate a response outside the span of atmospheric parameter changes.', ['local']);
}

// 6. Pressure broadening is plotted from the actual first CO transition.
{
  const s=page('A discrete transition has a continuous profile',{footer:'CO at 296 K. Equal integrated profile area. Source: HITRAN.'});
  equation(s,'f_0 = ΔE / h_P',64,178,43);
  text(s,'Collisions shorten molecular coherence.\n\nThermal motion introduces Doppler shifts.',64,283,410,196,27);
  text(s,'At 1 atm, this line has a Lorentz full width of about 4.82 GHz.',64,510,410,110,27,C.rust);
  chart(s,[{name:'1 atm',x:evidence.profiles.x,y:evidence.profiles.one_atm,color:C.rust},{name:'0.1 atm',x:evidence.profiles.x,y:evidence.profiles.point_one_atm,color:C.ink}],500,174,715,448,
    {min:105,max:125,majorUnit:5,title:'Frequency (GHz)'},
    {min:0,max:1.4,majorUnit:.35,title:'Normalized profile (1/GHz)',numberFormatCode:'0.00'},true);
  notes(s,'The unshifted center of this CO transition is about 115.271 GHz. An ideal infinitely sharp resonance would be a delta peak at its center, not a rectangular absorption band. A finite coherence time yields a Lorentzian response. Thermal velocities give a Gaussian Doppler distribution. A Voigt profile combines those contributions. Natural linewidth also exists but is not the main atmospheric width here. These mechanisms are physical and remain when receiver noise is set to zero. The plot compares area normalized profiles at 1 and 0.1 atm using the same HITRAN transition at 296 K. It isolates line broadening, rather than comparing equal ppm samples. At 1 atm the tabulated air half width is 2.40733 GHz, giving a Lorentz full width of 4.81467 GHz. Pressure shifts also move the center slightly. More sophisticated profiles and line mixing may matter for precision work. Smooth line wings and overlap must not be confused with separate continuum absorption.', ['hitran','nist','continuum']);
}

// 7. All observations remain tied to the new physical example.
{
  const s=page('CO has eight main rotational lines in this band',{footer:'Predicted extra loss for 1 ppm over 20 m at 296 K and 1 atm. Main isotopologue.'});
  chart(s,[{name:'Extra CO loss',x:evidence.spectrum.x,y:evidence.spectrum.y_mdb,color:C.rust}],64,160,1152,425,
    {min:60,max:1000,majorUnit:100,title:'Frequency (GHz)'},
    {min:0,max:1.2,majorUnit:.3,title:'Extra CO loss (mdB)',numberFormatCode:'0.0'});
  text(s,'115.271   230.538   345.796   461.041   576.268   691.473   806.652   921.800 GHz',64,607,1152,42,22,C.muted);
  notes(s,'The eight labels are the main isotopologue ground vibrational state rotational line centers in the 60 to 1000 GHz interval. JPL independently supports their positions. Other isotopologues and excited states add features. The actual spectrum includes all 146 retained HITRAN main isotopologue transitions with centers from 0 to 3000 GHz. The chart displays the stored physical spectrum, with every second sample plus the exact line center samples retained. A millidecibel is 0.001 dB. Relative peak heights follow the line strengths and widths for this temperature and pressure. They do not identify the most useful instrument band because background atmospheric loss and measurement precision also matter. This calculation uses a chosen gas column, exact background and calibration, and no receiver noise. It gives no practical detection threshold.', ['jpl','hitran','numbers']);
}

// 8. Length scans distinguish traversed cloud length from total distance.
{
  const s=page('Chemical loss grows only while crossing the cloud',{footer:'Nested paths through one stationary medium. Excess CO lies between 20 and 40 m.'});
  chart(s,evidence.paths.series.map((series,i)=>({name:series.frequency_ghz.toFixed(3)+' GHz',x:evidence.paths.x,y:series.loss_micro_db,color:[C.ink,C.rust,C.olive][i]})),64,160,1152,433,
    {min:0,max:200,majorUnit:40,title:'Atmospheric path length (m)'},
    {min:0,max:90,majorUnit:30,title:'Extra CO loss (µdB)',numberFormatCode:'0'},true);
  text(s,'Before 20 m: no added CO       20–40 m: column grows       After 40 m: same CO column',64,612,1152,42,22,C.muted);
  notes(s,'For constant local temperature and pressure, tau_c(f,l)=sigma_c(f) times the accumulated column N_c(l). Here N_c is zero before 20 m, increases inside the cloud, and stops changing beyond 40 m. More distance after the cloud still increases geometric and background atmospheric loss. Receivers all beyond the cloud see the same chemical column in this ideal setup. A microdecibel is 0.000001 dB. For truly nested paths in a stationary medium, differentiating optical depth with respect to l gives the local absorption coefficient. That derivative does not apply to arbitrary different paths or a changing cloud. Concentration and cloud thickness are not individually determined from a single integrated column.', ['local','numbers']);
}

// 9. Concrete scale, with assumptions beside the predictions.
{
  const s=page('A chosen CO column gives a very small channel change',{footer:'Conditional simulation. Exact atmosphere and calibration. No receiver noise.'});
  text(s,'1 ppm of excess CO\nacross a 20 m cloud',64,166,450,105,36,C.rust);
  text(s,'296 K and 1 atm\nWater partial pressure: 1000 Pa\nTotal path in this comparison: 200 m',64,310,450,149,25);
  table(s,[['Frequency','Extra loss','|h| / |h₀|'],['115.271 GHz','2.89 µdB','0.9999996673'],['230.538 GHz','23.35 µdB','0.9999973120'],['345.796 GHz','79.66 µdB','0.9999908288']],550,169,665,326,[.30,.25,.45],23);
  text(s,'The matched reference recovers the input column under the same model.',64,550,1148,82,33);
  notes(s,'All displayed values come from the saved CO example. The scenario values are chosen inputs, not field measurements. Temperature is 296 K, pressure is 101325 Pa and water partial pressure is 1000 Pa. The chemical cloud contains 1 ppm excess CO from 20 to 40 m along a horizontal path. At the unshifted 115.271 GHz center, extra loss is 2.889726e-6 dB and the amplitude ratio is 0.999999667308. At 230.538 GHz the corresponding loss is 2.334813e-5 dB. At 345.796 GHz it is 7.966024e-5 dB. The known reference permits numerical recovery of the chosen column. Generation and inversion use the same forward assumptions, so this is an algebraic consistency result rather than an independent physical validation. The main isotopologue, air broadened Voigt approximation omits minor isotopologues, explicit water perturber effects and non-Voigt corrections. No practical sensitivity or detection limit follows from these numbers.', ['numbers','hitran','itu','local']);
}

// 10. A clear inventory of missing knowledge.
{
  const s=page('The separation requires more than an absorption law');
  table(s,[['Information','Role in the separation'],['Geometry and instrument response','Separate path loss and instrument gain'],['Temperature, pressure and humidity','Set background loss and molecular line shapes'],['Reference CO and gas spectra','Separate target enhancement from other gases'],['Cloud length or spatial model','Convert molecular column to concentration']],64,169,1152,390,[.39,.61],25);
  text(s,'A standard atmosphere supplies assumed conditions. A matched reference must reproduce the conditions of the sample.',64,590,1150,66,26,C.rust);
  notes(s,'Knowledge of a well studied atmospheric law is not the same as knowledge of the atmosphere at acquisition time. The background needs temperature, pressure and humidity along the relevant ray. P.676 Annex 1 covers oxygen and water based gas attenuation up to 1000 GHz, with specified continuum terms, while omitting some minor species. Avoid double counting oxygen, water and continuum absorption by adding overlapping models. Geometry and instrument response also affect measured h. If the target already exists in the reference, the observable is a change from its reference column. To turn a column into a uniform concentration, cloud length must be known. These issues remain even if additive receiver noise is zero.', ['itu','hitran','local']);
}

// 11. The wider chemical survey needs an explicit criterion.
{
  const s=page('Chemical identifiability and practical detectability');
  text(s,'Identifiability',64,184,510,55,38,C.rust);
  text(s,'Can the gas produce a spectral response that the allowed background and other gases cannot reproduce?',64,271,510,182,29);
  text(s,'Practical detectability',684,184,530,55,38,C.rust);
  text(s,'Is the resulting channel change measurable at the chosen column, path length and instrument precision?',684,271,530,182,29);
  text(s,'The noiseless study addresses the first question. A useful concentration limit requires an error model.',64,532,1152,106,32);
  notes(s,'The overall objective is a defensible classification of which chemicals the system can distinguish in the specified band. For a local parameterized model, delta r = J_m delta theta_m + s_c delta N_c. CO is locally distinguishable when its response s_c lies outside the span of uncertain atmospheric responses J_m. With multiple gases, their columns must remain independent after accounting for nuisance responses. This local rank condition does not establish global uniqueness for a nonlinear model. Under exact arithmetic, exact forward knowledge and no receiver noise, arbitrarily small nonzero distinct responses are observable in principle. A finite operational concentration limit needs measurement precision, calibration, environmental uncertainty and a decision criterion. Nonzero extrapolated line wings alone do not certify practical detectability, and absence of an entry in one catalog does not prove a species has no response.', ['local']);
}

// 12. A concrete decision for the supervisor conversation.
{
  const s=page('The next experiment needs a defined reference',{dark:true});
  text(s,'How will we obtain h₀?',68,188,1140,93,65,C.light);
  text(s,'A matched measurement\nor a constrained atmospheric model',72,319,1090,108,39,'#D89474');
  text(s,'Then vary the uncertain atmospheric quantities\nand test whether CO remains distinguishable.',72,505,1090,105,30,C.light);
  notes(s,'The immediate meeting decision is how the experiment obtains the background reference. A controlled reference acquisition can isolate an enhancement if the atmosphere, geometry and hardware remain matched. A modeled reference needs explicitly constrained atmospheric and calibration parameters. The next CO calculation should vary those uncertain quantities and examine whether the CO response remains distinct. After this single gas case, apply the same reasoning to other named gases individually, then mixtures. Angular dependence follows once path geometry is settled. This presentation does not carry forward the old proposal tasks or detector performance claims.', ['local']);
}

// 13. Appendix for the three physical laws and model layers.
{
  const s=page('Appendix: the molecular model');
  text(s,'Transition positions',64,169,386,47,28,C.rust);
  equation(s,'E_J = h_P B J(J + 1)',480,163,38);
  text(s,'CO rigid rotor. J increases by one in absorption.',480,225,728,50,23,C.muted);
  text(s,'Cross section',64,313,386,47,28,C.rust);
  equation(s,'σ_c(f) = Σ_j S_j V_j(f − f_j)',480,304,37);
  text(s,'Voigt combines Lorentz and Doppler broadening.',480,369,728,63,23,C.muted);
  text(s,'Propagation',64,465,386,47,28,C.rust);
  equation(s,'τ_c = ∫ n_c(s) σ_c(f; s) ds',480,452,37);
  equation(s,'|a_c| = exp(−τ_c / 2)',480,530,37);
  text(s,'For uniform conditions: τc(f, l) = σc(f) Nc(l), where Nc is the molecular column.',64,622,1152,40,24);
  notes(s,'The rigid rotor gives an instructive approximation for CO rotational levels. B is in Hz and h_P is Planck constant. Allowed absorption changes J to J+1, so frequency is near 2B(J+1), with centrifugal distortion corrections required for accurate line positions. The cross section is the sum of integrated strengths times normalized profiles. In this formula S and V use a common frequency convention. HITRAN itself uses wavenumber, with f in GHz = 29.9792458 times wavenumber in cm^-1. A change of integration variable requires consistent strength and profile normalization. Number density times cross section gives a local absorption coefficient. Its integral gives optical depth. Power follows exp(-tau); amplitude follows exp(-tau/2). For uniform temperature and pressure, the cross section can be taken outside the path integral and the unknown becomes the molecular column. The first example fixes temperature at HITRAN reference 296 K. Other temperatures require line intensity population and partition function corrections.', ['rotor','hitran','beer']);
}

// 14. References remain clickable native text, with detailed citations in notes.
{
  const s=page('Sources and reproducible calculation');
  const refs=[
    ['HITRAN','Line positions, strengths and broadening',sources.hitran],
    ['JPL CO catalog','Independent rotational line positions',sources.jpl],
    ['ITU P.676-13, Annex 1','Atmospheric gas attenuation to 1000 GHz',sources.itu],
    ['NIST spectroscopy','Line broadening and molecular energy levels',sources.nist],
    ['Project calculation','CO spectra, channel matrices and assumptions',sources.local],
  ];
  refs.forEach(([label,detail,url],i)=>{
    const y=170+i*83;
    const labelBox=text(s,label,64,y,370,45,29,C.rust);
    labelBox.text.get(label).link={uri:url,isExternal:true};
    text(s,detail,464,y+3,740,49,25);
  });
  text(s,'Complete derivations and source links accompany each slide in the speaker notes.',64,615,1152,45,24,C.muted);
  notes(s,'The linked project note records the complete derivation, scientific assumptions and executable CO example. The numerical sources were downloaded and checked on October 14, 2026. The simulation uses real spectroscopic parameters with a chosen environmental scenario. References in individual notes identify which sources support each slide. Additional reading covers water vapor continuum, collision induced absorption and the rigid rotor correction terms.', ['hitran','hapi','jpl','itu','nist','rotor','continuum','cia','local','numbers']);
}

await fs.mkdir(BUILD,{recursive:true});
await fs.mkdir(OUT,{recursive:true});
await fs.writeFile(path.join(BUILD,'slides.json'),JSON.stringify(pages,null,2)+'\n');
await fs.writeFile(path.join(BUILD,'font-policy.json'),JSON.stringify({basis:'design',families:[FONT]},null,2)+'\n');
await fs.writeFile(path.join(OUT,'co_observability_presenter_notes.md'),pages.map((s,i)=>`## ${i+1}. ${s.title}\n\n${s.notes}\n\n${s.sources.map(ref=>`- [${ref.label}](${ref.url})`).join('\n')}`).join('\n\n')+'\n');

const candidate=path.join(BUILD,'candidate.pptx');
await (await PresentationFile.exportPptx(p)).save(candidate);
const finalPath=path.join(OUT,process.env.CO_DECK_NAME??'co_observability_editorial_v2.pptx');
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
