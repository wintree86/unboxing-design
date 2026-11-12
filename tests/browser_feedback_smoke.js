// Run only against the isolated synthetic board produced by design_factory.
async (page) => {
  const origin = new URL(page.url()).origin;
  const initial = await (await page.request.get(`${origin}/status`)).json();
  if (initial.run_id !== 'test' || initial.selected || initial.candidates?.[0]?.concept !== 'Concept a' ||
      initial.references?.[0]?.url !== 'https://example.com/reference' || initial.eligible_candidate_ids.length !== 2) {
    throw new Error('Expected a fresh synthetic feedback fixture, never a product run');
  }
  const measures=[];
  for (const width of [390,1200]) {
    await page.setViewportSize({width,height:900});await page.goto(origin);
    await page.locator('details').last().locator('summary').click();
    await page.evaluate(async()=>Promise.all([...document.querySelectorAll('img[src]')].map(i=>{i.loading='eager';return i.decode()})));
    measures.push(await page.evaluate(()=>({width:innerWidth,overflow:Math.max(0,document.documentElement.scrollWidth-innerWidth),
      images:document.querySelectorAll('img[src]').length,
      decoded:[...document.querySelectorAll('img[src]')].filter(i=>i.complete&&i.naturalWidth>0).length,
      referenceLinks:[...document.querySelectorAll('.references a')].filter(a=>a.textContent.includes('관찰 기록')).length,
      choices:document.querySelectorAll('#decision input[type=radio]').length,
      minControlHeight:Math.min(...[...document.querySelectorAll('#feedback select,#feedback textarea,#feedback button')].map(e=>e.getBoundingClientRect().height))})));
  }
  await page.locator('#feedback-candidate').selectOption('a');
  await page.locator('#feedback-intent').selectOption('rejection');
  await page.locator('#feedback-text').fill('Synthetic rejection of A; not a product choice');
  const rejection=page.waitForResponse(r=>r.url()===origin+'/event');await page.locator('#feedback button').click();
  const rejectionStatus=(await rejection).status();
  await page.waitForFunction(()=>!document.querySelector('#choose-a'));
  const afterA=await page.locator('#decision input[type=radio]').evaluateAll(es=>es.map(e=>e.value));
  await page.locator('#choose-b').check();await page.locator('#reason').fill('Synthetic scope-preservation check');
  const selection=page.waitForResponse(r=>r.url()===origin+'/event');await page.locator('#decision button').click();
  const selectionStatus=(await selection).status();await page.reload();
  await page.locator('#feedback-candidate').selectOption('');await page.locator('#feedback-intent').selectOption('diagnosis_only');
  await page.locator('#feedback-text').fill('Synthetic diagnosis only; stop all production');
  const hold=page.waitForResponse(r=>r.url()===origin+'/event');await page.locator('#feedback button').click();
  const holdStatus=(await hold).status();
  await page.waitForFunction(()=>document.querySelector('h1').textContent==='원인 조사와 피드백');
  const status=await (await page.request.get(origin+'/status')).json();
  const afterHold={choices:await page.locator('#decision input[type=radio]').count(),phase:status.phase,
    work_mode:status.work_mode,production_allowed:status.production_allowed,selected:status.selected?.candidate_id};
  const result={measures,rejectionStatus,afterA,selectionStatus,holdStatus,afterHold};
  if(measures.some(m=>m.overflow!==0||m.images!==4||m.decoded!==4||m.referenceLinks!==3||m.choices!==2||m.minControlHeight<48)||
     afterA.join()!=='b'||[rejectionStatus,selectionStatus,holdStatus].some(s=>s!==200)||afterHold.choices!==0||
     afterHold.production_allowed!==false||afterHold.selected!=='b'||afterHold.phase!=='diagnosis_only')throw new Error(JSON.stringify(result));
  return result;
}
