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

    const el={
        bal:document.getElementById('balance'), cases:document.getElementById('cases-grid'), inv:document.getElementById('inventory-grid'), 
        loader:document.getElementById('loading-screen'), openModal:document.getElementById('open-modal'), 
        mImg:document.getElementById('modal-case-img'), mPrice:document.getElementById('modal-case-price'), 
        slider:document.getElementById('case-slider'), sliderVal:document.getElementById('slider-count'), totalBtn:document.getElementById('total-price-btn'),
        popup:document.getElementById('drop-popup'), dropGrid:document.getElementById('drop-results-grid'), audio:document.getElementById('audio-player'),
        // Upgrade
        selModal:document.getElementById('select-modal'), selGrid:document.getElementById('select-grid'),
        uLeft:document.getElementById('u-slot-left'), uRight:document.getElementById('u-slot-right'),
        uChance:document.getElementById('u-chance'), uBtn:document.getElementById('upgrade-btn'), uCircle:document.getElementById('u-circle')
    };

    function upBal(n){if(n===undefined)return; if(currentBal!==n){el.bal.style.color='#fff'; setTimeout(()=>el.bal.style.color='',300);} currentBal=n; el.bal.innerText=n;}

    async function load(){
        try {
            const res=await fetch(`${API}/data`,{method:'POST', body:JSON.stringify({user_id:userId, username})});
            const d=await res.json();
            allItems=d.case_items||[]; inventory=d.inventory||[]; allItemsSorted=d.all_items||[];
            if(d.user) upBal(d.user.balance);

            // Кейсы
            el.cases.innerHTML=''; d.cases.forEach(c=>{
                const div=document.createElement('div'); div.className='case-card';
                div.innerHTML=`<img src="${c.icon_url}" class="case-img"><div class="case-name">${c.name}</div><div class="case-price"⭐️ ${c.price}</div>`;
                div.onclick=()=>{selectedCase=c; showOpenModal();}; el.cases.appendChild(div);
            });

            // Инвентарь
            el.inv.innerHTML=''; if(!inventory.length) el.inv.innerHTML="<p style='color:#666;grid-column:1/-1;text-align:center'>Пусто</p>";
            inventory.reverse().forEach(i=>{
                const div=document.createElement('div'); div.className=`item-card rarity-${i.rarity}`; div.id=`inv-${i.inv_id}`;
                div.innerHTML=`<img src="${i.image_url}" class="item-img"><div class="case-name">${i.name}</div><button class="sell-btn" onclick="sell(${i.inv_id},${i.sell_price})">Продать: <span>⭐️ ${i.sell_price}</span></button>`;
                el.inv.appendChild(div);
            });
            setTimeout(()=>el.loader.style.display='none',500);
        } catch(e){}
    }

    // --- ОТКРЫТИЕ (Слайдер) ---
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
            div.style.animationDelay=`${i*0.2}s`; // Анимация очереди
            div.innerHTML=`<img src="${item.image_url}"><div class="case-name">${item.name}</div>`;
            el.dropGrid.appendChild(div);
            if(i===0 && item.sound_url && item.sound_url!=='-') { el.audio.src=item.sound_url; el.audio.play().catch(()=>{}); }
        });
        load();
    }

    // --- АПГРЕЙД ---
    window.openItemSelect=(side)=>{
        el.selGrid.innerHTML=''; el.selModal.classList.remove('hidden');
        const list = side==='left' ? inventory : allItemsSorted;
        list.forEach(i=>{
            const div=document.createElement('div'); div.className='select-card';
            div.innerHTML=`<img src="${i.image_url}"><span>${i.price} ⭐️</span>`;
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

    function calcChance(){
        if(!upgMy || !upgTarget) { el.uChance.innerText="0%"; el.uBtn.disabled=true; return; }
        let ch = (upgMy.price / upgTarget.price) * 100 * 0.95;
        if(ch>80) ch=80; if(ch<1) ch=1;
        el.uChance.innerText=ch.toFixed(1)+"%"; el.uBtn.disabled=false;
    }

    el.uBtn.onclick=async()=>{
        if(!upgMy || !upgTarget) return;
        el.uBtn.disabled=true; el.uCircle.classList.add('spinning');
        
        try{
            const res=await fetch(`${API}/upgrade`,{method:'POST',body:JSON.stringify({user_id:userId, inv_id:upgMy.inv_id, target_id:upgTarget.id})});
            const d=await res.json();
            
            setTimeout(()=>{
                el.uCircle.classList.remove('spinning');
                if(d.status==='win'){
                    tg.showAlert("УСПЕХ! 🎉");
                    showResults([d.item]); // Показываем выигрыш
                } else {
                    tg.showAlert("СГОРЕЛ 🔥");
                    load();
                }
                // Сброс
                upgMy=null; upgTarget=null; el.uLeft.innerHTML="<p>ВЫБЕРИ<br>ПРЕДМЕТ</p>"; el.uLeft.classList.remove('selected');
                el.uRight.innerHTML="<p>ВЫБЕРИ<br>ЦЕЛЬ</p>"; el.uRight.classList.remove('selected'); el.uChance.innerText="0%";
            }, 2000); // 2 сек крутим
        } catch{ load(); }
    }

    window.sell=async(id,p)=>{ upBal(currentBal+p); document.getElementById(`inv-${id}`)?.remove(); await fetch(`${API}/sell`,{method:'POST',body:JSON.stringify({user_id:userId,inv_id:id,price:p})}); };
    document.getElementById('claim-btn').onclick=()=>{el.popup.classList.remove('active');};
    load();
});