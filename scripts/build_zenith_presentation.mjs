import fs from 'node:fs/promises';
import path from 'node:path';
import {pathToFileURL,fileURLToPath} from 'node:url';

const ROOT=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const TMP=path.join(ROOT,'tmp/zenith_deck');
const SKILL=process.env.PRESENTATION_SKILL_DIR??'C:/Users/guill/.codex/plugins/cache/openai-primary-runtime/presentations/26.905.11957/skills/presentations';
const MODULES=process.env.RUNTIME_NODE_MODULES??'C:/Users/guill/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules';
const PYTHON=process.env.RUNTIME_PYTHON??'C:/Users/guill/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe';
process.env.RUNTIME_NODE_MODULES=MODULES;
const {Presentation,PresentationFile,FileBlob}=await import(pathToFileURL(path.join(MODULES,'@oai/artifact-tool/dist/artifact_tool.mjs')));
const {finalizePresentation,applyPresentationChartFont,resolvePresentationFont}=await import(pathToFileURL(path.join(SKILL,'container_tools/artifact_tool_utils.mjs')));
const content=JSON.parse(await fs.readFile(path.join(TMP,'slides.json'),'utf8'));
const equations=JSON.parse(await fs.readFile(path.join(TMP,'equations.json'),'utf8'));
const font=resolvePresentationFont({fontFamily:'Arial'});
const ink='#153246',muted='#496071',teal='#126B76',red='#9F3343';
const p=Presentation.create({slideSize:{width:1600,height:900}});
const tables=[],charts=[];
// Excel chart workbooks preserve 15 significant digits. Display evidence at 14.
const chartNumber=v=>Number(v.toPrecision(14));

function text(slide,value,x,y,w,h,size=30,color=ink,bold=false){
  const box=slide.shapes.add({geometry:'textbox',position:{left:x,top:y,width:w,height:h},fill:'none',line:{fill:'none',width:0}});
  box.text=value;
  box.text.style={typeface:font,fontSize:size,color,bold,autoFit:'none',verticalAlignment:'middle',wrap:true};
  return box;
}
function table(slide,s,y,h){
  const data=s.table;
  const widths=(s.widths??data[0].map(()=>1/data[0].length)).map(v=>v*1456);
  const size=data[0].length>=5?24:27;
  const tb=slide.tables.add({rows:data.length,columns:data[0].length,left:72,top:y,width:1456,height:h,columnWidths:widths,values:data});
  tb.borders.assign({fill:'#D9E2E8',width:.6});
  tb.cells.block({row:0,column:0,rowCount:data.length,columnCount:data[0].length}).assign({textStyle:{typeface:font,fontSize:size,color:ink},margins:{left:14,right:14,top:8,bottom:8},anchor:'center'});
  for(let r=0;r<data.length;r++){
    tb.rows[r].height=h/data.length;
    for(let c=0;c<data[0].length;c++){
      tb.getCell(r,c).fill=r===0?ink:r%2?'#F0F5F7':'#FFFFFF';
      tb.getCell(r,c).text.style={typeface:font,fontSize:size,color:r===0?'#FFFFFF':ink,bold:r===0};
    }
  }
}
async function equation(slide,index,y,h){
  const eq=equations[index];
  if(!eq)throw new Error('Missing equation '+index);
  const ratio=Math.min(1435/eq.width,h/eq.height,1.6);
  slide.images.add({blob:new Uint8Array(await fs.readFile(path.join(TMP,'equations',eq.file))),contentType:'image/svg+xml',alt:'Equation: '+eq.latex,fit:'contain',position:{left:78,top:y+(h-eq.height*ratio)/2,width:eq.width*ratio,height:eq.height*ratio}});
}
for(let i=0;i<content.length;i++){
  const s=content[i],slide=p.slides.add(),n=i+1;
  slide.background.fill='#FFFFFF';
  if(s.kind==='cover'){
    slide.background.fill=ink;
    text(slide,s.title,86,156,1428,260,82,'#FFFFFF',true);
    text(slide,s.body[0],92,472,1400,80,40,'#BCDDE0');
    text(slide,s.body[1],92,682,1400,90,31,'#FFFFFF');
    text(slide,'5 October 2026',92,820,1200,32,22,'#BCDDE0');
  }else{
    text(slide,s.title,66,40,1468,115,48,ink,true);
    if(s.chart){
      const ch=slide.charts.add('scatter',{
        position:{left:72,top:177,width:1456,height:490},
        series:s.chart.series.map(z=>({name:z.name,xValues:s.chart.x.map(chartNumber),values:z.values.map(chartNumber),line:{fill:z.color,width:s.chart.series.length>1?2:3},marker:{symbol:'none'}})),
        scatterOptions:{style:'line'},hasLegend:s.chart.series.length>1,
        legend:{position:'bottom',textStyle:{typeface:font,fontSize:23}},
        xAxis:{min:s.chart.xmin??Math.floor(Math.min(...s.chart.x)),max:Math.ceil(Math.max(...s.chart.x)),majorUnit:s.chart.xtitle.includes('Frequency')?1:5,title:s.chart.xtitle,numberFormatCode:'0',textStyle:{typeface:font,fontSize:24}},
        yAxis:{min:s.chart.ymin,max:s.chart.ymax,title:s.chart.ytitle,numberFormatCode:s.chart.ymax<1?'0.00':'0.0',textStyle:{typeface:font,fontSize:24},majorGridlines:{fill:'#D9E2E8',width:1}},
        chartFill:'#FFFFFF',plotAreaFill:'#FFFFFF'});
      applyPresentationChartFont(ch,{fontFamily:font});charts.push(n);
    }else if(s.table&&s.latex){
      table(slide,s,173,315);tables.push(n);
      await equation(slide,n,500,115);
      if(s.legend)text(slide,s.legend,78,623,1430,65,23,muted);
    }else if(s.table){
      let y=180;
      if(s.body.length){s.body.forEach((v,j)=>text(slide,v,78,y+j*64,1430,62,28));y+=s.body.length*64+12;}
      table(slide,s,y,Math.min(670-y,s.table.length*79));tables.push(n);
    }else if(s.latex){
      await equation(slide,n,181,182);
      text(slide,s.legend??'',78,373,1435,95,24,muted);
      s.body.forEach((v,j)=>text(slide,v,78,498+j*81,1435,77,31));
    }else{
      const stride=s.body.length===3?143:114;
      s.body.forEach((v,j)=>text(slide,v,78,179+j*stride,1435,stride-10,33));
    }
    if(s.takeaway)text(slide,s.takeaway,78,698,1432,75,29,teal,true);
    if(s.caveat)text(slide,s.caveat,78,787,1430,49,23,red);
    text(slide,s.source,78,850,1375,30,19,muted);
    text(slide,String(n).padStart(2,'0'),1498,850,48,30,20,muted);
  }
  slide.speakerNotes.textFrame.setText(`${s.notes}\n\n${s.latex?'Equation source\n'+s.latex+'\n\n':''}${s.legend?'Notation and units\n'+s.legend+'\n\n':''}${s.caveat?'Conditions\n'+s.caveat+'\n\n':''}Sources\n${s.sources.join('\n')}`);
}
const candidate=path.join(TMP,'candidate.pptx');
await (await PresentationFile.exportPptx(p)).save(candidate);
console.log('Exported',content.length,'slides');
const finalPath=path.join(ROOT,'output/presentations',process.env.DECK_NAME??'zenith_acetonitrile_tutorial_v2.pptx');
const result=await finalizePresentation({workspaceDir:ROOT,candidatePath:candidate,finalPath,pythonExecutable:PYTHON,
  integrityValidatorPath:path.join(SKILL,'container_tools/inspect_presentation_package_integrity.py'),
  layoutValidatorPath:path.join(SKILL,'container_tools/inspect_presentation_layout_geometry.py'),
  layoutArgs:['--expected-slide-size-emu','15240000,8572500','--validate-heading-fit',...tables.flatMap(n=>['--require-native-table-slide',String(n)])],
  requiredNativeTableOwnerSlides:tables,requiredNativeChartOwnerSlides:charts,
  materializeLiteralChartWorkbooks:true,fontPolicy:{basis:'design',families:[font]},verifyArtifactToolImport:true,
  receiptPath:path.join(TMP,path.basename(finalPath)+'.validation.json')});
console.log('Finalized',result.finalPath);
const finalDeck=await PresentationFile.importPptx(await FileBlob.load(finalPath));
const renderDir=path.join(TMP,'renders');await fs.mkdir(renderDir,{recursive:true});
for(let i=0;i<finalDeck.slides.items.length;i++){
  const png=await finalDeck.export({slide:finalDeck.slides.items[i],format:'png',scale:1});
  await fs.writeFile(path.join(renderDir,`slide-${String(i+1).padStart(2,'0')}.png`),new Uint8Array(await png.arrayBuffer()));
}
console.log('Rendered',finalDeck.slides.items.length,'final slides');
