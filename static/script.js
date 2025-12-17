window.switchTab=function(t){document.querySelectorAll('.tab-content').forEach(e=>e.classList.remove('active'));document.querySelectorAll('.nav-btn').forEach(e=>e.classList.remove('active'));document.getElementById(`tab-${t}`).classList.add('active');if(t!=='market')document.querySelector(`.nav-btn[onclick="switchTab('${t}')"]`).classList.add('active');}
window.closeModal=function(id){document.getElementById(id).classList.add('hidden')}

document.addEventListener('DOMContentLoaded', () => {
    const tg = window.Telegram.WebApp; tg.expand();
    const API = window.location.origin + '/api';
    let userId = tg.initDataUnsafe?.user?.id || 0;
    let username = tg.initDataUnsafe?.user?.username || 'Guest';
    let allItems=[], inventory=[], allItemsSorted=[], currentBal=0;
    let selectedCase={id:0, price:0}, openCount=1;
    let upgMy=null, upgTarget=null;
    // Переменные для продажи
    let sellingItem=null, sellCount=1;

    const el={
        bal:document.getElementById('balance'), cases:document.getElementById('cases-grid'), inv:document.getElementById('inventory-grid'), 
        loader:document.getElementById('loading-screen'), openModal:document.getElementById('open-modal'), 
        mImg:document.getElementById('modal-case-img'), mPrice:document.getElementById('modal-case-price'), 
        slider:document.getElementById('case-slider'), sliderVal:document.getElementById('slider-count'), totalBtn:document.getElementById('total-price-btn'),
        popup:document.getElementById('drop-popup'), dropGrid:document.getElementById('drop-results-grid'), audio:document.getElementById('audio-player'),
        selModal:document.getElementById('select-modal'), selGrid:document.getElementById('select-grid'),
        uLeft:document.getElementById('u-slot-left'), uRight:document.getElementById('u-slot-right'),
        uBtn:document.getElementById('upgrade-btn'),
        // Новые элементы рулетки
        ring:document.getElementById('spinRing'), uChance:document.getElementById('u-chance'), resultLayer:document.getElementById('resultLayer'), resultText:document.getElementById('resultText'),
        
        // Элементы продажи
        sellModal:document.getElementById('sell-modal'), sellName:document.getElementById('sell-item-name'), sellImg:document.getElementById('sell-item-img'),
        sellOwned:document.getElementById('sell-owned-count'), sellSlider:document.getElementById('sell-slider'), sellSliderVal:document.getElementById('sell-slider-count'),
        sellTotalBtn:document.getElementById('total-sell-price'), confirmSellBtn:document.getElementById('confirm-sell-btn')
    };

    function upBal(n){if(n===undefined)return; if(currentBal!==n){el.bal.style.color='#fff'; setTimeout(()=>el.bal.style.color='',300);} currentBal=n; el.bal.innerText=n;}

    async function load(){
        try {
            const res=await fetch(`${API}/data`,{method:'POST', body:JSON.stringify({user_id:userId, username})});
            const d=await res.json();
            allItems=d.case_items||[]; inventory=d.inventory||[]; allItemsSorted=d.all_items||[];
            if(d.user) upBal(d.user.balance);

            el.cases.innerHTML=''; d.cases.forEach(c=>{
                const div=document.createElement('div'); div.className='case-card';
                div.innerHTML=`<img src="${c.icon_url}" class="case-img"><div class="case-name">${c.name}</div><div class="case-price">⭐️ ${c.price}</div>`;
                div.onclick=()=>{selectedCase=c; showOpenModal();}; el.cases.appendChild(div);
            });

            // Инвентарь
            el.inv.innerHTML=''; if(!inventory.length) el.inv.innerHTML="<p style='color:#666;grid-column:1/-1;text-align:center'>Пусто</p>";
            inventory.reverse().forEach(i=>{
                const div=document.createElement('div'); div.className=`item-card rarity-${i.rarity}`; div.id=`inv-item-${i.item_id}`;
                div.innerHTML=`<span class="item-quantity">x${i.quantity}</span><img src="${i.image_url}" class="item-img"><div class="case-name">${i.name}</div><button class="sell-btn" onclick="openSellModal(${i.item_id})">Продать: <span>⭐️ ${i.sell_price}</span></button>`;
                el.inv.appendChild(div);
            });
            
            // Leaderboard
            if(d.leaderboard) {
                const lbDiv = document.getElementById('leaderboard-list');
                if(lbDiv) {
                    lbDiv.innerHTML = '<h2>🏆 ТОП ИГРОКОВ</h2>';
                    d.leaderboard.forEach((u, idx) => {
                        lbDiv.innerHTML += `<div style="background:#222;padding:10px;margin:5px 0;border-radius:10px;display:flex;justify-content:space-between"><span>${idx+1}. ${u.username}</span><span style="color:#FFD700">${u.balance} ⭐️</span></div>`;
                    });
                }
            }

            setTimeout(()=>el.loader.style.display='none',500);
        } catch(e){}
    }

    // --- ПРОДАЖА ---
    window.openSellModal=(itemId)=>{
        sellingItem = inventory.find(i => i.item_id === itemId);
        if(!sellingItem) return;
        el.sellName.innerText = sellingItem.name;
        el.sellImg.src = sellingItem.image_url;
        el.sellOwned.innerText = sellingItem.quantity;
        el.sellSlider.max = sellingItem.quantity;
        el.sellSlider.value = 1;
        updateSellSlider(1);
        el.sellModal.classList.remove('hidden');
    }
    window.updateSellSlider=(v)=>{
        sellCount = parseInt(v);
        el.sellSliderVal.innerText = sellCount;
        el.sellTotalBtn.innerText = sellingItem.sell_price * sellCount;
    }
    el.confirmSellBtn.onclick = async() => {
        if(!sellingItem) return;
        const totalPrice = sellingItem.sell_price * sellCount;
        const itemId = sellingItem.item_id;
        el.sellModal.classList.add('hidden');
        
        // Оптимистичное обновление баланса
        upBal(currentBal + totalPrice);
        
        try {
            const res = await fetch(`${API}/sell_batch`,{method:'POST',body:JSON.stringify({user_id:userId, item_id:itemId, count:sellCount, price_per_item:sellingItem.sell_price})});
            const d = await res.json();
            if(d.error) {
                tg.showAlert("Ошибка продажи");
            }
            load();
        } catch(e) { load(); }
    }

    // --- КЕЙСЫ ---
    window.showOpenModal=()=>{
        el.mImg.src=selectedCase.icon_url; el.mPrice.innerText=selectedCase.price;
        el.slider.value=1; updateSlider(1); el.openModal.classList.remove('hidden');
    }
    window.updateSlider=(v)=>{
        openCount=parseInt(v); el.sliderVal.innerText=openCount; el.totalBtn.innerText=selectedCase.price*openCount;
    }
    document.getElementById('start-open-btn').onclick=async()=>{
        const price=selectedCase.price*openCount;
        if(currentBal<price) return tg.showAlert("Мало звезд!");
        el.openModal.classList.add('hidden'); upBal(currentBal-price);
        el.popup.classList.add('active'); el.dropGrid.innerHTML='<div class="spinner"></div>';
        try {
            const res=await fetch(`${API}/open`,{method:'POST',body:JSON.stringify({user_id:userId, case_id:selectedCase.id, count:openCount})});
            const d=await res.json();
            if(d.error){ el.popup.classList.remove('active'); load(); return tg.showAlert(d.error); }
            showResults(d.dropped);
        } catch{ load(); }
    };
    function showResults(items){
        el.dropGrid.innerHTML=''; el.dropGrid.className=items.length>1?'drop-grid multi':'drop-grid single';
        document.getElementById('drop-title').innerText = "🎉 ВЫПАЛО! 🎉";
        items.forEach((item,i)=>{
            const div=document.createElement('div'); div.className=`drop-item rarity-${item.rarity}`; 
            div.style.animationDelay=`${i*0.2}s`;
            div.innerHTML=`<img src="${item.image_url}"><div class="case-name">${item.name}</div>`;
            el.dropGrid.appendChild(div);
            if(i===0 && item.sound_url && item.sound_url!=='-') { el.audio.src=item.sound_url; el.audio.play().catch(()=>{}); }
        });
        load();
    }

    // --- АПГРЕЙД ЛОГИКА ---
    window.openItemSelect=(side)=>{
        el.selGrid.innerHTML=''; el.selModal.classList.remove('hidden');
        const list = side==='left' ? inventory.filter(i=>i.quantity>0) : allItemsSorted;
        list.forEach(i=>{
            const div=document.createElement('div'); div.className='select-card';
            const countBadge = (side==='left') ? `<span class="item-quantity">x${i.quantity}</span>` : '';
            div.innerHTML=`${countBadge}<img src="${i.image_url}"><span>${i.price} ⭐️</span>`;
            div.onclick=()=>{ selectUpgradeItem(side, i); el.selModal.classList.add('hidden'); };
            el.selGrid.appendChild(div);
        });
    }

    function selectUpgradeItem(side, item){
        if(side==='left'){
            upgMy=item; el.uLeft.innerHTML=`<img src="${item.image_url}"><p>${item.price} ⭐️</p>`; el.uLeft.classList.add('selected');
        } else {
            upgTarget=item; el.uRight.innerHTML=`<img src="${item.image_url}"><p>${item.price} ⭐️</p>`; el.uRight.classList.add('selected');
        }
        calcChance();
    }

    window.autoSelectTarget=(desiredChance)=>{
        if(!upgMy) return tg.showAlert("Сначала выбери свой предмет слева!");
        let targetPrice = (upgMy.price * 95) / desiredChance;
        let closestItem = allItemsSorted.reduce((prev, curr) => (Math.abs(curr.price - targetPrice) < Math.abs(prev.price - targetPrice) ? curr : prev));
        selectUpgradeItem('right', closestItem);
    }

    function calcChance(){
        if(!upgMy || !upgTarget) { el.uChance.innerText="0%"; el.uBtn.disabled=true; el.ring.style.background='conic-gradient(#444 0% 100%)'; return; }
        let ch = (upgMy.price / upgTarget.price) * 100 * 0.95;
        if(ch>80) ch=80; if(ch<1) ch=1;
        const chanceVal = ch.toFixed(2);
        el.uChance.innerText = chanceVal + "%";
        el.uBtn.disabled=false;
        el.ring.style.background = `conic-gradient(#ffcc00 0% ${chanceVal}%, #2a2a2a ${chanceVal}% 100%)`;
    }

    el.uBtn.onclick=async()=>{
        if(!upgMy || !upgTarget) return;
        
        el.uBtn.disabled=true; 
        el.resultLayer.classList.remove('show');
        el.ring.classList.remove('win-glow', 'lose-glow');
        el.ring.style.transition = 'none';
        el.ring.style.transform = 'rotate(0deg)';

        try{
            const res=await fetch(`${API}/upgrade`,{method:'POST',body:JSON.stringify({user_id:userId, item_id:upgMy.item_id, target_id:upgTarget.id})});
            const d=await res.json();
            
            if(d.error) {
                tg.showAlert("Ошибка: " + d.error);
                load();
                el.uBtn.disabled=false;
                return;
            }

            const winChanceVal = parseFloat(el.uChance.innerText);
            const isWin = (d.status === 'win');

            // Анимация вращения к нужному результату
            let stopAngle;
            if(isWin) {
                stopAngle = Math.random() * winChanceVal;
            } else {
                stopAngle = winChanceVal + (Math.random() * (100 - winChanceVal));
            }
            
            const angleDeg = (stopAngle / 100) * 360;
            const spins = 5 * 360; 
            const finalRotate = spins + (360 - angleDeg);

            setTimeout(() => {
                el.ring.style.transition = 'transform 4s cubic-bezier(0.15, 0, 0.2, 1)';
                el.ring.style.transform = `rotate(${finalRotate}deg)`;
            }, 50);

            setTimeout(()=>{
                el.resultLayer.classList.add('show');
                
                if(isWin){
                    el.resultText.innerText = "УСПЕХ";
                    el.resultText.className = "text-win";
                    el.ring.classList.add('win-glow');
                    showResults([d.item]); 
                } else {
                    el.resultText.innerText = "НЕУДАЧА";
                    el.resultText.className = "text-lose";
                    el.ring.classList.add('lose-glow');
                    load(); 
                }

                upgMy=null; upgTarget=null; 
                el.uLeft.innerHTML="<p>ВЫБЕРИ<br>ПРЕДМЕТ</p>"; el.uLeft.classList.remove('selected');
                el.uRight.innerHTML="<p>ВЫБЕРИ<br>ЦЕЛЬ</p>"; el.uRight.classList.remove('selected'); 
                el.uChance.innerText="0%";
                el.uBtn.disabled=false;

            }, 4050);

        } catch(e){ 
            console.error(e);
            tg.showAlert("Ошибка связи!");
            el.uBtn.disabled=false;
            load(); 
        }
    }
    
    document.getElementById('claim-btn').onclick=()=>{el.popup.classList.remove('active');};
    load();
});