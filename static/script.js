document.addEventListener('DOMContentLoaded', () => {
    const tg = window.Telegram.WebApp;
    tg.expand(); // Раскрываем на весь экран

    // --- КОНФИГУРАЦИЯ ---
    const API_URL = window.location.origin + '/api';
    const CARD_WIDTH = 100; // Ширина карточки в пикселях (из CSS)
    
    // Элементы DOM
    const els = {
        balance: document.getElementById('balance'),
        username: document.getElementById('username'),
        casesGrid: document.getElementById('cases-grid'),
        inventoryGrid: document.getElementById('inventory-grid'),
        leaderboardList: document.getElementById('leaderboard-list'),
        
        // Рулетка
        rouletteModal: document.getElementById('roulette-modal'),
        rouletteTape: document.getElementById('roulette-tape'),
        
        // Попап результата
        dropPopup: document.getElementById('drop-popup'),
        popupImg: document.getElementById('popup-img'),
        popupName: document.getElementById('popup-name'),
        popupRarity: document.getElementById('popup-rarity'),
        claimBtn: document.getElementById('claim-btn'),
        
        // Аудио
        audioPlayer: document.getElementById('audio-player'),
        tickSound: document.getElementById('tick-sound')
    };

    let userId = tg.initDataUnsafe?.user?.id || 12345; // Фолбек для теста в браузере
    let username = tg.initDataUnsafe?.user?.username || 'Tester';
    let allItems = []; // Кэш всех предметов для генерации фейков в рулетке

    // --- 1. ЗАГРУЗКА ДАННЫХ ---
    async function loadData() {
        try {
            const res = await fetch(`${API_URL}/data`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ user_id: userId, username: username })
            });
            const data = await res.json();
            
            updateUI(data);
            allItems = data.case_items || []; // Сохраняем для рулетки
            
        } catch (e) {
            console.error("Ошибка загрузки:", e);
        }
    }

    function updateUI(data) {
        // Обновляем шапку
        if(data.user) {
            els.balance.textContent = data.user.balance;
            els.username.textContent = data.user.username;
        }

        // Рендерим кейсы
        els.casesGrid.innerHTML = '';
        data.cases.forEach(c => {
            const div = document.createElement('div');
            div.className = 'case-card';
            div.innerHTML = `
                <img src="${c.icon_url}" class="case-img" onerror="this.src='https://placehold.co/100?text=CASE'">
                <div class="case-name">${c.name}</div>
                <div class="case-price">${c.price} 💰</div>
            `;
            div.onclick = () => openCase(c.id, c.price, data.user.balance);
            els.casesGrid.appendChild(div);
        });

        // Рендерим инвентарь
        els.inventoryGrid.innerHTML = '';
        if(data.inventory.length === 0) {
            els.inventoryGrid.innerHTML = '<div class="empty-msg">Пусто...</div>';
        } else {
            data.inventory.reverse().forEach(item => { // Новые сверху
                const div = document.createElement('div');
                div.className = `item-card rarity-${item.rarity}`;
                div.innerHTML = `
                    <img src="${item.image_url}" class="item-img">
                    <div class="item-name">${item.name}</div>
                `;
                els.inventoryGrid.appendChild(div);
            });
        }

        // Лидерборд
        els.leaderboardList.innerHTML = '';
        data.leaderboard.forEach((u, index) => {
            const div = document.createElement('div');
            div.style.padding = '5px';
            div.style.borderBottom = '1px solid #333';
            div.innerHTML = `<b>#${index+1}</b> ${u.username} — <span>${u.balance} 💰</span>`;
            els.leaderboardList.appendChild(div);
        });
    }

    // --- 2. ЛОГИКА ОТКРЫТИЯ (Рулетка) ---
    async function openCase(caseId, price, balance) {
        if (balance < price) {
            tg.showAlert("Недостаточно денег! Иди работай!");
            return;
        }

        // 1. Показываем модалку рулетки
        els.rouletteModal.classList.add('active');
        els.rouletteModal.classList.remove('hidden');
        els.rouletteTape.style.transition = 'none';
        els.rouletteTape.style.transform = 'translateX(0px)';
        els.rouletteTape.innerHTML = ''; // Чистим ленту

        // 2. Делаем запрос к серверу (узнаем результат заранее)
        try {
            const res = await fetch(`${API_URL}/open`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ user_id: userId, case_id: caseId })
            });
            
            const result = await res.json();
            
            if (result.error) {
                tg.showAlert(result.error);
                els.rouletteModal.classList.remove('active');
                return;
            }

            // 3. Генерируем ленту
            // Нам нужно, чтобы выигрышный предмет был на определенной позиции (например, 50-й)
            const WIN_INDEX = 50; 
            const TOTAL_ITEMS = 60;
            
            // Заполняем ленту фейками
            for (let i = 0; i < TOTAL_ITEMS; i++) {
                let item = allItems[Math.floor(Math.random() * allItems.length)];
                
                // Вставляем ВЫИГРЫШНЫЙ предмет на нужную позицию
                if (i === WIN_INDEX) {
                    item = result.dropped;
                }

                const div = document.createElement('div');
                div.className = `roulette-item rarity-${item.rarity}`;
                div.innerHTML = `<img src="${item.image_url}">`;
                els.rouletteTape.appendChild(div);
            }

            // 4. Запускаем анимацию
            // Небольшая задержка перед стартом
            setTimeout(() => {
                // Вычисляем смещение. 
                // (WIN_INDEX * CARD_WIDTH) - (Половина экрана) + (Половина карточки) + (Рандом внутри карточки для реализма)
                const windowWidth = document.querySelector('.roulette-window').offsetWidth;
                const randomOffset = Math.floor(Math.random() * 40) - 20; // +/- 20px
                const scrollPosition = (WIN_INDEX * CARD_WIDTH) - (windowWidth / 2) + (CARD_WIDTH / 2) + randomOffset;
                
                els.rouletteTape.style.transition = 'transform 6s cubic-bezier(0.15, 0.85, 0.15, 1)'; // Эффект замедления
                els.rouletteTape.style.transform = `translateX(-${scrollPosition}px)`;
                
                // Проигрываем тиканье (упрощенно - один звук старта)
                // В идеале нужно синхронизировать тиканье с прохождением карточек, но это сложно для JS без библиотек
                // Просто проиграем звук вращения
                // els.tickSound.play(); 

            }, 100);

            // 5. Когда анимация закончилась (через 6 секунд)
            setTimeout(() => {
                showResult(result.dropped);
                loadData(); // Обновляем баланс и инвентарь на фоне
            }, 6200);

        } catch (e) {
            console.error(e);
            els.rouletteModal.classList.remove('active');
        }
    }

    // --- 3. ПОКАЗ РЕЗУЛЬТАТА ---
    function showResult(item) {
        els.rouletteModal.classList.remove('active'); // Скрываем рулетку
        els.dropPopup.classList.remove('hidden');
        setTimeout(() => els.dropPopup.classList.add('active'), 10); // Плавное появление

        // Заполняем данные
        els.popupImg.src = item.image_url;
        els.popupName.textContent = item.name;
        els.popupRarity.textContent = item.rarity;
        els.popupRarity.className = `rarity-${item.rarity}`; // Цвет текста

        // Звук выпадения (ИМЯ ПРЕДМЕТА)
        if (item.sound_url) {
            els.audioPlayer.src = item.sound_url;
            els.audioPlayer.play().catch(e => console.log("Auto-play blocked:", e));
        }
    }

    // Кнопка "ЗАБРАТЬ"
    els.claimBtn.onclick = () => {
        els.dropPopup.classList.remove('active');
        setTimeout(() => els.dropPopup.classList.add('hidden'), 300);
        els.audioPlayer.pause();
        els.audioPlayer.currentTime = 0;
    };

    // Запуск
    loadData();
});