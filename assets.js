function showToast(msg, type){
  const colors = {success:'#16a34a', danger:'#dc2626', warning:'#f59e0b', info:'#2563eb'}
  const cont = document.getElementById('toastContainer')
  if(!cont) return alert(msg)
  const div = document.createElement('div')
  div.style.background = '#0b1220'
  div.style.border = '1px solid #334155'
  div.style.color = '#e5e7eb'
  div.style.borderLeft = '4px solid ' + (colors[type]||colors.info)
  div.style.padding = '10px 12px'
  div.style.marginBottom = '8px'
  div.style.borderRadius = '8px'
  div.textContent = msg
  cont.appendChild(div)
  setTimeout(()=>{div.remove()}, 3000)
}
function getUser(){
  try{return JSON.parse(localStorage.getItem('hms_user')||'null')}catch(e){return null}
}
function logout(){
  localStorage.removeItem('hms_user');
  location.href = '/login.html';
}
function renderNavUser(){
  const el = document.getElementById('navUser');
  if(!el) return;
  const u = getUser();
  if(u){
    const role = u.is_admin ? 'Admin' : 'User';
    el.innerHTML = `<span class="badge bg-primary">${u.name} (${role})</span> <a href="#" class="ms-2 link-light" onclick="logout()">Logout</a>`
  }else{
    el.innerHTML = `<a href="/login.html" class="nav-link">Login</a>`
  }
}
document.addEventListener('DOMContentLoaded', renderNavUser)
