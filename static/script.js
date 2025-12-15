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
    let currentBalance = 0; // Локальная переменная для мгновенного обновления

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

    // Функция обновления отображения баланса
    function updateBalanceDisplay(newBalance) {
        currentBalance = newBalance;
        // Анимация числа
        els.bal.innerText = newBalance;
        // Можно добавить анимацию цвета, если изменился
    }

    async function load() {
        try {
            const res = await fetch(`${API_URL}/data`, { method: 'POST', body: JSON.stringify({ user_id: userId, username }) });
            const data = await res.json();
            allItems = data.case_items || [];
            
            if(data.user) {
                updateBalanceDisplay(data.user.balance);
            }
            
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
                d.id = `inv-item-${i.inv_id}`; // ID для удаления
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

    // МГНОВЕННАЯ ПРОДАЖА
    window.sellItem = async function(invId, price) {
        if(!confirm(`Продать за ${price} монет?`)) return;
        
        // 1. Оптимистичное обновление (сразу меняем интерфейс)
        updateBalanceDisplay(currentBalance + price);
        const itemEl = document.getElementById(`inv-item-${invId}`);
        if(itemEl) itemEl.remove();

        // 2. Отправляем запрос на сервер
        const res = await fetch(`${API_URL}/sell`, { 
            method: 'POST', 
            body: JSON.stringify({ user_id: userId, inv_id: invId, price: price }) 
        });
        
        const d = await res.json();
        if(d.status !== 'ok') {
            tg.showAlert("Ошибка продажи! Откат...");
            load(); // Если ошибка - перезагружаем все данные обратно
        }
    };

    async function openCase(cid, price) {
        if(currentBalance < price) return tg.showAlert("Недостаточно денег!");
        
        // Сразу списываем деньги визуально
        updateBalanceDisplay(currentBalance - price);

        els.modal.classList.remove('hidden');
        els.tape.style.transition = 'none';
        els.tape.style.transform = 'translateX(0)';
        els.tape.innerHTML = '';

        const res = await fetch(`${API_URL}/open`, { method: 'POST', body: JSON.stringify({ user_id: userId, case_id: cid }) });
        const resD = await res.json();
        
        if(resD.error) { 
            els.modal.classList.add('hidden'); 
            load(); // Возвращаем баланс, если ошибка
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
            
            // После закрытия кейса - полная синхронизация, чтобы предмет появился в инвентаре
            load();
        }, 5200);
    }

    document.getElementById('claim-btn').onclick = () => {
        els.popup.classList.add('hidden');
        els.audio.pause();
    };

    load();
});