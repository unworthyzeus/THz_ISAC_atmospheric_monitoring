import fs from 'node:fs/promises';
import path from 'node:path';
import {pathToFileURL,fileURLToPath} from 'node:url';
const ROOT=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const TMP=path.join(ROOT,'tmp/supervisor_deck');
const SKILL='C:/Users/guill/.codex/plugins/cache/openai-primary-runtime/presentations/26.905.11957/skills/presentations';
const MODULES=process.env.RUNTIME_NODE_MODULES??'C:/Users/guill/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules';
process.env.RUNTIME_NODE_MODULES=MODULES;
const {Presentation,PresentationFile,FileBlob}=await import(pathToFileURL(path.join(MODULES,'@oai/artifact-tool/dist/artifact_tool.mjs')));
const {finalizePresentation,applyPresentationChartFont}=await import(pathToFileURL(path.join(SKILL,'container_tools/artifact_tool_utils.mjs')));
const PYTHON='C:/Users/guill/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe';
const content=JSON.parse(await fs.readFile(path.join(TMP,'slides.json'),'utf8'));
const equations=JSON.parse(await fs.readFile(path.join(TMP,'equations.json'),'utf8'));
const p=Presentation.create({slideSize:{width:1600,height:900}});
const font='Arial',ink='#153246',muted='#496071',teal='#126B76',red='#9F3343';
const tables=[],charts=[];
let compactFormula=false;
function fitFormula(y,h,size){
 return compactFormula&&y>=184?[184+(y-184)*.82,h*.82,size*.82]:[y,h,size];
}
function text(slide,value,x,y,w,h,size=28,color=ink,bold=false){
 [y,h,size]=fitFormula(y,h,size);
 const shape=slide.shapes.add({geometry:'textbox',position:{left:x,top:y,width:w,height:h},fill:'none',line:{fill:'none',width:0}});
 shape.text=value;
 shape.text.style={typeface:font,fontSize:size,color,bold,autoFit:'none',verticalAlignment:'middle',wrap:true};
 return shape;
}
function table(slide,data,x,y,w,h,widths,size=25){
 [y,h,size]=fitFormula(y,h,size);
 const tb=slide.tables.add({rows:data.length,columns:data[0].length,left:x,top:y,width:w,height:h,columnWidths:widths,values:data});
 tb.borders.assign({fill:'#D9E2E8',width:.6});
 tb.cells.block({row:0,column:0,rowCount:data.length,columnCount:data[0].length}).assign({textStyle:{typeface:font,fontSize:size,color:ink},margins:{left:12,right:12,top:6,bottom:6},anchor:'center'});
 for(let r=0;r<data.length;r++){
  tb.rows[r].height=h/data.length;
  for(let c=0;c<data[0].length;c++){
   tb.getCell(r,c).fill=r===0?ink:(r%2?'#F0F5F7':'#FFFFFF');
   tb.getCell(r,c).text.style={typeface:font,fontSize:size,color:r===0?'#FFFFFF':ink,bold:r===0};
  }
 }
 return tb;
}
async function equation(slide,index,x,y,w,h){
 [y,h]=fitFormula(y,h,0);
 const eq=equations[index];if(!eq)throw new Error('Missing LaTeX equation '+index);
 const ratio=Math.min(w/eq.width,h/eq.height,1.5);
 const ew=eq.width*ratio,eh=eq.height*ratio;
 slide.images.add({blob:new Uint8Array(await fs.readFile(path.join(TMP,'equations',eq.file))),contentType:'image/svg+xml',alt:'LaTeX: '+eq.latex,fit:'contain',position:{left:x,top:y+(h-eh)/2,width:ew,height:eh}});
}
function sideEvidence(slide,s,index){
 if(!s.detail)return;
 const data=[['Parameter / check','Value'],...s.detail];
 table(slide,data,1140,196,388,Math.max(275,75*data.length),[209,179],23);
 tables.push(index);
}
function inlineEvidence(slide,s,y=710){
 if(!s.detail)return;
 const width=1445/s.detail.length;
 s.detail.forEach((r,i)=>{
  text(slide,r[0],76+i*width,y,width-18,32,22,muted);
  text(slide,r[1],76+i*width,y+32,width-18,35,24,ink,true);
 });
}
for(let i=0;i<content.length;i++){
 const s=content[i],slide=p.slides.add(),number=i+1;
 compactFormula=Boolean(s.legend);
 slide.background.fill='#FFFFFF';
 if(s.kind==='cover'){
  slide.background.fill=ink;
  text(slide,'Sub-THz\natmospheric sensing',84,142,1420,260,82,'#FFFFFF',true);
  text(slide,s.body[0],90,478,1400,110,38,'#BCDDE0');
  text(slide,s.body[1],90,718,1370,128,28,'#FFFFFF');
 }else{
  text(slide,s.title,64,40,1472,112,number===26?42:48,ink,true);
  if(s.subtitle)text(slide,s.subtitle,72,142,1456,54,26,muted);
  let start=s.subtitle?216:184;
  if(s.chart){
   const ch=slide.charts.add('line',{position:{left:70,top:218,width:1030,height:402},categories:s.chart.categories,
    series:s.chart.series.map(z=>({name:z.name,values:z.values,line:{fill:z.color,width:4},marker:{symbol:'circle',size:9}})),
    hasLegend:true,legend:{position:'bottom',textStyle:{typeface:font,fontSize:25}},
    yAxis:{min:0,max:100,majorUnit:20,title:s.chart.ytitle,numberFormatCode:'0',textStyle:{fontSize:23,typeface:font},majorGridlines:{fill:'#D9E2E8',width:1}},
    xAxis:{textStyle:{fontSize:25,typeface:font}},chartFill:'#FFFFFF',plotAreaFill:'#FFFFFF',lineOptions:{smooth:false}});
   applyPresentationChartFont(ch,{fontFamily:font});charts.push(number);sideEvidence(slide,s,number);
  }else if(s.table){
   if(s.body.length){
    s.body.forEach((v,j)=>text(slide,v,76,start+j*66,1450,66,26));
    start+=s.body.length*66+16;
   }
   const end=s.formula?480:s.kind==='dense'?672:s.body.length?660:640;
   const widths=s.widths.map(v=>v*1456/s.widths.reduce((a,b)=>a+b,0));
   table(slide,s.table,72,start,1456,end-start,widths,s.kind==='dense'?24:26);tables.push(number);
   if(s.formula){
    await equation(slide,number,82,500,1435,108);
    if(s.explain)text(slide,s.explain,82,616,1435,64,25,muted);
   }
   inlineEvidence(slide,s,s.result?747:s.formula?710:704);
  }else{
   sideEvidence(slide,s,number);
   const end=s.formula?391:652;
   const stride=(end-start)/Math.max(1,s.body.length);
   s.body.forEach((v,j)=>text(slide,v,76,start+j*stride,1014,stride-6,number===30?25:s.body.length>4?26:28));
   if(s.formula){
    await equation(slide,number,76,396,1025,195);
    if(s.explain)text(slide,s.explain,76,599,1025,73,25,muted);
   }
  }
  if(s.result)text(slide,s.result,76,s.legend&&!s.table?721:681,1440,62,29,teal,true);
  if(s.limit)text(slide,s.limit,76,817,1398,52,24,red);
  compactFormula=false;
  if(s.legend){
   text(slide,'Notation and units',76,749,1440,24,20,teal,true);
   s.legend.forEach((column,j)=>{
    const box=text(slide,column,76+j*484,776,474,110,18,muted);
    box.text.style={typeface:font,fontSize:18,color:muted,autoFit:'none',verticalAlignment:'top',wrap:true};
   });
  }
  text(slide,String(number).padStart(2,'0'),1520,866,48,26,18,muted);
 }
 const sourceNotes=s.sources.map(q=>q.startsWith('http')?q:`https://github.com/unworthyzeus/THz_ISAC_atmospheric_monitoring/blob/${q.startsWith('docs/53_')||q.startsWith('results/presentation_source_audit/')?'main':'461a3ba'}/${q.replaceAll(' ','%20')}`).join('\n');
 slide.speakerNotes.textFrame.setText(`${s.notes}\n\n${s.latex?'LaTeX equation source\n'+s.latex:''}\n\n${s.legend?'Notation legend\n'+s.legend.join('\n'):''}\n\nSources\n${sourceNotes}\n\nResearch snapshot 461a3ba. Predictions and simulations remain distinct from measured field performance.`);
}
const candidate=path.join(TMP,'candidate-detailed.pptx');
await (await PresentationFile.exportPptx(p)).save(candidate);
console.log('Exported detailed deck',content.length);
const finalPath=path.join(ROOT,'output/presentations',process.env.DECK_NAME??'sub_thz_isac_supervisor_review_detailed.pptx');
const res=await finalizePresentation({workspaceDir:ROOT,candidatePath:candidate,finalPath,pythonExecutable:PYTHON,
 integrityValidatorPath:path.join(SKILL,'container_tools/inspect_presentation_package_integrity.py'),
 layoutValidatorPath:path.join(SKILL,'container_tools/inspect_presentation_layout_geometry.py'),
 layoutArgs:['--expected-slide-size-emu','15240000,8572500','--validate-bullet-geometry','--validate-heading-fit',...new Set(tables)].flatMap((v,i)=>typeof v==='number'?['--require-native-table-slide',String(v)]:[v]),
 requiredNativeTableOwnerSlides:[...new Set(tables)],requiredNativeChartOwnerSlides:charts,
 materializeLiteralChartWorkbooks:true,fontPolicy:{basis:'design',families:[font]},verifyArtifactToolImport:true,
 receiptPath:path.join(TMP,path.basename(finalPath)+'.validation.json')});
console.log('Finalized',res.finalPath);
const finalDeck=await PresentationFile.importPptx(await FileBlob.load(finalPath));
const renderDir=path.join(TMP,'renders-detailed');await fs.mkdir(renderDir,{recursive:true});
for(let i=0;i<finalDeck.slides.items.length;i++){
 const png=await finalDeck.export({slide:finalDeck.slides.items[i],format:'png',scale:1});
 await fs.writeFile(path.join(renderDir,`slide-${String(i+1).padStart(2,'0')}.png`),new Uint8Array(await png.arrayBuffer()));
}
console.log('Rendered',finalDeck.slides.items.length,'final slides');
