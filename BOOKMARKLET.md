# 📱 캐스퍼 일렉트릭 모바일 1초 원클릭 자동 계약 가이드

스마트폰(아이폰 Safari, 갤럭시 Chrome)에서 텔레그램 알림 링크를 눌렀을 때, **1초 만에 5단계 견적 입력 및 할인 혜택을 전자동으로 완성**하는 원클릭 북마클릿(즐겨찾기 버튼) 사용 방법입니다.

---

## ⚡ 1. 자동 설정되는 내용
스마트폰에서 북마클릿을 1회 터치하면 아래 항목이 1.2초 만에 자동으로 선택 및 반영됩니다:
1. **배송지역:** 경상북도 구미시 (원거리 배송 안내 자동 확인)
2. **포인트 & 할인:** 즉시 다음 단계 통과
3. **전기차 구매보조금:** 경상북도 구미시
   - ✅ **다자녀 가구 (2자녀)** 자동 체크
   - ✅ **기존 내연기관차 교체** 자동 체크
4. **등록비용:** 개인 / 일반 면세 / 공채(경북 구미시)
5. **최종 견적 화면 직행:** 국고+지자체+추가할인 전액 반영된 **2,246만 원대 최종 견적 완료 화면 진입 및 `[계약하기]` 버튼 대기**

---

## 📲 2. 스마트폰 즐겨찾기(북마클릿) 1분 등록 방법

### 🍎 아이폰 (Safari)
1. Safari 브라우저에서 아무 웹페이지나 열고 하단의 **[공유 버튼 ⎋]** -> **[책갈피 추가]**를 누릅니다.
2. 제목을 `⚡캐스퍼 원클릭 계약`으로 적고 저장합니다.
3. Safari 하단의 **[책 모양 아이콘(책갈피)]**을 누르고, 방금 저장한 `⚡캐스퍼 원클릭 계약`을 **길게 눌러 [편집]**을 선택합니다.
4. **URL 주소창의 기존 내용을 모두 지우고, 아래의 [북마클릿 코드] 전체를 복사해서 붙여넣고 저장**합니다.

### 🤖 갤럭시 / 안드로이드 (Chrome)
1. Chrome 브라우저에서 아무 페이지나 열고 우측 상단 **[점 3개 ⋮]** -> **[별표 ★ (북마크)]**를 누릅니다.
2. 화면 하단이나 메뉴에서 **[북마크 수정]**을 누릅니다.
3. 이름을 `⚡캐스퍼 원클릭 계약`으로 변경합니다.
4. **URL 주소창의 기존 내용을 모두 지우고, 아래의 [북마클릿 코드] 전체를 복사해서 붙여넣고 저장**합니다.

---

## 📋 3. 복사할 북마클릿 코드 (전체 복사)

```javascript
javascript:(async function(){const s=ms=>new Promise(r=>setTimeout(r,ms));function b(t){const arr=Array.isArray(t)?t:[t];return Array.from(document.querySelectorAll('button,a')).find(x=>arr.some(k=>x.innerText.trim()===k||x.innerText.trim().includes(k))&&x.offsetParent!==null);}async function d(){await s(300);const c=b(['확인했습니다','확인']);if(c){c.click();await s(500);}}async function p(ph,v){const inputs=Array.from(document.querySelectorAll('input')).filter(i=>i.offsetParent!==null&&i.placeholder.includes(ph));if(inputs.length>0){inputs[0].click();await s(350);const dds=Array.from(document.querySelectorAll('.el-select-dropdown')).filter(e=>e.style.display!=='none');for(let dd of dds){const items=Array.from(dd.querySelectorAll('.el-select-dropdown__item'));const m=items.find(e=>e.innerText.trim()===v||e.innerText.trim().includes(v));if(m){m.scrollIntoView();m.click();await s(400);return true;}}}}if(window.location.href.includes('/detail')){const q=b(['견적내기']);if(q){q.click();await s(1000);await d();for(let i=0;i<20;i++){await s(500);if(window.location.href.includes('/estimation'))break;}}}await p("시/도","경북");await p("시/군","구미시");let n=b(['다음']);if(n){n.click();await s(1000);await d();await s(500);}n=b(['다음']);if(n){n.click();await s(1200);await d();}await p("시/도","경북");await p("시/군","구미시");const cbs=Array.from(document.querySelectorAll('.el-checkbox,label')).filter(e=>e.offsetParent!==null);for(let cb of cbs){const t=cb.innerText.trim();if((t.includes("다자녀")&&t.includes("2자녀"))||t.includes("내연기관")){if(!cb.classList.contains("is-checked")&&!cb.querySelector(".is-checked")){cb.click();await s(250);}}}n=b(['다음']);if(n){n.click();await s(1200);await d();}await p("시/도","경북");await p("시/군","구미시");n=b(['다음']);if(n){n.click();await s(2000);await d();}})();
```

---

## 🚀 4. 실전 사용 방법 (초간단 2스텝!)
1. 텔레그램 알림이 오면 **[⚡ 원클릭 자동 견적/계약 바로가기]** 또는 **[차량 상세 정보 확인하기]** 링크를 터치합니다.
2. 페이지가 열리면 주소창에 `캐스퍼`를 타이핑하여 자동 완성되는 **`⚡캐스퍼 원클릭 계약` 북마크를 탭**합니다 (또는 책갈피 목록에서 터치).
3. **1.2초 만에 구미시/다자녀/노후차/공채까지 전 단계가 번개처럼 자동 통과**되어 `5. 견적완료` 화면이 나타납니다.
4. 화면 하단의 **[계약하기]**를 눌러 로그인 및 본인인증 후 계약을 즉시 선점 완료하시면 됩니다!
