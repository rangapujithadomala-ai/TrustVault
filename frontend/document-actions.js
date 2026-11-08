document.addEventListener("DOMContentLoaded",async()=>{
 const csrf=document.querySelector('meta[name="csrf-token"]')?.content||"";
 const controls=[...document.querySelectorAll("[data-star-document]")];
 try{const response=await fetch("/documents/starred",{credentials:"same-origin"});if(response.ok){const result=await response.json();const ids=new Set((result.documents||[]).map(d=>d.id));controls.forEach(button=>{const active=ids.has(button.dataset.starDocument);button.textContent=active?"★":"☆";button.setAttribute("aria-pressed",String(active));});}}catch(_){/* leave neutral outline stars if load fails */}
 controls.forEach(button=>button.addEventListener("click",async()=>{
  const response=await fetch(`/documents/${encodeURIComponent(button.dataset.starDocument)}/star`,{method:"POST",headers:{"X-CSRFToken":csrf}});
  const result=await response.json().catch(()=>({}));
  if(!response.ok){alert(result.error||"Unable to update starred status.");return;}
  button.textContent=result.starred?"★":"☆";button.setAttribute("aria-pressed",String(result.starred));
 }));
 document.querySelectorAll("[data-version-document]").forEach(input=>input.addEventListener("change",async()=>{
  const file=input.files?.[0];if(!file)return;
  const form=new FormData();form.append("file",file);
  const response=await fetch(`/documents/${encodeURIComponent(input.dataset.versionDocument)}/version`,{method:"POST",headers:{"X-CSRFToken":csrf},body:form});
  const result=await response.json().catch(()=>({}));
  if(response.ok){alert(result.message||"New version uploaded.");location.reload();}else alert(result.error||"Version upload failed.");
 }));
});
