import {readFileSync,writeFileSync} from 'node:fs';
const dir=new URL('./',import.meta.url);
const moduleSource=readFileSync(new URL('fmb-tv-preferences.js',dir),'utf8');
const wrapperSource=readFileSync(new URL('worker-wrapper.js.txt',dir),'utf8');
const callback=`async () => {
  const dryRun = true;
  const expectedModifiedOn = '2026-10-20T03:44:37.04595Z';
  const expectedEtag = 'e3e2354e297e85dea54372189015bb727357b84f5d032dfef4f73f8ada189692';
  const moduleSource = ${JSON.stringify(moduleSource)};
  const wrapperSource = ${JSON.stringify(wrapperSource)};
  const name = 'fm-blog-database';
  const sha256=async text=>[...new Uint8Array(await crypto.subtle.digest('SHA-256',new TextEncoder().encode(text)))].map(x=>x.toString(16).padStart(2,'0')).join('');
  const scriptPath = '/accounts/' + accountId + '/workers/scripts/' + name;
  const fail = message => { throw new Error(message); };
  async function workerMetadata() {
    const result = await cloudflare.request({method:'GET',path:'/accounts/' + accountId + '/workers/scripts'});
    if (!result.success || !Array.isArray(result.result)) fail('Could not read current Worker metadata.');
    const worker = result.result.find(w=>w.id===name);
    if (!worker || worker.modified_on!==expectedModifiedOn || worker.etag!==expectedEtag) fail('Worker changed since review; fetch and review its new state before retrying.');
    return worker;
  }
  const before=await workerMetadata();
  const [download,settingsResponse]=await Promise.all([
    cloudflare.request({method:'GET',path:scriptPath}),
    cloudflare.request({method:'GET',path:scriptPath+'/settings'})
  ]);
  if(!download.success || typeof download.result!=='string' || !settingsResponse.success) fail('Could not read complete current Worker.');
  const raw=download.result, settings=settingsResponse.result;
  if (raw.includes('--- TRUNCATED ---')) fail('Worker download was truncated.');
  const firstBreak=raw.indexOf('\\r\\n'), boundary=raw.slice(2,firstBreak);
  if (!boundary || !raw.startsWith('--') || !raw.includes('--'+boundary+'--')) fail('Invalid Worker multipart.');
  const parsed=[];
  for (const chunk of raw.split('--'+boundary).slice(1)) {
    if (chunk.startsWith('--')) break;
    if (!chunk.startsWith('\\r\\n') || !chunk.endsWith('\\r\\n')) fail('Invalid multipart framing.');
    const part=chunk.slice(2,-2), split=part.indexOf('\\r\\n\\r\\n');
    if(split<0)fail('Invalid module headers.');
    let header=part.slice(0,split), body=part.slice(split+4);
    const moduleName=header.match(/name="([^"]+)"/)?.[1];
    if(!moduleName || parsed.some(p=>p.name===moduleName))fail('Missing or duplicated module name.');
    // Downloads omit filename, but uploads must submit files, not text fields.
    if(!/filename=/.test(header))header=header.replace(/(Content-Disposition:[^\\r\\n]+)/i,'$1; filename="'+moduleName+'"');
    if(!/Content-Type:/i.test(header)) {
      const type=moduleName.endsWith('.js')?'application/javascript+module':moduleName==='_headers'?'text/plain':null;
      if(!type)fail('Unknown original module type: '+moduleName);
      header+='\\r\\nContent-Type: '+type;
    }
    parsed.push({name:moduleName,header,body});
  }
  if(parsed.length<30)fail('Unexpectedly incomplete Worker module inventory.');
  if(parsed.some(p=>p.name==='fmb-tv-preferences.js'))fail('FM TV module already exists; do not overwrite a prior deployment.');
  const main=parsed.filter(p=>p.name==='index.js');
  if(main.length!==1)fail('Expected exactly one index.js.');
  const previousMain=main[0].body;
  if((previousMain.match(/export\\s*\\{zA as default\\}/g)||[]).length!==1 ||
     (previousMain.match(/const fmbForumPreviousFetch=zA.fetch;/g)||[]).length!==1 ||
     !previousMain.includes('function bl(') || !previousMain.includes('function $0(') ||
     !previousMain.includes('async function cl(') || !previousMain.includes('async function ul(')) fail('Existing handler/auth contract changed; review required.');
  if(previousMain.includes('FM_TV_PREFERENCES_V1') || previousMain.includes('fmbTvPreviousFetch'))fail('FM TV wrapper already exists.');
  main[0].body=previousMain+'\\n'+wrapperSource+'\\n';
  parsed.push({name:'fmb-tv-preferences.js',header:'Content-Disposition: form-data; name="fmb-tv-preferences.js"; filename="fmb-tv-preferences.js"\\r\\nContent-Type: application/javascript+module',body:moduleSource});
  if(!Array.isArray(settings.bindings) || !settings.bindings.some(b=>b.name==='DB'&&b.type==='d1'&&b.id==='0db4e400-2e0c-4eff-812a-e1b4ff73aebb'))fail('DB binding changed; migration target must be reviewed.');
  const metadata={main_module:'index.js',keep_assets:true,keep_bindings:[...new Set(settings.bindings.map(b=>b.type))]};
  for(const key of ['compatibility_date','compatibility_flags','usage_model','tags','tail_consumers','logpush','observability','annotations','limits','cache_options']){
    if(Object.prototype.hasOwnProperty.call(settings,key))metadata[key]=settings[key];
  }
  if(settings.placement && Object.keys(settings.placement).length){
    metadata.placement={...settings.placement};delete metadata.placement.last_analyzed_at;delete metadata.placement.status;
  }
  const mainBeforeSha256=await sha256(previousMain);
  if(mainBeforeSha256!=='cde696dda34ab7e751c1f3c45991ce6655629edcbd9e5af58dc45c24e53c588c')fail('Main module changed since review.');
  const inventory=await Promise.all(parsed.map(async p=>({name:p.name,chars:p.body.length,sha256:await sha256(p.body)})));
  const summary={dryRun,beforeModifiedOn:before.modified_on,beforeEtag:before.etag,originalChars:raw.length,originalModules:parsed.length-1,newModules:parsed.length,mainBeforeChars:previousMain.length,mainBeforeSha256,mainAfterChars:main[0].body.length,bindings:settings.bindings.map(b=>({name:b.name,type:b.type})),inventory};
  const uploadBoundary='FMTV'+Date.now().toString(16);
  const pieces=['--'+uploadBoundary+'\\r\\nContent-Disposition: form-data; name="metadata"\\r\\nContent-Type: application/json\\r\\n\\r\\n'+JSON.stringify(metadata)+'\\r\\n'];
  for(const part of parsed)pieces.push('--'+uploadBoundary+'\\r\\n'+part.header+'\\r\\n\\r\\n'+part.body+'\\r\\n');
  pieces.push('--'+uploadBoundary+'--\\r\\n');
  const uploadBody=pieces.join('');
  const form=await new Response(uploadBody,{headers:{'Content-Type':'multipart/form-data; boundary='+uploadBoundary}}).formData();
  for(const part of parsed){
    const file=form.get(part.name);
    if(!file || typeof file==='string' || typeof file.text!=='function')fail('Module is not a multipart file: '+part.name);
    if(await file.text()!==part.body)fail('Multipart round-trip changed module body: '+part.name);
  }
  if(form.getAll('index.js').length!==1 || JSON.parse(form.get('metadata')).main_module!=='index.js')fail('Multipart main_module mismatch.');
  summary.multipartFiles=parsed.length;summary.mainMultipartFile=form.get('index.js').name;
  if(dryRun)return summary;
  // No remote state changes before this point. Re-check immediately before upload.
  await workerMetadata();
  const lastSettings=await cloudflare.request({method:'GET',path:scriptPath+'/settings'});
  if(!lastSettings.success || JSON.stringify(lastSettings.result)!==JSON.stringify(settings))fail('Worker settings changed during preparation.');
  const result=await cloudflare.request({method:'PUT',path:scriptPath,body:uploadBody,contentType:'multipart/form-data; boundary='+uploadBoundary,rawBody:true});
  return {...summary,success:result.success,status:result.status,errors:result.errors,result:result.success?{id:result.result?.id,etag:result.result?.etag,modified_on:result.result?.modified_on,deployment_id:result.result?.deployment_id}:undefined};
}`;
writeFileSync(new URL('cloudflare-deploy-callback.js',dir),callback+'\n');
console.log('Generated read-only-by-default callback; change dryRun only after review/migration.');
