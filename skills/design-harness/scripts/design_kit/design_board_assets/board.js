"use strict";
const data = JSON.parse(document.getElementById("board-data").textContent);
const gallery = document.getElementById("gallery");
const scene = document.getElementById("scene");
const scale = document.getElementById("scale");
const zoom = document.getElementById("zoom");
const names = {"shop-detail":"가게 상세", "product-updates":"전체 입고 소식", "write-update":"입고 제보", default:"기본", error:"오류", empty:"빈 화면", loading:"로딩", success:"완료"};
const cellLabel = c => c.map(x=>names[x]||x).join(" · ");
const cells = data.phase === "awaiting_final" || data.phase === "ready_for_build"
  ? [...new Map(data.candidates.flatMap(c=>c.frames).map(f=>[JSON.stringify(f.cell),f.cell])).values()]
  : data.cells;
cells.forEach((cell,i)=>scene.add(new Option(cellLabel(cell),String(i))));
function el(tag,text,className){const node=document.createElement(tag);if(text!==undefined)node.textContent=text;if(className)node.className=className;return node;}
function showScene(){
  gallery.replaceChildren();
  const current=cells[Number(scene.value)];
  if(!current)return;
  document.getElementById("feedback-screen").value=current[0];
  for(const candidate of data.candidates){
    const article=el("article",undefined,"candidate");
    article.append(el("h2",candidate.title),el("p",candidate.concept));
    const frame=candidate.frames.find(f=>JSON.stringify(f.cell)===JSON.stringify(current));
    if(frame){
      const scroll=el("div",undefined,"preview-scroll");scroll.tabIndex=0;scroll.setAttribute("aria-label",`${candidate.title} 미리보기 영역`);
      const button=el("button",undefined,"preview");button.type="button";button.dataset.scale=scale.value;
      if(scale.value!=="fit")button.style.width=`${frame.width*Number(scale.value)}px`;
      button.setAttribute("aria-label",`${candidate.title} ${cellLabel(current)} 확대`);
      const img=el("img");img.src=frame.image;img.alt=`${candidate.title} · ${cellLabel(current)}`;
      button.append(img);scroll.append(button);article.append(scroll);
      button.addEventListener("click",()=>{document.getElementById("zoom-title").textContent=img.alt;const large=document.getElementById("zoom-image");large.src=img.src;large.alt=img.alt;zoom.showModal();});
    }else article.append(el("p","이 상태는 아직 제작되지 않았습니다.","empty"));
    const features=el("ul");candidate.features.forEach(f=>features.append(el("li",f)));article.append(features);gallery.append(article);
    if(candidate.direction_image){const link=el("a","아트디렉션 보드 열기");link.href=candidate.direction_image;link.target="_blank";link.rel="noopener";article.append(link);}
  }
}
scene.addEventListener("change",showScene);scale.addEventListener("change",showScene);showScene();
function exportEvent(payload){
  const blob=new Blob([JSON.stringify(payload,null,2)],{type:"application/json"});
  const url=URL.createObjectURL(blob);const link=el("a");link.href=url;link.download=`${data.run_id}-${payload.kind}-${payload.id}.json`;link.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
}
for(const form of document.querySelectorAll('form[action="/event"]')){
  const textarea=form.querySelector("textarea");const draftKey=`design-draft:${data.run_id}:${form.id}`;
  try{textarea.value=localStorage.getItem(draftKey)||"";}catch{}
  textarea.addEventListener("input",()=>{try{localStorage.setItem(draftKey,textarea.value);}catch{}});
  let pendingId=null;
  form.addEventListener("input",()=>{pendingId=null;});
  form.addEventListener("submit",async e=>{
    e.preventDefault();if(!form.reportValidity())return;
    const values=Object.fromEntries(new FormData(form));
    const candidate=data.candidates.find(c=>c.id===values.candidate_id);
    pendingId ||= crypto.randomUUID();
    const payload={...values,id:pendingId,version:candidate.version,actor:"user",authority:"Explicit export from local comparison board"};
    const status=form.id==="feedback"?document.getElementById("feedback-status"):document.getElementById("run-status");
    if(!data.online){delete payload.csrf;exportEvent(payload);status.textContent="기록 파일을 다운로드했습니다. 하네스에 가져오면 저장됩니다.";return;}
    const button=form.querySelector('button[type="submit"]');button.disabled=true;
    try{
      const response=await fetch("/event",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(payload)});
      const result=await response.json();if(!response.ok)throw new Error(result.error||"저장하지 못했습니다.");
      status.classList.remove("error");status.textContent=form.id==="feedback"?"피드백을 저장했습니다.":values.kind==="final"?"전체 디자인의 최종 결정을 저장했습니다.":"방향 선택을 저장했습니다. 이 방향으로 전체 화면을 확장합니다.";
      try{localStorage.removeItem(draftKey);}catch{}
      if(form.id==="feedback"){textarea.value="";pendingId=null;}else{form.hidden=true;}
    }catch(error){status.classList.add("error");status.textContent=`저장되지 않았습니다. ${error.message} 내용을 유지했으니 연결 확인 후 다시 제출해 주세요.`;}
    finally{button.disabled=false;}
  });
}
