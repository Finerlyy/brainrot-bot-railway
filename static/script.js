document.addEventListener('DOMContentLoaded', () => {
    const tg = window.Telegram.WebApp;
    tg.expand(); 
    const API_URL = window.location.origin + '/api';
    const CARD_WIDTH = 100;
    
    let userId = tg.initDataUnsafe?.user?.id || 0;
    let username = tg.initDataUnsafe?.user?.username || 'Guest';
    let allItems = []; 

    const els = {
        bal: document.getElementById('balance'), user: document.getElementById('username'),
        cases: document.getElementById('cases-grid'), inv: document.getElementById('inventory-grid'),
        top: document.getElementById('leaderboard-list'),
        modal: document.getElementById('roulette-modal'), tape: document.getElementById('roulette-tape'),
        popup: document.getElementById('drop-popup'), pImg: document.getElementById('popup-img'),
        pName: document.getElementById('popup-name'), pRar: document.getElementById('popup-rarity'),
        audio: document.getElementById('audio-player')
    };

    async function load() {
        try {
            const res = await fetch(`${API_URL}/data`, { method: 'POST', body: JSON.stringify({ user_id: userId, username }) });
            const data = await res.json();
            allItems = data.case_items || [];
            
            if(data.user) { els.bal.innerText = data.user.balance; els.user.innerText = data.user.username; }
            
            els.cases.innerHTML = '';
            data.cases.forEach(c => {
                const d = document.createElement('div'); d.className = 'case-card';
                d.innerHTML = `<img src="${c.icon_url}" class="case-img"><div class="case-name">${c.name}</div><div class="case-price">${c.price} 💰</div>`;
                d.onclick = () => open(c.id, c.price, data.user.balance);
                els.cases.appendChild(d);
            });

            els.inv.innerHTML = '';
            data.inventory.reverse().forEach(i => {
                const d = document.createElement('div'); d.className = `item-card rarity-${i.rarity}`;
                d.innerHTML = `<img src="${i.image_url}" class="item-img"><div class="item-name">${i.name}</div>`;
                els.inv.appendChild(d);
            });

            els.top.innerHTML = '';
            data.leaderboard.forEach((u, i) => {
                els.top.innerHTML += `<div style="padding:5px; border-bottom:1px solid #333">#${i+1} ${u.username} - ${u.balance}💰</div>`;
            });
        } catch(e) { console.error(e); }
    }

    async function open(cid, price, bal) {
        if(bal < price) return tg.showAlert("Нет денег!");
        
        els.modal.classList.remove('hidden');
        els.tape.style.transition = 'none';
        els.tape.style.transform = 'translateX(0)';
        els.tape.innerHTML = '';

        const res = await fetch(`${API_URL}/open`, { method: 'POST', body: JSON.stringify({ user_id: userId, case_id: cid }) });
        const resD = await res.json();
        
        if(resD.error) { els.modal.classList.add('hidden'); return tg.showAlert(resD.error); }

        const WIN = 40; 
        for(let i=0; i<50; i++) {
            let it = (i===WIN) ? resD.dropped : allItems[Math.floor(Math.random()*allItems.length)];
            const d = document.createElement('div'); d.className = `roulette-item rarity-${it?.rarity || 'Common'}`;
            d.innerHTML = `<img src="${it?.image_url || ''}">`;
            els.tape.appendChild(d);
        }

        setTimeout(() => {
            const offset = (WIN * CARD_WIDTH) - 150 + (CARD_WIDTH/2);
            els.tape.style.transition = 'transform 5s cubic-bezier(0.1,0.9,0.1,1)';
            els.tape.style.transform = `translateX(-${offset}px)`;
        }, 100);

        setTimeout(() => {
            els.modal.classList.add('hidden');
            els.popup.classList.remove('hidden');
            els.pImg.src = resD.dropped.image_url;
            els.pName.innerText = resD.dropped.name;
            els.pRar.innerText = resD.dropped.rarity;
            if(resD.dropped.sound_url) { els.audio.src = resD.dropped.sound_url; els.audio.play().catch(()=>{}); }
            load();
        }, 5200);
    }

    document.getElementById('claim-btn').onclick = () => {
        els.popup.classList.add('hidden');
        els.audio.pause();
    };

    load();
});