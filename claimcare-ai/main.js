document.addEventListener('DOMContentLoaded', () => {
  const claimForm = document.getElementById('claim-form');
  const copayInput = document.getElementById('copay-cost');
  const nonCoveredInput = document.getElementById('non-covered-cost');
  const treatmentTypeSelect = document.getElementById('treatment-type');
  const generationSelect = document.getElementById('generation');
  const symptomsInput = document.getElementById('symptoms');

  const formError = document.getElementById('form-error');
  const btnSubmit = document.getElementById('btn-submit');
  const loadingBox = document.getElementById('loading-box');
  const resultBox = document.getElementById('result-box');
  const btnRecalc = document.getElementById('btn-recalc');

  // 통화 형식 포맷터 (예: 120,000원)
  const formatWon = (num) => new Intl.NumberFormat('ko-KR').format(num) + '원';

  // 에러 메시지 표시 함수
  const showError = (msg) => {
    formError.textContent = msg;
    formError.classList.remove('hidden');
    formError.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
  };

  const clearError = () => {
    formError.textContent = '';
    formError.classList.add('hidden');
  };

  // 폼 제출 이벤트 핸들러
  claimForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    clearError();

    const copayCost = parseInt(copayInput.value, 10);
    const nonCoveredCost = parseInt(nonCoveredInput.value, 10);

    // [UX 방어 1] 필수값 누락 및 유효성 검증
    if (isNaN(copayCost) || isNaN(nonCoveredCost)) {
      showError('급여 및 비급여 진료비 금액을 올바르게 숫자로 입력해 주세요.');
      return;
    }

    if (copayCost === 0 && nonCoveredCost === 0) {
      showError('진료비 발생 금액이 0원입니다. 최소 하나 이상의 금액을 입력해 주세요.');
      return;
    }

    // UI 상태: 로딩 시작
    btnSubmit.disabled = true;
    claimForm.classList.add('hidden');
    resultBox.classList.add('hidden');
    loadingBox.classList.remove('hidden');

    const payload = {
      treatmentType: treatmentTypeSelect.value,
      generation: generationSelect.value,
      copayCost: copayCost,
      nonCoveredCost: nonCoveredCost,
      symptoms: symptomsInput.value.trim() || '허리 요통 및 통증'
    };

    try {
      // [API 연동] 백엔드 Serverless Function 호출
      const response = await fetch('/api/calculate', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(payload)
      });

      if (!response.ok) {
        const errData = await response.json().catch(() => ({}));
        throw new Error(errData.message || 서버 오류 발생 ());
      }

      const result = await response.json();

      // UI 상태: 결과 렌더링
      renderResult(result);
      loadingBox.classList.add('hidden');
      resultBox.classList.remove('hidden');
      resultBox.scrollIntoView({ behavior: 'smooth', block: 'start' });

    } catch (err) {
      // [UX 방어 2] API 실패 및 네트워크 타임아웃 대응
      loadingBox.classList.add('hidden');
      claimForm.classList.remove('hidden');
      showError(⚠️ 분석 처리 중 오류가 발생했습니다: );
    } finally {
      btnSubmit.disabled = false;
    }
  });

  // 결과 화면 데이터 바인딩
  const renderResult = (data) => {
    const summary = data.summary || {};
    document.getElementById('res-total-cost').textContent = formatWon(summary.total_cost || 0);
    document.getElementById('res-deductible').textContent = formatWon(summary.deductible_amount || 0);
    document.getElementById('res-payout').textContent = formatWon(summary.expected_payout || 0);

    document.getElementById('res-basis').textContent = data.calculation_basis || '약관 기준에 따라 산출되었습니다.';

    // 제출 서류 렌더링
    const docListEl = document.getElementById('res-documents');
    docListEl.innerHTML = '';
    (data.required_documents || []).forEach(doc => {
      const li = document.createElement('li');
      li.textContent = doc;
      docListEl.appendChild(li);
    });

    // 어드바이저 팁 렌더링
    const tipListEl = document.getElementById('res-tips');
    tipListEl.innerHTML = '';
    (data.advisor_tips || []).forEach(tip => {
      const li = document.createElement('li');
      li.textContent = tip;
      tipListEl.appendChild(li);
    });
  };

  // 다시 계산하기 버튼
  btnRecalc.addEventListener('click', () => {
    resultBox.classList.add('hidden');
    claimForm.classList.remove('hidden');
    claimForm.scrollIntoView({ behavior: 'smooth', block: 'start' });
  });
});
