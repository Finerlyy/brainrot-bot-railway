// Глобальная функция для переключения вкладок
window.switchTab = function(tabName) {
    document.querySelectorAll('.tab-content').forEach(el => el.classList.remove('active'));
    document.querySelectorAll('.nav-btn').forEach(el => el.classList.remove('active'));
    document.getElementById(`tab-${tabName}`).classList.add('active');
    document.querySelector(`.nav-btn[onclick="switchTab('${tabName}')"]`).classList.add('active');
};

document.addEventListener('DOMContentLoaded', () => {
    const tg = window.Telegram.WebApp;
    tg.expand();
    
    const API_URL = window.location.origin + '/api';
    const CARD_WIDTH = 100;
    
    let userId = tg.initDataUnsafe?.user?.id || 0;
    let username = tg.initDataUnsafe?.user?.username || 'Guest';
    let allItems = [];
    let currentBalance = 0;

    const els = {
        bal: document.getElementById('balance'),
        cases: document.getElementById('cases-grid'),
        inv: document.getElementById('inventory-grid'),
        top: document.getElementById('leaderboard-list'),
        modal: document.getElementById('roulette-modal'),
        tape: document.getElementById('roulette-tape'),
        popup: document.getElementById('drop-popup'),
        pImg: document.getElementById('popup-img'),
        pName: document.getElementById('popup-name'),
        pRar: document.getElementById('popup-rarity'),
        audio: document.getElementById('audio-player'),
        loader: document.getElementById('loading-screen')
    };

    function updateBalanceDisplay(newBalance) {
        // Если баланс изменился, делаем небольшую анимацию цвета
        if (currentBalance !== newBalance) {
            els.bal.style.color = '#fff'; // Вспышка белым
            setTimeout(() => els.bal.style.color = '#ffd700', 300); // Возврат к золотому
        }
        currentBalance = newBalance;
        els.bal.innerText = newBalance;
    }

    async function load() {
        try {
            const res = await fetch(`${API_URL}/data`, { method: 'POST', body: JSON.stringify({ user_id: userId, username }) });
            const data = await res.json();
            allItems = data.case_items || [];
            
            if(data.user) updateBalanceDisplay(data.user.balance);
            
            // КЕЙСЫ
            els.cases.innerHTML = '';
            data.cases.forEach(c => {
                const d = document.createElement('div'); d.className = 'case-card';
                d.innerHTML = `<img src="${c.icon_url}" class="case-img"><div class="case-name">${c.name}</div><div class="case-price">${c.price} 💰</div>`;
                d.onclick = () => openCase(c.id, c.price);
                els.cases.appendChild(d);
            });

            // ИНВЕНТАРЬ
            els.inv.innerHTML = '';
            if (data.inventory.length === 0) els.inv.innerHTML = "<p style='text-align:center;width:100%;color:#666'>Пусто</p>";
            
            data.inventory.reverse().forEach(i => {
                const d = document.createElement('div'); 
                d.className = `item-card rarity-${i.rarity}`;
                d.id = `inv-item-${i.inv_id}`;
                d.innerHTML = `
                    <img src="${i.image_url}" class="item-img">
                    <div class="item-name">${i.name}</div>
                    <button class="sell-btn" onclick="sellItem(${i.inv_id}, ${i.sell_price})">Продать: <span>${i.sell_price}</span></button>
                `;
                els.inv.appendChild(d);
            });

            // ТОП
            els.top.innerHTML = '';
            data.leaderboard.forEach((u, i) => {
                els.top.innerHTML += `<div style="padding:10px; border-bottom:1px solid #333; display:flex; justify-content:space-between;"><span>#${i+1} ${u.username}</span> <span>${u.balance}💰</span></div>`;
            });

            setTimeout(() => els.loader.style.opacity = '0', 500);
            setTimeout(() => els.loader.style.display = 'none', 1000);

        } catch(e) { console.error(e); }
    }

    // --- НОВАЯ ФУНКЦИЯ: СИНХРОНИЗАЦИЯ БАЛАНСА ---
    async function startBalanceSync() {
        setInterval(async () => {
            // Если открыта рулетка или попап, не обновляем, чтобы не отвлекать
            if (!els.modal.classList.contains('hidden') || !els.popup.classList.contains('hidden')) return;

            try {
                // Запрашиваем только данные пользователя для экономии трафика
                // Но так как у нас один эндпоинт /api/data, используем его
                const res = await fetch(`${API_URL}/data`, { method: 'POST', body: JSON.stringify({ user_id: userId, username }) });
                const data = await res.json();
                if(data.user) {
                    updateBalanceDisplay(data.user.balance);
                }
            } catch (e) {
                console.log("Ошибка синхронизации:", e);
            }
        }, 3000); // Проверяем каждые 3 секунды
    }

    window.sellItem = async function(invId, price) {
        if(!confirm(`Продать за ${price} монет?`)) return;
        
        updateBalanceDisplay(currentBalance + price);
        const itemEl = document.getElementById(`inv-item-${invId}`);
        if(itemEl) itemEl.remove();

        const res = await fetch(`${API_URL}/sell`, { 
            method: 'POST', 
            body: JSON.stringify({ user_id: userId, inv_id: invId, price: price }) 
        });
        
        const d = await res.json();
        if(d.status !== 'ok') {
            tg.showAlert("Ошибка продажи!");
            load();
        }
    };

    async function openCase(cid, price) {
        if(currentBalance < price) return tg.showAlert("Недостаточно денег!");
        
        updateBalanceDisplay(currentBalance - price);

        els.modal.classList.remove('hidden');
        els.tape.style.transition = 'none';
        els.tape.style.transform = 'translateX(0)';
        els.tape.innerHTML = '';

        const res = await fetch(`${API_URL}/open`, { method: 'POST', body: JSON.stringify({ user_id: userId, case_id: cid }) });
        const resD = await res.json();
        
        if(resD.error) { 
            els.modal.classList.add('hidden'); 
            load(); 
            return tg.showAlert(resD.error); 
        }

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
    startBalanceSync(); // ЗАПУСКАЕМ ТАЙМЕР
});