document.addEventListener('DOMContentLoaded', () => {
    const WEB_APP_URL = window.location.origin;
    const roller = document.getElementById('roller');
    const caseOpener = document.getElementById('case-opener');
    const caseSelection = document.getElementById('case-selection');
    const resultDisplay = document.getElementById('result-display');
    const closeRollerBtn = document.getElementById('close-roller');
    const openAnotherBtn = document.getElementById('open-another');
    const casesContainer = document.getElementById('cases-container');
    const inventoryList = document.getElementById('inventory-list');
    const loadingMessage = document.getElementById('loading-message');

    let CURRENT_USER_DATA = null;
    let ALL_ITEMS = []; // Все предметы для генерации рулетки
    let CURRENT_CASE = null;
    let USER_ID = null;
    let USER_USERNAME = "MemeLover";

    // Инициализация Telegram WebApp
    if (window.Telegram && window.Telegram.WebApp) {
        window.Telegram.WebApp.ready();
        const initData = window.Telegram.WebApp.initDataUnsafe;
        if (initData.user) {
            USER_ID = initData.user.id;
            USER_USERNAME = initData.user.username || initData.user.first_name;
        }
    }

    // --- 1. Основные функции API ---

    // Функция для получения всех данных (пользователь, баланс, кейсы, инвентарь)
    async function fetchData() {
        try {
            const response = await fetch(`${WEB_APP_URL}/api/data`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ user_id: USER_ID, username: USER_USERNAME })
            });

            if (!response.ok) throw new Error("Failed to fetch data from API");

            const data = await response.json();
            CURRENT_USER_DATA = data.user;
            ALL_ITEMS = data.case_items; // Все предметы для рулетки
            
            updateUI(data);
            createCaseButtons(data.cases);

        } catch (error) {
            console.error("Error fetching initial data:", error);
            loadingMessage.textContent = "Ошибка загрузки данных. Убедитесь, что бот запущен.";
        }
    }

    // Обновление UI (баланс, имя, инвентарь)
    function updateUI(data) {
        document.getElementById('username').textContent = data.user.username || 'Игрок';
        document.getElementById('balance').textContent = data.user.balance;
        
        // Обновление инвентаря
        inventoryList.innerHTML = '';
        data.inventory.forEach(item => {
            const div = document.createElement('div');
            div.className = `inventory-item rarity-${item.rarity}`;
            div.innerHTML = `<img src="${item.image_url}" alt="${item.name}"><p>${item.name}</p>`;
            inventoryList.appendChild(div);
        });

        // Скрываем сообщение о загрузке
        loadingMessage.classList.add('hidden');
    }
    
    // --- 2. Функции выбора кейсов ---
    
    function createCaseButtons(cases) {
        casesContainer.innerHTML = ''; // Очистка
        cases.forEach(caseItem => {
            const button = document.createElement('button');
            button.className = 'case-button';
            button.dataset.caseId = caseItem.id;
            button.innerHTML = `
                <img src="${caseItem.icon_url || 'https://i.imgur.com/default_case.png'}" alt="${caseItem.name}">
                <h4>${caseItem.name}</h4>
                <p>Открыть за ${caseItem.price} 💰</p>
            `;
            
            // Проверка, можно ли открыть
            if (CURRENT_USER_DATA && CURRENT_USER_DATA.balance < caseItem.price) {
                button.disabled = true;
            }
            
            button.addEventListener('click', () => startOpening(caseItem));
            casesContainer.appendChild(button);
        });
    }

    // --- 3. Функции открытия кейса и анимации ---

    function startOpening(caseItem) {
        CURRENT_CASE = caseItem;
        
        // Проверка баланса перед началом
        if (CURRENT_USER_DATA.balance < caseItem.price) {
            alert("Недостаточно средств!");
            return;
        }
        
        // Скрываем выбор, показываем рулетку
        caseSelection.classList.add('hidden');
        resultDisplay.classList.add('hidden');
        caseOpener.classList.remove('hidden');
        
        // Начальный звук открытия (опционально)
        // const openSound = new Audio('path/to/opening_sound.mp3');
        // openSound.play();

        // 1. Генерируем элементы для рулетки
        generateRollerItems();

        // 2. Отправляем запрос на открытие
        fetchDroppedItem(caseItem.id);
    }

    // Генерирует ленту предметов для прокрутки
    function generateRollerItems() {
        roller.innerHTML = '';
        const itemsToDisplay = 100; // Для плавной прокрутки нужно много предметов
        const visibleItems = 10;
        
        // Заполняем рулетку случайными предметами
        for (let i = 0; i < itemsToDisplay; i++) {
            // Выбираем случайный предмет из ВСЕХ (или только из этого кейса, если ALL_ITEMS фильтровать)
            const randomItem = ALL_ITEMS[Math.floor(Math.random() * ALL_ITEMS.length)];
            
            const itemElement = document.createElement('div');
            itemElement.className = `roller-item rarity-${randomItem.rarity}`;
            itemElement.innerHTML = `<img src="${randomItem.image_url}" alt="${randomItem.name}"><p>${randomItem.name}</p>`;
            roller.appendChild(itemElement);
        }

        // Устанавливаем начальное положение (чтобы центр был чистым)
        roller.style.transition = 'none';
        roller.style.transform = `translateX(0px)`;
    }

    // Запрос выпавшего предмета
    async function fetchDroppedItem(caseId) {
        try {
            const response = await fetch(`${WEB_APP_URL}/api/open`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ user_id: USER_ID, case_id: caseId })
            });
            
            if (!response.ok) throw new Error("API failed to open case or insufficient balance.");

            const data = await response.json();
            
            // 3. Запускаем анимацию прокрутки
            animateRoller(data.dropped);

        } catch (error) {
            console.error("Error opening case:", error);
            alert("Не удалось открыть кейс. Возможно, ошибка сервера или недостаточно средств.");
            // Возвращаемся к выбору
            caseOpener.classList.add('hidden');
            caseSelection.classList.remove('hidden');
            fetchData(); // Обновить данные
        }
    }

    // Функция анимации
    function animateRoller(droppedItem) {
        const rollerWidth = roller.offsetWidth;
        const itemWidth = 100 + 2; // Ширина элемента + margin
        const targetIndex = 94; // Целевая позиция (ближе к концу ленты)
        
        // 1. Находим нужный элемент в рулетке (для имитации)
        const items = roller.querySelectorAll('.roller-item');
        
        // Заменяем предмет на целевой позиции (для гарантии выигрыша)
        if (items[targetIndex]) {
            items[targetIndex].className = `roller-item rarity-${droppedItem.rarity}`;
            items[targetIndex].innerHTML = `<img src="${droppedItem.image_url}" alt="${droppedItem.name}"><p>${droppedItem.name}</p>`;
        }
        
        // 2. Рассчитываем конечную позицию
        // Смещение, чтобы целевой элемент оказался прямо под индикатором (50% окна)
        const offset = rollerWidth / 2 - (itemWidth / 2); 
        const targetPosition = targetIndex * itemWidth;
        const finalTransform = offset - targetPosition;

        // 3. Запускаем CSS-анимацию
        roller.style.transition = 'transform 6s cubic-bezier(0.05, 0.65, 0.1, 1.0)';
        roller.style.transform = `translateX(${finalTransform}px)`;

        // 4. После завершения анимации (6 секунд) показываем результат
        setTimeout(() => {
            showResult(droppedItem);
        }, 6500); // Немного больше, чем длительность transition
    }

    // --- 4. Отображение результатов ---

    function showResult(droppedItem) {
        caseOpener.classList.add('hidden');
        resultDisplay.classList.remove('hidden');
        
        document.getElementById('dropped-img').src = droppedItem.image_url;
        document.getElementById('dropped-name').textContent = droppedItem.name;
        document.getElementById('dropped-rarity').textContent = `Редкость: ${droppedItem.rarity}`;
        
        // Проигрывание звука
        if (droppedItem.sound_url) {
            const dropSound = new Audio(droppedItem.sound_url);
            dropSound.play().catch(e => console.error("Error playing sound:", e));
        }

        // Обновляем UI после выигрыша (баланс, инвентарь)
        fetchData();
    }
    
    // --- 5. Обработчики кнопок ---
    
    openAnotherBtn.addEventListener('click', () => {
        resultDisplay.classList.add('hidden');
        caseSelection.classList.remove('hidden');
    });

    closeRollerBtn.addEventListener('click', () => {
        caseOpener.classList.add('hidden');
        caseSelection.classList.remove('hidden');
    });

    // Запуск при загрузке страницы
    fetchData();
});