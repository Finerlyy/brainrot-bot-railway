window.switchTab = function(t){
    document.querySelectorAll('.tab-content').forEach(e=>e.classList.remove('active'));
    document.querySelectorAll('.nav-btn').forEach(e=>e.classList.remove('active'));
    document.getElementById(`tab-${t}`).classList.add('active');
    document.querySelector(`.nav-btn[onclick="switchTab('${t}')"]`).classList.add('active');
}
window.closeModal = function(id){
    document.getElementById(id).classList.add('hidden');
}

document.addEventListener('DOMContentLoaded', () => {
    const tg = window.Telegram.WebApp; 
    tg.expand();
    
    const API = window.location.origin + '/api';
    let userId = tg.initDataUnsafe?.user?.id || 0;
    let username = tg.initDataUnsafe?.user?.username || 'Guest';
    let allItems=[], currentBal=0, selectedCaseId=0, selectedCasePrice=0, selectedCount=1;

    const el = {
        bal: document.getElementById('balance'), 
        cases: document.getElementById('cases-grid'),
        inv: document.getElementById('inventory-grid'), 
        top: document.getElementById('leaderboard-list'),
        loader: document.getElementById('loading-screen'), 
        openModal: document.getElementById('open-modal'),
        mImg: document.getElementById('modal-case-img'), 
        mName: document.getElementById('modal-case-name'),
        mPrice: document.getElementById('modal-case-price'), 
        totalBtn: document.getElementById('total-price-btn'),
        popup: document.getElementById('drop-popup'), 
        dropGrid: document.getElementById('drop-results-grid'),
        audio: document.getElementById('audio-player')
    };

    function upBal(n){
        // Защита от NaN/Undefined
        if (n === undefined || n === null) return;
        
        if(currentBal !== n){
            el.bal.style.color = '#fff';
            setTimeout(() => el.bal.style.color = '', 300);
        }
        currentBal = n;
        el.bal.innerText = n; // Просто обновляем число
    }

    async function load(){
        try {
            const res = await fetch(`${API}/data`, {method:'POST', body:JSON.stringify({user_id:userId, username})});
            if (!res.ok) throw new Error("Server Error");
            
            const d = await res.json();
            allItems = d.case_items || []; 
            
            if(d.user) upBal(d.user.balance);

            // КЕЙСЫ
            el.cases.innerHTML = '';
            d.cases.forEach(c => {
                const div = document.createElement('div');
                div.className = 'case-card';
                div.innerHTML = `
                    <img src="${c.icon_url}" class="case-img">
                    <div class="case-name">${c.name}</div>
                    <div class="case-price"><span class="star-icon">⭐️</span> ${c.price}</div>
                `;
                div.onclick = () => showOpenModal(c);
                el.cases.appendChild(div);
            });

            // ИНВЕНТАРЬ
            el.inv.innerHTML = '';
            if(d.inventory.length === 0) el.inv.innerHTML = "<p style='color:#666;grid-column:1/-1;text-align:center'>Пусто</p>";
            
            d.inventory.reverse().forEach(i => {
                const div = document.createElement('div');
                div.className = `item-card rarity-${i.rarity}`;
                div.id = `inv-${i.inv_id}`;
                div.innerHTML = `
                    <img src="${i.image_url}" class="item-img">
                    <div class="case-name">${i.name}</div>
                    <button class="sell-btn" onclick="sell(${i.inv_id},${i.sell_price})">
                        Продать: <span>⭐️ ${i.sell_price}</span>
                    </button>
                `;
                el.inv.appendChild(div);
            });

            // ТОП
            el.top.innerHTML = '';
            d.leaderboard.forEach((u, i) => {
                el.top.innerHTML += `
                    <div style="padding:10px;border-bottom:1px solid #333;display:flex;justify-content:space-between;align-items:center">
                        <span>#${i+1} ${u.username}</span>
                        <span style="color:#FFD700;font-weight:bold">⭐️ ${u.balance}</span>
                    </div>`;
            });

            setTimeout(() => el.loader.style.opacity = '0', 200);
            setTimeout(() => el.loader.style.display = 'none', 700);
        } catch(e) { 
            console.error(e); 
        }
    }

    // --- ЛОГИКА ОТКРЫТИЯ ---
    window.showOpenModal = function(c) {
        selectedCaseId = c.id; 
        selectedCasePrice = c.price;
        el.mImg.src = c.icon_url; 
        el.mName.innerText = c.name; 
        el.mPrice.innerText = c.price;
        selectCount(1);
        el.openModal.classList.remove('hidden');
    }

    window.selectCount = function(n) {
        selectedCount = n;
        document.querySelectorAll('.count-btn').forEach(b => b.classList.toggle('active', b.innerText === `x${n}`));
        el.totalBtn.innerText = selectedCasePrice * n;
    }

    document.getElementById('start-open-btn').onclick = async () => {
        const totalPrice = selectedCasePrice * selectedCount;
        if(currentBal < totalPrice) return tg.showAlert("Недостаточно звезд!");
        
        el.openModal.classList.add('hidden');
        upBal(currentBal - totalPrice); // Визуальное списание

        // Показываем лоадер в попапе
        el.popup.classList.add('active');
        el.dropGrid.innerHTML = '<div class="spinner"></div>';

        try {
            const res = await fetch(`${API}/open`, {
                method:'POST', 
                body:JSON.stringify({user_id:userId, case_id:selectedCaseId, count:selectedCount})
            });
            const data = await res.json();
            
            if(data.error) { 
                el.popup.classList.remove('active');
                load(); // Возвращаем баланс
                return tg.showAlert(data.error); 
            }

            showResults(data.dropped);
        } catch(e) {
             console.error(e);
             tg.showAlert("Ошибка: " + e.message); 
             load();
        }
    };

    function showResults(items) {
        el.dropGrid.innerHTML = '';
        el.dropGrid.className = items.length > 1 ? 'drop-grid multi' : 'drop-grid single';
        
        items.forEach((item, i) => {
            const div = document.createElement('div'); 
            div.className = `drop-item rarity-${item.rarity}`; 
            div.style.animationDelay = `${i * 0.1}s`;
            div.innerHTML = `
                <img src="${item.image_url}">
                <div class="case-name" style="font-size:0.8rem">${item.name}</div>
                <div style="font-size:0.7rem;opacity:0.7">${item.rarity}</div>
            `;
            el.dropGrid.appendChild(div);
            
            // ИСПРАВЛЕНИЕ: Проверяем, что ссылка на звук не является прочерком "-"
            if(i === 0 && item.sound_url && item.sound_url !== '-' && item.sound_url.startsWith('http')) { 
                el.audio.src = item.sound_url; 
                el.audio.play().catch(err => console.log("Audio error:", err)); 
            }
        });
        load(); // Фоновое обновление инвентаря
    }

    // --- ПРОДАЖА ---
    window.sell = async function(id, p) {
        // Убрал confirm для скорости, можно вернуть если нужно
        // if(!confirm(`Продать за ${p}?`)) return;
        
        upBal(currentBal + p); 
        const itemNode = document.getElementById(`inv-${id}`);
        if(itemNode) itemNode.remove();

        try {
            const res = await fetch(`${API}/sell`, {
                method:'POST',
                body:JSON.stringify({user_id:userId, inv_id:id, price:p})
            });
            const d = await res.json();
            if(d.status !== 'ok') load(); // Если ошибка - откатываем
        } catch(e) {
            load();
        }
    };

    document.getElementById('claim-btn').onclick = () => { 
        el.popup.classList.remove('active'); 
        el.audio.pause(); 
    };
    
    // Загрузка
    load();
    
    // Авто-обновление баланса (каждые 4 сек)
    setInterval(() => {
        if(document.hidden || el.popup.classList.contains('active')) return;
        fetch(`${API}/data`, {method:'POST', body:JSON.stringify({user_id:userId, username})})
            .then(r => r.json())
            .then(d => { if(d.user) upBal(d.user.balance); })
            .catch(() => {});
    }, 4000);
});