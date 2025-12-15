window.switchTab = function(t){document.querySelectorAll('.tab-content').forEach(e=>e.classList.remove('active'));document.querySelectorAll('.nav-btn').forEach(e=>e.classList.remove('active'));document.getElementById(`tab-${t}`).classList.add('active');document.querySelector(`.nav-btn[onclick="switchTab('${t}')"]`).classList.add('active');}
window.closeModal = function(id){document.getElementById(id).classList.add('hidden');}

document.addEventListener('DOMContentLoaded', () => {
    const tg = window.Telegram.WebApp; tg.expand();
    const API = window.location.origin + '/api';
    let userId = tg.initDataUnsafe?.user?.id || 0;
    let username = tg.initDataUnsafe?.user?.username || 'Guest';
    let allItems=[], currentBal=0, selectedCaseId=0, selectedCasePrice=0, selectedCount=1;

    const el = {
        bal: document.getElementById('balance'), cases: document.getElementById('cases-grid'),
        inv: document.getElementById('inventory-grid'), top: document.getElementById('leaderboard-list'),
        loader: document.getElementById('loading-screen'), openModal: document.getElementById('open-modal'),
        mImg: document.getElementById('modal-case-img'), mName: document.getElementById('modal-case-name'),
        mPrice: document.getElementById('modal-case-price'), totalBtn: document.getElementById('total-price-btn'),
        roulette: document.getElementById('roulette-modal'), tape: document.getElementById('roulette-tape'),
        popup: document.getElementById('drop-popup'), dropGrid: document.getElementById('drop-results-grid'),
        audio: document.getElementById('audio-player')
    };

    function upBal(n){if(currentBal!==n){el.bal.style.color='#fff';setTimeout(()=>el.bal.style.color='#ffd700',300);}currentBal=n;el.bal.innerText=n;}

    async function load(){try{
        const res=await fetch(`${API}/data`,{method:'POST',body:JSON.stringify({user_id:userId,username})});
        const d=await res.json(); allItems=d.case_items||[]; if(d.user)upBal(d.user.balance);
        el.cases.innerHTML='';d.cases.forEach(c=>{const div=document.createElement('div');div.className='case-card';div.innerHTML=`<img src="${c.icon_url}" class="case-img"><div class="case-name">${c.name}</div><div class="case-price">${c.price} 💰</div>`;div.onclick=()=>showOpenModal(c);el.cases.appendChild(div);});
        el.inv.innerHTML='';if(d.inventory.length===0)el.inv.innerHTML="<p style='color:#666;grid-column:1/-1'>Пусто</p>";
        d.inventory.reverse().forEach(i=>{const div=document.createElement('div');div.className=`item-card rarity-${i.rarity}`;div.id=`inv-${i.inv_id}`;div.innerHTML=`<img src="${i.image_url}" class="item-img"><div class="item-name">${i.name}</div><button class="sell-btn" onclick="sell(${i.inv_id},${i.sell_price})">Продать: <span>${i.sell_price}</span></button>`;el.inv.appendChild(div);});
        el.top.innerHTML='';d.leaderboard.forEach((u,i)=>{el.top.innerHTML+=`<div style="padding:10px;border-bottom:1px solid #333;display:flex;justify-content:space-between"><span>#${i+1} ${u.username}</span><span>${u.balance}💰</span></div>`});
        setTimeout(()=>el.loader.style.display='none',500);
    }catch(e){console.error(e);}}

    // --- ЛОГИКА ОТКРЫТИЯ ---
    window.showOpenModal = function(c) {
        selectedCaseId = c.id; selectedCasePrice = c.price;
        el.mImg.src = c.icon_url; el.mName.innerText = c.name; el.mPrice.innerText = c.price;
        selectCount(1); // Сброс на x1
        el.openModal.classList.remove('hidden');
    }

    window.selectCount = function(n) {
        selectedCount = n;
        document.querySelectorAll('.count-btn').forEach(b => b.classList.toggle('active', b.innerText === `x${n}`));
        el.totalBtn.innerText = selectedCasePrice * n;
    }

    document.getElementById('start-open-btn').onclick = async () => {
        const totalPrice = selectedCasePrice * selectedCount;
        if(currentBal < totalPrice) return tg.showAlert("Недостаточно денег!");
        
        el.openModal.classList.add('hidden');
        upBal(currentBal - totalPrice); // Списываем сразу

        if(selectedCount === 1) {
            // Рулетка для одного кейса
            el.roulette.classList.remove('hidden'); el.tape.style.transition='none'; el.tape.style.transform='translateX(0)'; el.tape.innerHTML='';
        } else {
            // Сразу показываем лоадер для мульти-открытия
             el.popup.classList.add('active');
             el.dropGrid.innerHTML = '<div class="spinner"></div>';
        }

        try {
            const res = await fetch(`${API}/open`, {method:'POST', body:JSON.stringify({user_id:userId, case_id:selectedCaseId, count:selectedCount})});
            const data = await res.json();
            
            if(data.error) { 
                el.roulette.classList.add('hidden'); el.popup.classList.remove('active');
                load(); return tg.showAlert(data.error); 
            }

            if(selectedCount === 1) {
                // Запуск рулетки
                const WIN=40, dropped=data.dropped[0];
                for(let i=0;i<50;i++){const it=(i===WIN)?dropped:allItems[Math.floor(Math.random()*allItems.length)];const d=document.createElement('div');d.className=`roulette-item rarity-${it.rarity}`;d.innerHTML=`<img src="${it.image_url}">`;el.tape.appendChild(d);}
                setTimeout(()=>{el.tape.style.transition='transform 5s cubic-bezier(0.1,0.9,0.1,1)';el.tape.style.transform=`translateX(-${(WIN*120)-150+60}px)`;},100);
                setTimeout(()=>showResults(data.dropped), 5200);
            } else {
                // Сразу показываем результаты мульти-открытия
                showResults(data.dropped);
            }
        } catch(e) {
             tg.showAlert("Ошибка сети"); load();
        }
    };

    function showResults(items) {
        el.roulette.classList.add('hidden');
        el.popup.classList.add('active');
        el.dropGrid.innerHTML = '';
        el.dropGrid.className = items.length > 1 ? 'drop-grid multi' : 'drop-grid single';
        
        items.forEach((item, i) => {
            const div = document.createElement('div'); div.className = `drop-item rarity-${item.rarity}`; div.style.animationDelay = `${i*0.1}s`;
            div.innerHTML = `<img src="${item.image_url}"><h3>${item.name}</h3><p>${item.rarity}</p>`;
            el.dropGrid.appendChild(div);
            if(i===0 && item.sound_url) { el.audio.src=item.sound_url; el.audio.play().catch(()=>{}); }
        });
        load(); // Фоновое обновление
    }

    // --- ПРОДАЖА ---
    window.sell = async function(id, p) {
        if(!confirm(`Продать за ${p}?`)) return;
        upBal(currentBal + p); document.getElementById(`inv-${id}`)?.remove();
        const res = await fetch(`${API}/sell`,{method:'POST',body:JSON.stringify({user_id:userId,inv_id:id,price:p})});
        if((await res.json()).status!=='ok') load();
    };

    document.getElementById('claim-btn').onclick = () => { el.popup.classList.remove('active'); el.audio.pause(); };
    
    load();
    setInterval(()=>{if(document.hidden)return;fetch(`${API}/data`,{method:'POST',body:JSON.stringify({user_id:userId,username})}).then(r=>r.json()).then(d=>{if(d.user)upBal(d.user.balance)})},3000);
});