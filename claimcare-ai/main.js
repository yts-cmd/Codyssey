document.addEventListener('DOMContentLoaded', () => {
  const claimForm = document.getElementById('claim-form');
  const copayInput = document.getElementById('copay-cost');
  const nonCoveredInput = document.getElementById('non-covered-cost');
  const treatmentTypeSelect = document.getElementById('treatment-type');
  const generationSelect = document.getElementById('generation');
  const symptomsInput = document.getElementById('symptoms');

  const fileInput = document.getElementById('file-input');
  const dropZone = document.getElementById('drop-zone');
  const uploadPrompt = document.getElementById('upload-prompt');
  const previewContainer = document.getElementById('preview-container');
  const previewControls = document.getElementById('preview-controls');
  const fileCountText = document.getElementById('file-count-text');
  const btnClearAll = document.getElementById('btn-clear-all');

  const formError = document.getElementById('form-error');
  const btnSubmit = document.getElementById('btn-submit');
  const loadingBox = document.getElementById('loading-box');
  const loadingTitle = document.getElementById('loading-title');
  const resultBox = document.getElementById('result-box');
  const btnRecalc = document.getElementById('btn-recalc');

  let uploadedImages = [];

  const formatWon = (num) => new Intl.NumberFormat('ko-KR').format(num) + '원';

  const showError = (msg) => {
    formError.textContent = msg;
    formError.classList.remove('hidden');
    formError.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
  };

  const clearError = () => {
    formError.textContent = '';
    formError.classList.add('hidden');
  };

  // 이미지 초고속 압축 함수 (OCR 판독 해상도 1200px 유지, 용량 90% 압축)
  const compressImage = (file) => {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.readAsDataURL(file);
      reader.onload = (event) => {
        const img = new Image();
        img.src = event.target.result;
        img.onload = () => {
          const maxDim = 1200;
          let width = img.width;
          let height = img.height;

          if (width > maxDim || height > maxDim) {
            if (width > height) {
              height = Math.round((height * maxDim) / width);
              width = maxDim;
            } else {
              width = Math.round((width * maxDim) / height);
              height = maxDim;
            }
          }

          const canvas = document.createElement('canvas');
          canvas.width = width;
          canvas.height = height;
          const ctx = canvas.getContext('2d');
          ctx.drawImage(img, 0, 0, width, height);

          // 0.8 품질 JPEG로 압축하여 대폭 경량화
          const compressedDataUrl = canvas.toDataURL('image/jpeg', 0.8);
          resolve(compressedDataUrl);
        };
        img.onerror = (err) => reject(err);
      };
      reader.onerror = (err) => reject(err);
    });
  };

  dropZone.addEventListener('click', (e) => {
    if (e.target.closest('#btn-clear-all') || e.target.closest('.preview-remove-btn')) return;
    fileInput.click();
  });

  dropZone.addEventListener('dragover', (e) => {
    e.preventDefault();
    dropZone.style.borderColor = 'var(--primary)';
  });
  dropZone.addEventListener('dragleave', () => {
    dropZone.style.borderColor = '#93c5fd';
  });
  dropZone.addEventListener('drop', (e) => {
    e.preventDefault();
    dropZone.style.borderColor = '#93c5fd';
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      processFiles(Array.from(e.dataTransfer.files));
    }
  });

  fileInput.addEventListener('change', (e) => {
    if (e.target.files && e.target.files.length > 0) {
      processFiles(Array.from(e.target.files));
    }
  });

  const processFiles = async (files) => {
    clearError();
    const imageFiles = files.filter(f => f.type.startsWith('image/'));
    if (imageFiles.length === 0) {
      showError('이미지 파일(JPG, PNG 등)만 등록할 수 있습니다.');
      return;
    }

    for (const file of imageFiles) {
      try {
        const compressedData = await compressImage(file);
        uploadedImages.push({
          name: file.name,
          data: compressedData
        });
      } catch (err) {
        console.error('이미지 압축 실패:', err);
      }
    }
    renderPreviews();
  };

  const renderPreviews = () => {
    previewContainer.innerHTML = '';
    if (uploadedImages.length === 0) {
      uploadPrompt.classList.remove('hidden');
      previewContainer.classList.add('hidden');
      previewControls.classList.add('hidden');
      fileInput.value = '';
      return;
    }

    uploadPrompt.classList.add('hidden');
    previewContainer.classList.remove('hidden');
    previewControls.classList.remove('hidden');
    fileCountText.textContent = `총 ${uploadedImages.length}장의 사진이 첨부되었습니다.`;

    uploadedImages.forEach((imgObj, idx) => {
      const item = document.createElement('div');
      item.className = 'preview-item';
      item.innerHTML = `
        <img src="${imgObj.data}" alt="${imgObj.name}">
        <button type="button" class="preview-remove-btn" data-index="${idx}" title="삭제">✕</button>
      `;
      previewContainer.appendChild(item);
    });

    document.querySelectorAll('.preview-remove-btn').forEach(btn => {
      btn.addEventListener('click', (e) => {
        e.stopPropagation();
        const removeIdx = parseInt(btn.getAttribute('data-index'), 10);
        uploadedImages.splice(removeIdx, 1);
        renderPreviews();
      });
    });
  };

  btnClearAll.addEventListener('click', (e) => {
    e.stopPropagation();
    uploadedImages = [];
    renderPreviews();
  });

  claimForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    clearError();

    const copayVal = copayInput.value.trim();
    const nonCoveredVal = nonCoveredInput.value.trim();
    const copayCost = copayVal ? parseInt(copayVal, 10) : 0;
    const nonCoveredCost = nonCoveredVal ? parseInt(nonCoveredVal, 10) : 0;

    if (uploadedImages.length === 0 && (copayCost === 0 && nonCoveredCost === 0)) {
      showError('영수증 사진을 등록하거나, 최소 하나 이상의 진료비 금액을 입력해 주세요.');
      return;
    }

    btnSubmit.disabled = true;
    claimForm.classList.add('hidden');
    resultBox.classList.add('hidden');
    loadingBox.classList.remove('hidden');
    loadingTitle.textContent = `AI가 첨부된 ${uploadedImages.length}장의 서류와 약관을 고속 분석 중입니다...`;

    const payload = {
      treatmentType: treatmentTypeSelect.value,
      generation: generationSelect.value,
      copayCost: copayCost,
      nonCoveredCost: nonCoveredCost,
      symptoms: symptomsInput.value.trim() || '허리 요통 및 통증',
      images: uploadedImages.map(img => img.data)
    };

    try {
      const response = await fetch('/api/calculate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });

      if (!response.ok) {
        const errData = await response.json().catch(() => ({}));
        throw new Error(errData.message || `서버 에러 (${response.status})`);
      }

      const result = await response.json();
      renderResult(result);

      loadingBox.classList.add('hidden');
      resultBox.classList.remove('hidden');
      resultBox.scrollIntoView({ behavior: 'smooth', block: 'start' });

    } catch (err) {
      loadingBox.classList.add('hidden');
      claimForm.classList.remove('hidden');
      showError(`⚠️ 분석 처리 중 오류가 발생했습니다: ${err.message}`);
    } finally {
      btnSubmit.disabled = false;
    }
  });

  const renderResult = (data) => {
    const summary = data.summary || {};
    document.getElementById('res-total-cost').textContent = formatWon(summary.total_cost || 0);
    document.getElementById('res-deductible').textContent = formatWon(summary.deductible_amount || 0);
    document.getElementById('res-payout').textContent = formatWon(summary.expected_payout || 0);

    const ocrBanner = document.getElementById('ocr-banner');
    const ocrInfo = document.getElementById('ocr-info');
    if (data.ocr_detected) {
      ocrInfo.textContent = `급여: ${formatWon(data.ocr_detected.copay_cost)} / 비급여: ${formatWon(data.ocr_detected.non_covered_cost)} / 감지 항목: ${data.ocr_detected.symptoms}`;
      ocrBanner.classList.remove('hidden');
    } else {
      ocrBanner.classList.add('hidden');
    }

    document.getElementById('res-basis').textContent = data.calculation_basis || '약관 기준에 따라 산출되었습니다.';

    const docListEl = document.getElementById('res-documents');
    docListEl.innerHTML = '';
    (data.required_documents || []).forEach(doc => {
      const li = document.createElement('li');
      li.textContent = doc;
      docListEl.appendChild(li);
    });

    const tipListEl = document.getElementById('res-tips');
    tipListEl.innerHTML = '';
    (data.advisor_tips || []).forEach(tip => {
      const li = document.createElement('li');
      li.textContent = tip;
      tipListEl.appendChild(li);
    });
  };

  btnRecalc.addEventListener('click', () => {
    resultBox.classList.add('hidden');
    claimForm.classList.remove('hidden');
    claimForm.scrollIntoView({ behavior: 'smooth', block: 'start' });
  });
});