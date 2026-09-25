/**
 * Casper Electric Mobile 1-Click Fast Pass Script
 * Repository: https://github.com/genlit-eng/CasperElectric
 */
(async function() {
    // 0. 화면 상단에 진행 상황 토스트 표시
    let toast = document.createElement('div');
    toast.style.cssText = 'position:fixed;top:20px;left:50%;transform:translateX(-50%);background:rgba(0,44,95,0.92);color:#fff;padding:12px 24px;border-radius:30px;font-size:15px;font-weight:bold;z-index:999999;box-shadow:0 4px 14px rgba(0,0,0,0.3);text-align:center;pointer-events:none;transition:all 0.3s;';
    toast.innerText = '⚡ 캐스퍼 원클릭 자동 설정 시작...';
    document.body.appendChild(toast);
    const updateToast = (msg) => { if (toast) toast.innerText = msg; };

    const sleep = ms => new Promise(r => setTimeout(r, ms));

    function findVisibleBtn(texts) {
        if (typeof texts === 'string') texts = [texts];
        const btns = Array.from(document.querySelectorAll('button, a'));
        return btns.find(b => {
            const t = b.innerText.trim();
            return texts.some(target => t === target || t.includes(target)) && b.offsetParent !== null;
        });
    }

    async function dismissModal() {
        await sleep(300);
        const confirmBtn = findVisibleBtn(['확인했습니다', '확인']);
        if (confirmBtn) {
            confirmBtn.click();
            await sleep(500);
        }
    }

    async function pickSelectByPlaceholder(placeholderText, targetText) {
        const inputs = Array.from(document.querySelectorAll('input')).filter(i => i.offsetParent !== null && i.placeholder.includes(placeholderText));
        if (inputs.length > 0) {
            const input = inputs[0];
            input.click();
            await sleep(350);
            const dropdowns = Array.from(document.querySelectorAll('.el-select-dropdown')).filter(el => el.style.display !== 'none');
            for (let dd of dropdowns) {
                const items = Array.from(dd.querySelectorAll('.el-select-dropdown__item'));
                const match = items.find(el => el.innerText.trim() === targetText || el.innerText.trim().includes(targetText));
                if (match) {
                    match.scrollIntoView();
                    match.click();
                    await sleep(400);
                    return true;
                }
            }
        }
        return false;
    }

    // 상세 페이지(/detail)인 경우 견적내기 자동 통과
    if (window.location.href.includes('/detail')) {
        updateToast('⚡ 1단계 견적 페이지로 이동 중...');
        const qBtn = findVisibleBtn(['견적내기']);
        if (qBtn) {
            qBtn.click();
            await sleep(1000);
            await dismissModal();
            for (let i = 0; i < 20; i++) {
                await sleep(500);
                if (window.location.href.includes('/estimation')) break;
            }
        }
    }

    // --- STEP 1: 배송지역 (경북 구미시) ---
    updateToast('⚡ Step 1: 배송지(경북 구미시) 설정...');
    await pickSelectByPlaceholder("시/도", "경북");
    await pickSelectByPlaceholder("시/군", "구미시");
    let next = findVisibleBtn(['다음']);
    if (next) {
        next.click();
        await sleep(1000);
        await dismissModal();
        await sleep(500);
    }

    // --- STEP 2: 포인트 & 할인 ---
    updateToast('⚡ Step 2: 포인트 & 할인 통과...');
    next = findVisibleBtn(['다음']);
    if (next) {
        next.click();
        await sleep(1200);
        await dismissModal();
    }

    // --- STEP 3: 전기차 구매보조금 (경북 구미시, 노후차 교체) ---
    updateToast('⚡ Step 3: 보조금/노후차 설정...');
    await pickSelectByPlaceholder("시/도", "경북");
    await pickSelectByPlaceholder("시/군", "구미시");

    const checkboxes = Array.from(document.querySelectorAll('.el-checkbox, label')).filter(el => el.offsetParent !== null);
    for (let cb of checkboxes) {
        const txt = cb.innerText.trim();
        if (txt.includes("내연기관")) {
            if (!cb.classList.contains("is-checked") && !cb.querySelector(".is-checked")) {
                cb.click();
                await sleep(250);
            }
        }
    }

    next = findVisibleBtn(['다음']);
    if (next) {
        next.click();
        await sleep(1200);
        await dismissModal();
    }

    // --- STEP 4: 등록비용 (공채: 경북 구미시) ---
    updateToast('⚡ Step 4: 등록비용 공채(경북 구미시) 설정...');
    await pickSelectByPlaceholder("시/도", "경북");
    await sleep(800);

    const visibleInps = Array.from(document.querySelectorAll('input.el-input__inner')).filter(i => i.offsetParent !== null);
    let bondSigunInp = visibleInps.find(i => i.value.includes("경산시") || i.placeholder.includes("선택하세요") || i.value.includes("구미시"));
    if (!bondSigunInp && visibleInps.length >= 3) {
        bondSigunInp = visibleInps[2];
    }
    if (bondSigunInp) {
        bondSigunInp.click();
        await sleep(500);
        const dds = Array.from(document.querySelectorAll('.el-select-dropdown')).filter(e => e.style.display !== 'none');
        for (let dd of dds) {
            const match = Array.from(dd.querySelectorAll('.el-select-dropdown__item')).find(x => x.innerText.trim().includes("구미"));
            if (match) {
                match.scrollIntoView();
                match.click();
                await sleep(500);
                break;
            }
        }
    }

    next = findVisibleBtn(['다음']);
    if (next) {
        next.click();
        await sleep(2000);
        await dismissModal();
    }

    // --- STEP 5: 견적완료 및 계약대기 ---
    updateToast('✅ 모든 할인 반영 완료! [계약하기]를 눌러주세요');
    setTimeout(() => { if (toast) toast.remove(); }, 5000);
})();

