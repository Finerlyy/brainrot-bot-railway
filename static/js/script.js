
function formatBalance(num) {
    if (num >= 1000000) return (num / 1000000).toFixed(1) + 'M';
    if (num >= 1000) return (num / 1000).toFixed(1) + 'k';
    return num.toLocaleString();
}

// ЦВЕТА И МНОЖИТЕЛИ МУТАЦИЙ
const MUTATION_COLORS = {
    'Gold': '#FFD700',
    'Diamond': '#b9f2ff',
    'Bloodrot': '#ff3333',
    'Candy': '#ff69b4',
    'Rainbow': '#cc33ff', 
    'Galaxy': '#9933ff'
};

const MUTATION_MULTIPLIERS = {
    'Gold': 1.1,
    'Diamond': 1.2,
    'Bloodrot': 1.5,
    'Candy': 1.5,
    'Rainbow': 2.0,
    'Galaxy': 3.0
};

const RARITY_ORDER = {'Secret': 7, 'Immortal': 6, 'Legendary': 5, 'Mythical': 4, 'Rare': 3, 'Uncommon': 2, 'Common': 1};
const RARITY_COLORS_HEX = {'Common':'#666','Uncommon':'#5e98d9','Rare':'#4b69ff','Mythical':'#d32ce6','Legendary':'#ff9900','Immortal':'#00ffff','Secret':'#ff0000'};
const VISUAL_WEIGHTS = {'Common': 1000, 'Uncommon': 500, 'Rare': 200, 'Mythical': 50, 'Legendary': 10, 'Immortal': 3, 'Secret': 1};
const MUT_EMOJIS = {'Gold':'🥇','Diamond':'💎','Bloodrot':'🩸','Candy':'🍬','Rainbow':'🌈','Galaxy':'🌌'};

let selGameType = 'rps';
let activeGameId = null;
let wagerType = 'money';
let selWagerItem = null;

window.switchTab=function(t){
    document.querySelectorAll('.tab-content').forEach(e=>e.classList.remove('active'));
    document.querySelectorAll('.nav-btn').forEach(e=>e.classList.remove('active'));
    document.getElementById(`tab-${t}`).classList.add('active');
    if(t !== 'profile') document.getElementById('back-to-my-profile').style.display = 'none';
    const navBtn = document.querySelector(`.nav-btn[onclick="switchTab('${t}')"]`);
    if(navBtn) navBtn.classList.add('active');
}

window.closeModal=function(id){document.getElementById(id).classList.remove('active'); document.getElementById(id).classList.add('hidden');}

// --- УНИВЕРСАЛЬНАЯ ФУНКЦИЯ СОРТИРОВКИ ---
function sortItems(items) {
    return items.sort((a,b) => {
        let rA = RARITY_ORDER[a.rarity] || 0;
        let rB = RARITY_ORDER[b.rarity] || 0;
        if (rB !== rA) return rB - rA; // Сначала по редкости (по убыванию)
        return b.price - a.price; // Потом по цене
    });
}

// --- ГЕНЕРАЦИЯ HTML КАРТОЧКИ ПРЕДМЕТА ---
function createItemCardHTML(item, isClickable=true, onClickAction=null) {
    const div = document.createElement('div'); 
    div.className = `item-card rarity-${item.rarity}`;
    
    let mutsHtml = '';
    // Проверяем мутации
    let mList = item.muts_list || [];
    if(!mList.length && item.mutations && Array.isArray(item.mutations)) mList = item.mutations;
    else if(!mList.length && typeof item.mutations === 'string' && item.mutations) mList = item.mutations.split(',').filter(x=>x);

    if(mList.length > 0) {
        div.classList.add('mutated');
        const mainMut = mList[0];
        const color = MUTATION_COLORS[mainMut] || '#FFD700';
        div.style.setProperty('--glow-color', color);
        
        mutsHtml = '<div class="mutation-badges">';
        mList.forEach(m => { mutsHtml += `<span class="mut-badge">${MUT_EMOJIS[m] || m}</span>`; });
        mutsHtml += '</div>';
    }
    
    // Цена продажи или базовая цена
    let priceDisplay = item.sell_price ? item.sell_price : item.price;

    let sellBtnHtml = '';
    if(item.sell_price && isClickable && !onClickAction) {
        sellBtnHtml = `<button class="sell-btn" onclick="openSellModal(${item.item_id}, '${mList.join(',')}')">Продать: <span>⭐️ ${formatBalance(priceDisplay)}</span></button>`;
    } else {
        sellBtnHtml = `<div class="case-price" style="margin-top:5px;">⭐️ ${formatBalance(item.price)}</div>`;
    }

    let qtyHtml = item.quantity > 0 ? `<span class="item-quantity">x${item.quantity}</span>` : '';

    div.innerHTML = `${mutsHtml}${qtyHtml}<img src="${item.image_url}" class="item-img"><div class="case-name">${item.name}</div>${sellBtnHtml}`;

    if(isClickable) {
        div.onclick = (e) => {
            if(e.target.closest('.sell-btn')) return;
            if(onClickAction) onClickAction(item);
            else viewItemDetails(item);
        };
    }
    return div;
}


document.addEventListener('DOMContentLoaded', () => {
    const tg = window.Telegram.WebApp; tg.expand();
    const API = window.location.origin + '/api';
    let userId = tg.initDataUnsafe?.user?.id || 0;
    let username = tg.initDataUnsafe?.user?.username || 'Guest';
    let photoUrl = tg.initDataUnsafe?.user?.photo_url || '';
    
    let allItems=[], inventory=[], allItemsSorted=[], currentBal=0;
    let selectedCase={id:0, price:0, keys: 0}, openCount=1;
    let upgMy=null, upgTarget=null;
    let sellingItem=null, sellCount=1;

    const el = {
        bal: document.getElementById('balance'),
        cases: document.getElementById('cases-grid'),
        inv: document.getElementById('inventory-grid'),
        gamesList: document.getElementById('games-list'),
        gameUi: document.getElementById('active-game-ui'),
        gamesLobby: document.getElementById('games-lobby'),
        gameControls: document.getElementById('game-controls'),
        gameStatus: document.getElementById('game-status-text'),
        gameSpinner: document.getElementById('game-loading-spinner'),
        gameExitBtn: document.getElementById('game-exit-btn'),
        gameCancelBtn: document.getElementById('game-cancel-btn'),
        
        loader:document.getElementById('loading-screen'), openModal:document.getElementById('open-modal'), mPrice:document.getElementById('modal-case-price'), slider:document.getElementById('case-slider'), sliderVal:document.getElementById('slider-count'), popup:document.getElementById('drop-popup'), dropGrid:document.getElementById('drop-results-grid'), audio:document.getElementById('audio-player'), selModal:document.getElementById('select-modal'), selGrid:document.getElementById('select-grid'), uLeft:document.getElementById('u-slot-left'), uRight:document.getElementById('u-slot-right'), uBtn:document.getElementById('upgrade-btn'), uChance:document.getElementById('u-chance'), resultLayer:document.getElementById('resultLayer'), resultText:document.getElementById('resultText'), sellModal:document.getElementById('sell-modal'), sellName:document.getElementById('sell-item-name'), sellImg:document.getElementById('sell-item-img'), sellOwned:document.getElementById('sell-owned-count'), sellSlider:document.getElementById('sell-slider'), sellSliderVal:document.getElementById('sell-slider-count'), sellTotalBtn:document.getElementById('total-sell-price'), confirmSellBtn:document.getElementById('confirm-sell-btn'), sellSliderContainer:document.getElementById('sell-slider-container'), multiBox: document.getElementById('multi-roulette-container'), btnFast: document.getElementById('btn-fast'), btnSpin: document.getElementById('btn-spin'), profUser: document.getElementById('profile-username'), profBal: document.getElementById('prof-balance'), profNet: document.getElementById('prof-networth'), profCases: document.getElementById('prof-cases'), profDays: document.getElementById('prof-days'), 
        profInventory: document.getElementById('prof-inventory'), 
        profInvContainer: document.getElementById('prof-inv-container'),
        btnViewProfInv: document.getElementById('btn-view-prof-inv'),
        profBestContainer: document.getElementById('prof-best-container'),
        profBestDrop: document.getElementById('prof-best-drop'),
        profAvatar: document.getElementById('prof-avatar'), lbList: document.getElementById('leaderboard-list'), backBtn: document.getElementById('back-to-my-profile'),
        
        upgCircleFg: document.getElementById('upgrade-circle-fg'),
        wagerMoneyBlock: document.getElementById('wager-money-block'),
        wagerItemBlock: document.getElementById('wager-item-block'),
        selWagerItemDiv: document.getElementById('selected-wager-item'),
        btnWagerMoney: document.getElementById('btn-wager-money'),
        btnWagerItem: document.getElementById('btn-wager-item'),
        
        detModal: document.getElementById('details-modal'),
        detName: document.getElementById('det-item-name'),
        detImg: document.getElementById('det-item-img'),
        detBase: document.getElementById('det-base-price'),
        detMuts: document.getElementById('det-mutations-block'),
        detFinal: document.getElementById('det-final-price'),
        detRarity: document.getElementById('det-rarity-badge')
    };

    function upBal(n){ if(n!==undefined){ currentBal=n; el.bal.innerText = formatBalance(n); } }

    function renderAll(d, isInitial) {
        if(d.user) {
            upBal(d.user.balance);
            if(document.getElementById('back-to-my-profile').style.display === 'none') {
                renderProfile(d.user, d.inventory, true, d.user.best_item);
            }
        }
        const casesJSON = JSON.stringify(d.cases);
        if (isInitial || el.cases.dataset.hash !== casesJSON) {
            el.cases.dataset.hash = casesJSON;
            el.cases.innerHTML=''; 
            d.cases.forEach(c=>{
                const div=document.createElement('div'); div.className='case-card';
                let keyBadge = ''; if(c.keys && c.keys > 0) { keyBadge = `<div class="keys-badge">🔑 ${c.keys}</div>`; }
                div.innerHTML=`${keyBadge}<img src="${c.icon_url}" class="case-img"><div class="case-name">${c.name}</div><div class="case-price">⭐️ ${formatBalance(c.price)}</div>`;
                div.onclick=()=>{selectedCase=c; showOpenModal();}; el.cases.appendChild(div);
            });
        }
        
        d.inventory = sortItems(d.inventory);
        const invJSON = JSON.stringify(d.inventory);
        if (isInitial || el.inv.dataset.hash !== invJSON) {
            el.inv.dataset.hash = invJSON;
            el.inv.innerHTML=''; 
            if(!d.inventory.length) el.inv.innerHTML="<p style='color:#666;grid-column:1/-1;text-align:center;margin-top:20px;font-size:0.9rem'>Инвентарь пуст</p>";
            d.inventory.forEach(i=>{
                el.inv.appendChild(createItemCardHTML(i));
            });
        }
        if(d.leaderboard) {
            el.lbList.innerHTML = '';
            d.leaderboard.forEach((u, idx) => {
                const rankClass = idx < 3 ? `lb-rank-${idx+1}` : '';
                const avatarHtml = u.photo_url ? `<img src="${u.photo_url}" class="lb-avatar">` : '<span class="lb-avatar" style="background:#444;display:inline-block;text-align:center;line-height:35px;font-size:18px;">👤</span>';
                el.lbList.innerHTML += `<div class="leaderboard-item" onclick="viewProfile(${u.tg_id})"><div><span class="lb-rank ${rankClass}">#${idx+1}</span>${avatarHtml}<span>${u.username}</span></div><span style="color:#FFD700;font-weight:bold">${formatBalance(u.net_worth)} <span class="star-icon">⭐️</span></span></div>`;
            });
        }
    }
    
    // --- ДЕТАЛИ ПРЕДМЕТА ---
    window.viewItemDetails = (item) => {
        el.detName.innerText = item.name;
        el.detImg.src = item.image_url;
        el.detBase.innerText = formatBalance(item.price);
        el.detRarity.innerText = item.rarity;
        el.detRarity.style.color = RARITY_COLORS_HEX[item.rarity] || '#fff';
        el.detRarity.style.border = `1px solid ${RARITY_COLORS_HEX[item.rarity] || '#fff'}`;
        el.detRarity.style.background = `rgba(0,0,0,0.5)`;

        let rawVal = item.price;
        let muts = item.muts_list || [];
        if(!muts.length && item.mutations) muts = item.mutations.split(',');

        el.detMuts.innerHTML = '';
        if (muts && muts.length > 0) {
            muts.forEach(m => {
                if(!m) return;
                const mult = MUTATION_MULTIPLIERS[m] || 1.0;
                rawVal *= mult;
                const emoji = MUT_EMOJIS[m] || '';
                const color = MUTATION_COLORS[m] || '#fff';
                const row = document.createElement('div');
                row.className = 'info-row';
                row.innerHTML = `<span class="mut-row" style="color:${color}">${emoji} ${m}</span><span class="info-value" style="color:${color}">x${mult.toFixed(1)}</span>`;
                el.detMuts.appendChild(row);
            });
        } else {
             el.detMuts.innerHTML = '<div class="info-row"><span class="info-label">Мутации:</span><span class="info-value" style="color:#666">Нет</span></div>';
        }
        el.detFinal.innerText = formatBalance(Math.floor(rawVal));
        el.detModal.classList.remove('hidden');
    }

    async function load(){
        try {
            const res=await fetch(`${API}/data`,{method:'POST', body:JSON.stringify({user_id:userId, username, photo_url: photoUrl})});
            const d=await res.json();
            allItems=d.case_items||[]; inventory=d.inventory||[]; allItemsSorted=d.all_items||[];
            renderAll(d, true);
            updateGamesList();
            pollGameStatus();
            setTimeout(()=>el.loader.style.display='none',500);
        } catch(e){ console.error(e); }
    }

    // --- POLLING ---
    async function autoUpdate(){
        if(el.popup.classList.contains('active') || !el.openModal.classList.contains('hidden') || el.loader.style.display !== 'none') return;
        if(activeGameId) pollGameStatus(); else updateGamesList(); 
        try {
            const res=await fetch(`${API}/data`,{method:'POST', body:JSON.stringify({user_id:userId, username})});
            const d=await res.json();
            if(d.error) return;
            allItems=d.case_items||[]; inventory=d.inventory||[]; allItemsSorted=d.all_items||[];
            renderAll(d, false);
        } catch(e){ console.error("AutoUpdate Error", e); }
    }
    setInterval(autoUpdate, 2000); 

    // --- GAME LOGIC ---
    window.showCreateGameModal = () => { document.getElementById('create-game-modal').classList.remove('hidden'); setWagerType('money'); }
    window.setWagerType = (type) => {
        wagerType = type;
        if(type === 'money') {
            el.btnWagerMoney.classList.add('active'); el.btnWagerItem.classList.remove('active');
            el.wagerMoneyBlock.style.display = 'block'; el.wagerItemBlock.style.display = 'none';
        } else {
            el.btnWagerMoney.classList.remove('active'); el.btnWagerItem.classList.add('active');
            el.wagerMoneyBlock.style.display = 'none'; el.wagerItemBlock.style.display = 'block';
        }
    }
    window.createGame = async () => {
        const amount = parseInt(document.getElementById('wager-amount').value);
        let payload = {user_id: userId, game_type: selGameType};
        if(wagerType === 'money') { payload.wager_type = 'balance'; payload.wager_amount = amount; } 
        else {
            if(!selWagerItem) return tg.showAlert("Выберите предмет!");
            payload.wager_type = 'item'; payload.wager_item_id = selWagerItem.item_id; payload.wager_amount = 0;
        }
        try {
            const res = await fetch(`${API}/games/create`, { method: 'POST', body: JSON.stringify(payload) });
            const d = await res.json();
            if(d.status === 'ok') { closeModal('create-game-modal'); pollGameStatus(); } else tg.showAlert("Ошибка: " + d.error);
        } catch(e) { console.error(e); }
    }
    async function updateGamesList() {
        if(activeGameId) return; 
        try {
            const res = await fetch(`${API}/games/list`, {method:'POST'});
            const d = await res.json();
            el.gamesList.innerHTML = '';
            if(d.games.length === 0) el.gamesList.innerHTML = "<p style='color:#666;text-align:center;margin-top:20px;'>Нет активных игр</p>";
            d.games.forEach(g => {
                if(g.host_id === userId || g.guest_id === userId) { activeGameId = g.id; renderActiveGame(g); return; }
                let icon = g.game_type === 'rps' ? '✂️' : '🎲';
                let wager = g.wager_type === 'balance' ? `${g.wager_amount} ⭐️` : `📦 ${g.item_name}`;
                let imgHtml = g.wager_type === 'item' ? `<img src="${g.item_img}" style="width:30px;height:30px;vertical-align:middle;border-radius:5px;"> ` : '';
                el.gamesList.innerHTML += `<div class="game-card"><div style="display:flex;align-items:center"><span class="game-type-icon">${icon}</span><div><div style="font-weight:700">${g.host_name}</div><small style="color:#aaa">${imgHtml}${wager}</small></div></div><button class="main-action-btn" style="width:auto;padding:8px 20px;font-size:0.8rem;" onclick="joinGame(${g.id})">ИГРАТЬ</button></div>`;
            });
        } catch(e) {}
    }
    window.joinGame = async (gid) => {
        try {
            const res = await fetch(`${API}/games/join`, {method:'POST', body:JSON.stringify({user_id:userId, game_id:gid})});
            const d = await res.json();
            if(d.status === 'ok') { activeGameId = gid; pollGameStatus(); } else tg.showAlert(d.error);
        } catch(e){}
    }
    async function pollGameStatus() {
        try {
            const res = await fetch(`${API}/games/status`, {method:'POST', body:JSON.stringify({user_id:userId})});
            const d = await res.json();
            if(d.game) { activeGameId = d.game.id; renderActiveGame(d.game); } else { if(activeGameId) { activeGameId = null; exitGame(); } }
        } catch(e){}
    }
    function renderActiveGame(game) {
        el.gamesLobby.style.display = 'none'; el.gameUi.style.display = 'flex';
        let isHost = (game.host_tg_id === userId);
        let myMove = isHost ? game.host_move : game.guest_move;
        let oppName = isHost ? (game.guest_name || "Ожидание...") : game.host_name;
        let wagerText = game.wager_type === 'balance' ? `${game.wager_amount} ⭐` : `📦 ${game.item_name}`;
        el.gameSpinner.style.display = 'none'; el.gameControls.innerHTML = ''; el.gameCancelBtn.style.display = 'none'; el.gameExitBtn.style.display = 'block';
        if (game.status === 'open') {
            el.gameStatus.innerHTML = `Ожидание соперника...<br><small style='color:#888;font-weight:400'>Ставка: ${wagerText}</small>`;
            el.gameSpinner.style.display = 'block';
            if(isHost) el.gameCancelBtn.style.display = 'block'; 
            el.gameExitBtn.style.display = 'none'; 
        } else if (game.status === 'playing') {
            if (!myMove) {
                el.gameStatus.innerHTML = `Твой ход!<br><small style='color:#aaa'>Против: ${oppName}</small>`;
                if(game.game_type === 'rps') {
                    el.gameControls.innerHTML = `<button class="move-btn" onclick="sendMove('rock')">🪨</button><button class="move-btn" onclick="sendMove('scissors')">✂️</button><button class="move-btn" onclick="sendMove('paper')">📄</button>`;
                } else {
                    if (isHost) el.gameControls.innerHTML = `<button class="move-btn" onclick="sendMove('1')">1</button><button class="move-btn" onclick="sendMove('2')">2</button>`;
                    else el.gameControls.innerHTML = `<button class="move-btn" onclick="sendMove('odd')">Нечет</button><button class="move-btn" onclick="sendMove('even')">Чет</button>`;
                }
            } else {
                el.gameStatus.innerHTML = `Ждем ход соперника...<br><small style='color:#aaa'>Против: ${oppName}</small>`;
                el.gameSpinner.style.display = 'block';
                el.gameExitBtn.style.display = 'none'; 
            }
        } else if (game.status === 'finished') {
            let winText;
            if(game.winner_id === 0) winText = "🤝 НИЧЬЯ";
            else if((isHost && game.winner_id === game.host_id) || (!isHost && game.winner_id === game.guest_id)) winText = "🏆 ТЫ ВЫИГРАЛ!";
            else winText = "💀 ТЫ ПРОИГРАЛ";
            el.gameStatus.innerHTML = `${winText}<br><small style='color:#aaa'>Против: ${oppName}</small>`;
            el.gameExitBtn.style.display = 'block';
        }
    }
    window.sendMove = async (mv) => { await fetch(`${API}/games/move`, {method:'POST', body:JSON.stringify({user_id:userId, game_id:activeGameId, move:mv})}); pollGameStatus(); }
    window.exitGame = async () => { if(activeGameId) try { await fetch(`${API}/games/cancel`, {method:'POST', body:JSON.stringify({user_id:userId, game_id:activeGameId})}); } catch(e) {}; el.gameUi.style.display = 'none'; el.gamesLobby.style.display = 'block'; activeGameId = null; updateGamesList(); }
    window.cancelActiveGame = async () => { if(!confirm("Отменить игру и вернуть ставку?")) return; try { await fetch(`${API}/games/cancel`, {method:'POST', body:JSON.stringify({user_id:userId, game_id:activeGameId})}); exitGame(); } catch(e) {} }

    function renderProfile(user, inventoryData, isMe, bestItem = null) {
        el.profUser.innerText = user.username;
        el.profBal.innerText = formatBalance(user.balance);
        el.profNet.innerText = formatBalance(user.net_worth);
        el.profCases.innerText = user.cases_opened;
        const regDate = new Date(user.reg_date);
        const diffTime = Math.abs(new Date() - regDate);
        const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24)); 
        el.profDays.innerText = diffDays;
        
        if(user.photo_url) el.profAvatar.innerHTML = `<img src="${user.photo_url}">`;
        else el.profAvatar.innerHTML = '👤';
        
        // --- Рендер Лучшего Дропа ---
        if (bestItem) {
             el.profBestDrop.innerHTML = '';
             // Создаем карточку, но не кликабельную для действия (просто просмотр)
             const card = createItemCardHTML({
                 name: bestItem.name,
                 price: bestItem.price,
                 image_url: bestItem.image_url,
                 rarity: bestItem.rarity,
                 quantity: 0 // Скрываем количество
             }, true, null); // true = кликабельно для просмотра деталей
             
             // Убираем кнопку продажи из HTML карточки, если она там есть (хотя quantity 0 должно скрыть)
             card.innerHTML = card.innerHTML.replace(/<button.*button>/, '');
             el.profBestDrop.appendChild(card);
        } else {
             el.profBestDrop.innerHTML = '<div style="text-align:center; color:#555; padding:10px; font-size:0.9rem;">Нет предметов</div>';
        }

        el.profInventory.innerHTML = '';
        el.profInventory.style.display = 'none'; // Скрываем сетку по умолчанию

        if(inventoryData && inventoryData.length > 0) {
            inventoryData = sortItems(inventoryData);
            inventoryData.forEach(item => {
                el.profInventory.appendChild(createItemCardHTML(item, true, null));
            });
        } else {
            el.profInventory.innerHTML = '<div style="text-align:center; color:#555; padding:20px; grid-column:1/-1;">Нет предметов</div>';
        }

        if(isMe) {
            el.backBtn.style.display = 'none';
            el.profInvContainer.style.display = 'none'; // В своем профиле скрываем кнопку "Посмотреть инвентарь" (он есть в табе)
            el.profBestContainer.style.display = 'block'; // Показываем лучший дроп
        } else {
            el.backBtn.style.display = 'block';
            el.profInvContainer.style.display = 'block'; // Показываем блок с кнопкой
            el.btnViewProfInv.style.display = 'block'; // Показываем кнопку
            el.profBestContainer.style.display = 'block'; // Показываем лучший дроп и у чужого
        }
    }
    
    // Обработчик кнопки "Посмотреть инвентарь"
    el.btnViewProfInv.onclick = () => {
        el.profInventory.style.display = 'grid'; // Показываем сетку
        el.btnViewProfInv.style.display = 'none'; // Скрываем кнопку
    };

    window.viewProfile = async (targetId) => {
        if(targetId == userId) { switchTab('profile'); return; }
        el.loader.style.display = 'flex';
        try {
            const res = await fetch(`${API}/profile`, {method: 'POST', body: JSON.stringify({target_id: targetId})});
            const d = await res.json();
            if(d.profile) { 
                renderProfile(d.profile, d.profile.inventory, false, d.profile.best_item); 
                switchTab('profile'); 
            }
        } catch(e) { console.error(e); }
        el.loader.style.display = 'none';
    }

    window.openSellModal=(itemId, muts)=>{
        sellingItem = inventory.find(i => i.item_id === itemId && (i.mutations === muts || (!i.mutations && !muts)));
        if(!sellingItem) return;
        el.sellName.innerText = sellingItem.name;
        el.sellImg.src = sellingItem.image_url;
        el.sellOwned.innerText = sellingItem.quantity;
        if(sellingItem.quantity === 1) { el.sellSliderContainer.style.display = 'none'; sellCount = 1; } 
        else { el.sellSliderContainer.style.display = 'block'; el.sellSlider.max = sellingItem.quantity; el.sellSlider.value = 1; sellCount = 1; }
        updateSellSlider(sellCount);
        el.sellModal.classList.remove('hidden');
    }
    window.updateSellSlider=(v)=>{ sellCount = parseInt(v); el.sellSliderVal.innerText = sellCount; el.sellTotalBtn.innerText = formatBalance(sellingItem.sell_price * sellCount); }
    el.confirmSellBtn.onclick = async() => {
        if(!sellingItem) return;
        const totalPrice = sellingItem.sell_price * sellCount;
        el.sellModal.classList.add('hidden');
        upBal(currentBal + totalPrice);
        try { 
            await fetch(`${API}/sell_batch`,{method:'POST',body:JSON.stringify({
                user_id:userId, 
                item_id:sellingItem.item_id, 
                count:sellCount, 
                price_per_item:sellingItem.sell_price,
                mutations: sellingItem.muts_list
            })}); 
            load(); 
        } catch(e) { load(); }
    }

    window.sellAllItems = async () => {
        if(inventory.length === 0) return tg.showAlert("Инвентарь пуст!");
        if(!confirm("Вы точно хотите продать ВЕСЬ инвентарь?")) return;
        el.loader.style.display = 'flex';
        try {
            const res = await fetch(`${API}/sell_all`, {method: 'POST', body: JSON.stringify({user_id: userId})});
            const d = await res.json();
            if(d.status === 'ok') { tg.showAlert(`Продано на ${formatBalance(d.total)} звезд!`); load(); } 
            else { tg.showAlert("Ошибка продажи"); }
        } catch(e) { console.error(e); }
        el.loader.style.display = 'none';
    }

    function getWeightedRandomItem(itemsInCase) {
        const pool = (itemsInCase && itemsInCase.length > 0) ? itemsInCase : allItemsSorted;
        let totalWeight = 0; const weightedList = [];
        pool.forEach(item => { const w = VISUAL_WEIGHTS[item.rarity] || 100; totalWeight += w; weightedList.push({item, weight: w}); });
        let random = Math.random() * totalWeight;
        for(const entry of weightedList) { if(random < entry.weight) return entry.item; random -= entry.weight; }
        return pool[0];
    }

    window.showOpenModal=()=>{ el.multiBox.style.display = 'none'; el.multiBox.innerHTML = ''; el.btnFast.disabled = false; el.btnSpin.disabled = false; el.slider.disabled = false; el.slider.value = 1; updateSlider(1); el.openModal.classList.remove('hidden'); }
    window.updateSlider=(v)=>{ openCount=parseInt(v); el.sliderVal.innerText=openCount; if(selectedCase.keys >= openCount) el.mPrice.innerHTML = `<span style="color:#33ff33">БЕСПЛАТНО (Ключи: ${selectedCase.keys})</span>`; else el.mPrice.innerHTML = `Цена: <span class="star-icon">⭐️</span> ${formatBalance(selectedCase.price*openCount)}`; }

    async function runOpenCase(mode) {
        const price = selectedCase.price * openCount;
        if(selectedCase.keys < openCount && currentBal < price) return tg.showAlert("Мало звезд!");
        el.btnFast.disabled = true; el.btnSpin.disabled = true; el.slider.disabled = true;
        try {
            const res = await fetch(`${API}/open`,{method:'POST',body:JSON.stringify({user_id:userId, case_id:selectedCase.id, count:openCount})});
            const d=await res.json();
            if(d.error){ el.btnFast.disabled = false; el.btnSpin.disabled = false; el.slider.disabled = false; return tg.showAlert(d.error); }
            if(!d.used_keys) { upBal(currentBal - price); } else { selectedCase.keys -= openCount; }
            if (mode === 'fast') { el.openModal.classList.add('hidden'); showResults(d.dropped); } 
            else { el.multiBox.style.display = 'block'; el.multiBox.innerHTML = ''; d.dropped.forEach((winItem, idx) => { createRouletteRow(winItem, idx); }); setTimeout(() => { el.openModal.classList.add('hidden'); showResults(d.dropped); }, 5500); }
        } catch(e) { console.error(e); load(); }
    }
    el.btnFast.onclick = () => runOpenCase('fast'); el.btnSpin.onclick = () => runOpenCase('spin');

    function createRouletteRow(winItem, index) {
        const row = document.createElement('div'); row.className = 'case-roulette-row';
        const line = document.createElement('div'); line.className = 'roulette-center-line';
        const track = document.createElement('div'); track.className = 'roulette-track';
        const WIN_INDEX = 29; 
        const itemsInCase = allItemsSorted.filter(i => i.case_id === selectedCase.id);
        for(let i=0; i<45; i++) {
            let item = (i === WIN_INDEX) ? winItem : getWeightedRandomItem(itemsInCase);
            const card = document.createElement('div'); card.className = `roulette-card rarity-${item.rarity}`;
            let imgUrl = item.image_url; if(item.rarity === 'Secret') imgUrl = 'https://cdn-icons-png.flaticon.com/512/5726/5726678.png'; 
            card.innerHTML = `<img src="${imgUrl}">`; track.appendChild(card);
        }
        row.appendChild(line); row.appendChild(track); el.multiBox.appendChild(row);
        const CARD_WIDTH = 100; const CARD_GAP = 10; const UNIT_WIDTH = CARD_WIDTH + CARD_GAP; 
        const containerWidth = el.multiBox.clientWidth || 350; const centerOfContainer = containerWidth / 2;
        const centerOfWinningCard = (UNIT_WIDTH * WIN_INDEX) + (UNIT_WIDTH / 2);
        const randomOffset = Math.floor(Math.random() * 70) - 35;
        const scrollAmount = centerOfWinningCard - centerOfContainer + randomOffset;
        setTimeout(() => { track.style.transition = "transform 5s cubic-bezier(0.1, 0, 0.2, 1)"; track.style.transform = `translateX(-${scrollAmount}px)`; }, 50 + (index * 50));
    }

    function showResults(items){
        el.popup.classList.remove('hidden'); el.popup.classList.add('active');
        el.dropGrid.innerHTML=''; el.dropGrid.className = items.length > 1 ? 'drop-grid multi' : 'drop-grid single';
        document.getElementById('drop-title').innerText = "🎉 ВЫПАЛО! 🎉";
        const grouped = {}; 
        items.forEach(item => { 
            const key = item.id + (item.mutations ? item.mutations.join('') : '');
            if (grouped[key]) { grouped[key].count++; } 
            else { grouped[key] = { ...item, count: 1 }; } 
        });
        const uniqueItems = Object.values(grouped);
        uniqueItems.forEach((item, index)=>{
            const div=document.createElement('div'); div.className=`drop-item rarity-${item.rarity}`; 
            div.style.animationDelay = `${index * 0.1}s`; 
            const countBadge = item.count > 1 ? `<div class="drop-quantity">x${item.count}</div>` : '';
            let mutsHtml = '';
            if(item.mutations && item.mutations.length > 0) {
                const mainMut = item.mutations[0];
                const color = MUTATION_COLORS[mainMut] || '#FFD700';
                div.style.border = `2px solid ${color}`;
                div.style.boxShadow = `0 0 15px ${color}`;
                mutsHtml = '<div class="mutation-badges" style="top:-10px;left:-5px">';
                item.mutations.forEach(m => { mutsHtml += `<span class="mut-badge">${MUT_EMOJIS[m] || m}</span>`; });
                mutsHtml += '</div>';
            }
            div.innerHTML=`${countBadge}${mutsHtml}<img src="${item.image_url}"><div class="case-name">${item.name}</div>`;
            el.dropGrid.appendChild(div);
            if(index === 0 && item.sound_url && item.sound_url!=='-') { el.audio.src=item.sound_url; el.audio.play().catch(()=>{}); }
        });
        load();
    }

    // --- ОБНОВЛЕННАЯ ФУНКЦИЯ ВЫБОРА (С ЦВЕТАМИ РЕДКОСТИ) ---
    window.openItemSelect=(side)=>{
        el.selGrid.innerHTML=''; el.selModal.classList.remove('hidden');
        let list = (side==='left' || side==='wager') ? inventory.filter(i=>i.quantity>0) : allItemsSorted;
        if (side === 'right' && upgMy) { const myRank = RARITY_ORDER[upgMy.rarity] || 0; list = list.filter(item => (RARITY_ORDER[item.rarity] || 0) > myRank); }
        list = sortItems(list);
        if(list.length === 0) { el.selGrid.innerHTML = "<p style='grid-column:1/-1;text-align:center;color:#666;font-size:0.9rem;'>Нет доступных предметов</p>"; return; }
        list.forEach(i=>{
            const div = createItemCardHTML(i, true, (clickedItem) => {
                if(side==='wager') {
                    selWagerItem = clickedItem;
                    el.selWagerItemDiv.innerHTML = `<img src="${clickedItem.image_url}" style="width:50px;height:50px;border-radius:5px;vertical-align:middle;"> <b>${clickedItem.name}</b>`;
                } else { selectUpgradeItem(side, clickedItem); }
                el.selModal.classList.add('hidden'); 
            });
            div.className = `select-card rarity-${i.rarity}`;
            if(i.muts_list && i.muts_list.length > 0) div.classList.add('mutated'); 
            div.innerHTML = div.innerHTML.replace(/<button.*button>/, ''); 
            div.innerHTML += `<span>${formatBalance(i.price)} ⭐️</span>`;
            el.selGrid.appendChild(div);
        });
    }

    function selectUpgradeItem(side, item){
        if(side==='left'){ upgMy=item; el.uLeft.innerHTML=`<img src="${item.image_url}"><div class="u-item-name">${item.name}</div><p>${formatBalance(item.price)} ⭐️</p>`; el.uLeft.classList.add('selected'); upgTarget = null; el.uRight.innerHTML="<p>ЦЕЛЬ</p>"; el.uRight.classList.remove('selected'); } 
        else { upgTarget=item; el.uRight.innerHTML=`<img src="${item.image_url}"><div class="u-item-name">${item.name}</div><p>${formatBalance(item.price)} ⭐️</p>`; el.uRight.classList.add('selected'); }
        calcChance();
    }
    window.autoSelectTarget=(desiredChance)=>{
        if(!upgMy) return tg.showAlert("Сначала выбери свой предмет слева!");
        let targetPrice = (upgMy.price * 95) / desiredChance;
        const myRank = RARITY_ORDER[upgMy.rarity] || 0;
        const validItems = allItemsSorted.filter(item => (RARITY_ORDER[item.rarity] || 0) > myRank);
        if (validItems.length === 0) return tg.showAlert("Нет подходящих предметов для улучшения!");
        let closestItem = validItems.reduce((prev, curr) => (Math.abs(curr.price - targetPrice) < Math.abs(prev.price - targetPrice) ? curr : prev));
        selectUpgradeItem('right', closestItem);
    }
    function calcChance(){
        if(!upgMy || !upgTarget) { el.uChance.innerText="0%"; el.uBtn.disabled=true; el.upgCircleFg.style.strokeDashoffset = 628; return; }
        let ch = (upgMy.price / upgTarget.price) * 100 * 0.95; if(ch>80) ch=80; if(ch<1) ch=1;
        const chanceVal = ch.toFixed(2); el.uChance.innerText = chanceVal + "%"; el.uBtn.disabled=false;
        const radius = 100; const circumference = 2 * Math.PI * radius; 
        const offset = circumference - (ch / 100) * circumference;
        el.upgCircleFg.style.strokeDashoffset = offset;
    }
    el.uBtn.onclick=async()=>{
        if(!upgMy || !upgTarget) return;
        el.uBtn.disabled=true; el.resultLayer.classList.remove('show'); 
        document.querySelector('.progress-ring').style.transition = 'none';
        document.querySelector('.progress-ring').style.transform = 'rotate(-90deg)';
        try{
            const res=await fetch(`${API}/upgrade`,{method:'POST',body:JSON.stringify({user_id:userId, item_id:upgMy.item_id, target_id:upgTarget.id})});
            const d=await res.json();
            if(d.error) { tg.showAlert(d.error); el.uBtn.disabled=false; return; }
            const winChanceVal = parseFloat(el.uChance.innerText); const isWin = (d.status === 'win');
            let stopAngle; 
            if(isWin) { stopAngle = Math.random() * winChanceVal; } 
            else { stopAngle = winChanceVal + (Math.random() * (100 - winChanceVal)); }
            const spins = 5 * 360; 
            const finalRotate = spins - (stopAngle/100 * 360);
            const ringEl = document.querySelector('.progress-ring');
            ringEl.style.transition = 'transform 4s cubic-bezier(0.15, 0, 0.2, 1)'; 
            ringEl.style.transform = `rotate(${finalRotate - 90}deg)`; 
            setTimeout(()=>{
                el.resultLayer.classList.add('show');
                if(isWin){ el.resultText.innerText = "УСПЕХ"; el.resultText.className = "text-win"; showResults([d.item]); } 
                else { el.resultText.innerText = "НЕУДАЧА"; el.resultText.className = "text-lose"; load(); }
                upgMy=null; upgTarget=null; el.uLeft.innerHTML="<p>ПРЕДМЕТ</p>"; el.uLeft.classList.remove('selected'); el.uRight.innerHTML="<p>ЦЕЛЬ</p>"; el.uRight.classList.remove('selected'); el.uChance.innerText="0%"; el.uBtn.disabled=false; el.upgCircleFg.style.strokeDashoffset = 628;
            }, 4050);
        } catch(e){ console.error(e); tg.showAlert("Ошибка связи!"); el.uBtn.disabled=false; load(); }
    }
    document.getElementById('claim-btn').onclick=()=>{ el.popup.classList.remove('active'); el.popup.classList.add('hidden'); };
    load();
});
