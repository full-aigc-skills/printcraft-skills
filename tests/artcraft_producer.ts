/** 显式跨仓原生验收：实际 ArtCraft 调度器和 VectorCraft 公共技能，不参与基础测试。 */
import {readFile,writeFile,mkdir,rename,readdir,lstat} from 'node:fs/promises';
import {resolve,join} from 'node:path';
import {pathToFileURL} from 'node:url';
import {createHash} from 'node:crypto';
import assert from 'node:assert/strict';
import {execFile} from 'node:child_process';
import {promisify} from 'node:util';
const [artRoot,vectorSkill,nativeExecutable,runtimeHome,python,workdir]=process.argv.slice(2).map(value=>resolve(value));
if(process.argv.length!==8)throw new Error('six_explicit_paths_required');
const sha=(value:Buffer|string)=>createHash('sha256').update(value).digest('hex');
async function sourceInventory(){
 const result:Record<string,string>={};
 async function visit(directory:string){
  for(const entry of (await readdir(join(artRoot,directory),{withFileTypes:true})).sort((a,b)=>a.name.localeCompare(b.name))){
   const name=directory+'/'+entry.name;
   if(entry.isSymbolicLink())throw new Error('producer_source_symlink');
   if(entry.isDirectory())await visit(name);
   else if(entry.isFile())result[name]=sha(await readFile(join(artRoot,name)));
  }
 }
 await visit('src');await visit('schemas');
 result['package.json']=sha(await readFile(join(artRoot,'package.json')));
 return result;
}
const sourceSha256=await sourceInventory();
const load=(path:string)=>import(pathToFileURL(join(artRoot,'src',path)).href);
const {TaskLedger}=await load('harness/task_ledger.ts');
const {LocalRunner}=await load('harness/local_runner.ts');
const {WorkflowEngine}=await load('planning/workflow_engine.ts');
const {publicSkillFactory}=await load('adapters/public_skill.ts');
const {packageProject,verifyProjectPackage}=await load('artifacts/project_package.ts');
const producerVersion=JSON.parse(await readFile(join(artRoot,'package.json'),'utf8')).version;
const files=await Promise.all((await readdir(join(vectorSkill,'scripts'))).filter(name=>/\.(py|json)$/.test(name)).sort().map(async name=>{
 const path=join(vectorSkill,'scripts',name);
 if((await lstat(path)).isSymbolicLink())throw new Error('vector_resource_symlink');
 return {path,sha256:sha(await readFile(path))};
}));
const lock=JSON.parse(await readFile(join(vectorSkill,'scripts/runtime.lock.json'),'utf8'));
const version=(await promisify(execFile)(nativeExecutable,['--version'])).stdout.trim();
const identity={pluginId:'vectorcraft',pluginVersion:'0.1.0-cross-plugin-acceptance',cliVersion:version,sha256:sha(await readFile(nativeExecutable)),mode:'headless',capabilitySnapshotSha256:sha(JSON.stringify(lock))};
await mkdir(workdir,{recursive:false});
const ledger=new TaskLedger(join(workdir,'tasks.sqlite'));
const factory=publicSkillFactory({pluginId:'vectorcraft',skillRoot:vectorSkill,python,pythonSha256:sha(await readFile(python)),nativeExecutable,runtimeHome,files,outputRoot:join(workdir,'deliveries')});
const launches:string[]=[];
const tracked=async(node:any,inputs:any[],taskId:string)=>{
 const result=await factory(node,inputs,taskId);
 const prepare=result.adapter.prepare;
 return {...result,adapter:{...result.adapter,prepare:async(request:any)=>{launches.push(node.id);return prepare(request);}}};
};
const engine=new WorkflowEngine(ledger,new LocalRunner(ledger,async(request:any)=>assert.equal(request.authorizationRef,'printcraft-cross-plugin-fixtures')),{vectorcraft:tracked});
const node=(id:string,color:string)=>({id,dependsOn:[],projectKey:id,runtimeIdentity:identity,expectedRevision:null,payload:{schemaVersion:'craft-skill-workflow/v1',plan:{document:{name:id,width:128,height:96,units:'Points'},operations:[{command:'shape.rectangle',params:{x:24,y:24,width:64,height:48},as:'badge'},{command:'paint.setFill',params:{ids:[{$ref:'badge.id'}],color}},{command:'paint.setStroke',params:{ids:[{$ref:'badge.id'}],none:true}}],exports:[{format:'pdf',artboard:0},{format:'png',artboard:0}]},assetBindings:[],outputs:[{assetId:id+'-pdf',location:'artboard-1.pdf',mediaType:'application/pdf'}]}});
const plan={workflowId:'printcraft-cross-plugin',ownerId:'fixture-owner',revision:'v1',authorizationRef:'printcraft-cross-plugin-fixtures',budget:{currency:'USD',maxMinorUnits:0,maxRevisions:2,maxExternalCalls:0},deadline:new Date(Date.now()+600000).toISOString(),nodes:[node('change','#ef5b36'),node('preserve','#27ae60')]};
try{
 const first=await engine.run(plan);
 await writeFile(join(workdir,'first.json'),JSON.stringify(first,null,2));
 assert.equal(first.state,'review_ready',JSON.stringify(first));
 assert.deepEqual(launches.sort(),['change','preserve']);launches.splice(0);
 const firstPackage=await packageProject(ledger,first.runKey,plan.ownerId,plan.authorizationRef,join(workdir,'package-v1'));
 const revised=structuredClone(plan);revised.revision='v2';
 const previous=first.nodes.change;
 revised.nodes[0].expectedRevision=previous.outputs[0].nativeProjectRef.sha256;
 revised.nodes[0].externalInputs=[{root:previous.root,artifact:previous.outputs[0]}];
 revised.nodes[0].payload.sourceProject={assetId:previous.outputs[0].assetId};
 delete revised.nodes[0].payload.plan.document;
 revised.nodes[0].payload.plan.operations=[{command:'paint.setFill',params:{ids:[{$ref:'badge.id'}],color:'#2458d6'}}];
 const second=await engine.run(revised);
 await writeFile(join(workdir,'second.json'),JSON.stringify(second,null,2));
 assert.equal(second.state,'review_ready',JSON.stringify(second));
 assert.deepEqual(launches,['change']);
 assert.equal(second.nodes.preserve.taskId,first.nodes.preserve.taskId);
 assert.equal(second.nodes.preserve.outputs[0].sha256,first.nodes.preserve.outputs[0].sha256);
 assert.notEqual(second.nodes.change.outputs[0].sha256,first.nodes.change.outputs[0].sha256);
 const secondPackage=await packageProject(ledger,second.runKey,plan.ownerId,plan.authorizationRef,join(workdir,'package-v2'));
 await mkdir(join(workdir,'移动 空格'),{recursive:false});
 const moved=join(workdir,'移动 空格','package-v2');await rename(secondPackage.root,moved);
 const verifiedFirst=await verifyProjectPackage(firstPackage.root,firstPackage.sha256);
 const verifiedSecond=await verifyProjectPackage(moved,secondPackage.sha256);
 assert.deepEqual(await sourceInventory(),sourceSha256,'producer source changed');
 for(const file of files)assert.equal(sha(await readFile(file.path)),file.sha256);
 const report={status:'PASS',scope:'REAL_LOCAL_ARTCRAFT_VECTORCRAFT_PRODUCER_NOT_PUBLISHED_HOST',producer:'artcraft',producerVersion,sourceSha256,vectorRuntime:identity,vectorSkillFiles:files,selectiveRework:{changedNodes:launches,preservedTaskId:second.nodes.preserve.taskId,preservedSha256:second.nodes.preserve.outputs[0].sha256},portablePackage:{status:'PASS_SAME_MACHINE_DIRECTORY_MOVE',sha256:secondPackage.sha256,root:moved},first:verifiedFirst,second:verifiedSecond};
 await writeFile(join(workdir,'producer-report.json'),JSON.stringify(report,null,2));
 console.log(JSON.stringify({status:'PASS',report:join(workdir,'producer-report.json')}));
}finally{ledger.close();}
