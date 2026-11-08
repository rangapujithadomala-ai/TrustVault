document.addEventListener("DOMContentLoaded",function(){
 const emailDisplay=document.getElementById("email-display");
 const resendButton=document.getElementById("resend-button");
 const resendMessage=document.getElementById("resend-message");
 const email=new URLSearchParams(window.location.search).get("email")||"";
 if(email)emailDisplay.textContent=email;
 resendButton.addEventListener("click",async function(){
  const target=email||prompt("Enter your registered email address:");if(!target)return;
  const csrf=document.querySelector('meta[name="csrf-token"]')?.content||"";
  resendButton.disabled=true;resendButton.textContent="Sending...";resendMessage.textContent="";
  try{const response=await fetch("/auth/resend-verification",{method:"POST",headers:{"Content-Type":"application/json","X-CSRFToken":csrf},body:JSON.stringify({email:target})});const result=await response.json().catch(()=>({}));if(!response.ok)throw new Error(result.error||"Unable to resend verification email.");resendMessage.textContent=result.message||"If the account is eligible, a verification email will be sent.";}
  catch(error){resendMessage.textContent=error.message;}
  finally{resendButton.disabled=false;resendButton.textContent="Resend Verification Email";}
 });
});
