import fs from 'node:fs/promises';
import path from 'node:path';
import {pathToFileURL,fileURLToPath} from 'node:url';

const ROOT=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const TMP=path.join(ROOT,'tmp/zenith_compact_deck');
const SKILL=process.env.PRESENTATION_SKILL_DIR??'C:/Users/guill/.codex/plugins/cache/openai-primary-runtime/presentations/26.1007.11041/skills/presentations';
const MODULES=process.env.RUNTIME_NODE_MODULES??'C:/Users/guill/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules';
const PYTHON=process.env.RUNTIME_PYTHON??'C:/Users/guill/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe';
process.env.RUNTIME_NODE_MODULES=MODULES;
const {Presentation,PresentationFile,FileBlob}=await import(pathToFileURL(path.join(MODULES,'@oai/artifact-tool/dist/artifact_tool.mjs')));
const {finalizePresentation,applyPresentationChartFont,resolvePresentationFont}=await import(pathToFileURL(path.join(SKILL,'container_tools/artifact_tool_utils.mjs')));
const content=JSON.parse(await fs.readFile(path.join(TMP,'slides.json'),'utf8'));
const equations=JSON.parse(await fs.readFile(path.join(TMP,'equations.json'),'utf8'));
const font=resolvePresentationFont({fontFamily:'Arial'});
const colors={ink:'#153246',muted:'#496071',teal:'#126B76',red:'#9F3343'};
const p=Presentation.create({slideSize:{width:1600,height:900}});
const tables=[],charts=[];
function text(slide,value,x,y,w,h,size=24,color='ink',bold=false){
  const box=slide.shapes.add({geometry:'textbox',position:{left:x,top:y,width:w,height:h},fill:'none',line:{fill:'none',width:0}});
  box.text=value;
  box.text.style={typeface:font,fontSize:size,color:colors[color]??color,bold,autoFit:'none',verticalAlignment:'top',wrap:true};
}
function table(slide,b){
  const d=b.values;
  const tb=slide.tables.add({rows:d.length,columns:d[0].length,left:b.x,top:b.y,width:b.w,height:b.h,columnWidths:b.widths.map(v=>v*b.w),values:d});
  tb.borders.assign({fill:'#D9E2E8',width:.6});
  tb.cells.block({row:0,column:0,rowCount:d.length,columnCount:d[0].length}).assign({textStyle:{typeface:font,fontSize:b.size,color:colors.ink},margins:{left:11,right:11,top:6,bottom:6},anchor:'center'});
  for(let r=0;r<d.length;r++){
    tb.rows[r].height=b.row_heights?.[r]??b.h/d.length;
    for(let c=0;c<d[0].length;c++){
      tb.getCell(r,c).fill=r===0?colors.ink:r%2?'#F0F5F7':'#FFFFFF';
      tb.getCell(r,c).text.style={typeface:font,fontSize:b.size,color:r===0?'#FFFFFF':colors.ink,bold:r===0};
    }
  }
}
for(let i=0;i<content.length;i++){
  const s=content[i],slide=p.slides.add(),n=i+1;
  slide.background.fill='#FFFFFF';
  text(slide,s.title,60,30,1480,65,44,'ink',true);
  text(slide,s.lead,66,106,1468,60,25,'muted');
  for(const b of s.blocks){
    if(b.type==='text')text(slide,b.text,b.x,b.y,b.w,b.h,b.size,b.color,b.bold);
    else if(b.type==='table'){table(slide,b);tables.push(n);}
    else if(b.type==='math'){
      const eq=equations[b.id];
      const ratio=Math.min(b.w/eq.width,b.h/eq.height,1.5);
      slide.images.add({blob:new Uint8Array(await fs.readFile(path.join(TMP,'equations',eq.file))),contentType:'image/svg+xml',alt:'Equation: '+eq.latex,fit:'contain',position:{left:b.x,top:b.y+(b.h-eq.height*ratio)/2,width:eq.width*ratio,height:eq.height*ratio}});
    }else if(b.type==='chart'){
      const round=v=>Number(v.toPrecision(14));
      const ch=slide.charts.add('scatter',{position:{left:b.x,top:b.y,width:b.w,height:b.h},
        series:[{name:'Predicted extra CH₃CN loss',xValues:b.xvalues.map(round),values:b.values.map(round),line:{fill:colors.teal,width:3},marker:{symbol:'none'}}],
        scatterOptions:{style:'line'},hasLegend:false,
        xAxis:{min:230,max:240,majorUnit:2,title:'Frequency (GHz)',numberFormatCode:'0',textStyle:{typeface:font,fontSize:21}},
        yAxis:{min:0,max:.05,majorUnit:.01,title:'Extra loss (dB)',numberFormatCode:'0.00',textStyle:{typeface:font,fontSize:21},majorGridlines:{fill:'#D9E2E8',width:1}},
        chartFill:'#FFFFFF',plotAreaFill:'#FFFFFF'});
      applyPresentationChartFont(ch,{fontFamily:font});charts.push(n);
    }
  }
  text(slide,s.caveat,66,786,1468,65,19.5,'red');
  text(slide,'Sources',66,856,82,25,17,'muted');
  const refWidth=1240/s.sources.length;
  s.sources.forEach((r,j)=>text(slide,r.label,155+j*refWidth,856,refWidth-8,25,17,'muted'));
  text(slide,n+'/7',1468,852,66,30,20,'muted');
  const body=s.blocks.map(b=>b.type==='text'?b.text:b.type==='math'?b.latex:b.type==='table'?b.values.map(r=>r.join(' | ')).join('\n'):'Predicted spectrum from saved data').join('\n\n');
  slide.speakerNotes.textFrame.setText(s.lead+'\n\n'+body+'\n\n'+s.notes+'\n\n'+s.caveat+'\n\nSources\n'+s.sources.map(r=>r.label+': '+r.url).join('\n'));
}
const candidate=path.join(TMP,'candidate.pptx');
await (await PresentationFile.exportPptx(p)).save(candidate);
const finalPath=path.join(ROOT,'output/presentations',process.env.DECK_NAME??'zenith_compact_example_v3.pptx');
const result=await finalizePresentation({workspaceDir:ROOT,candidatePath:candidate,finalPath,pythonExecutable:PYTHON,
  explicitTotalSlideCount:7,requiredNativeTableOwnerSlides:[...new Set(tables)],requiredNativeChartOwnerSlides:charts,
  integrityValidatorPath:path.join(SKILL,'container_tools/inspect_presentation_package_integrity.py'),
  layoutValidatorPath:path.join(SKILL,'container_tools/inspect_presentation_layout_geometry.py'),
  layoutArgs:['--expected-slide-size-emu','15240000,8572500','--validate-heading-fit',...[...new Set(tables)].flatMap(n=>['--require-native-table-slide',String(n)])],
  materializeLiteralChartWorkbooks:true,fontPolicy:{basis:'design',families:[font]},verifyArtifactToolImport:true,
  receiptPath:path.join(TMP,path.basename(finalPath)+'.validation.json')});
const finalDeck=await PresentationFile.importPptx(await FileBlob.load(result.finalPath));
await fs.mkdir(path.join(TMP,'renders'),{recursive:true});
for(let i=0;i<finalDeck.slides.items.length;i++){
  const png=await finalDeck.export({slide:finalDeck.slides.items[i],format:'png',scale:1});
  await fs.writeFile(path.join(TMP,'renders',`slide-${String(i+1).padStart(2,'0')}.png`),new Uint8Array(await png.arrayBuffer()));
}
console.log('Finalized and rendered seven slides:',result.finalPath);
