document.addEventListener('DOMContentLoaded', function() {
    const selectEl = document.getElementById('collection-select');
    const searchForm = document.getElementById('search-form');

    // 1. Redirección al cambiar de colección
    if (selectEl) {
        selectEl.addEventListener('change', function(e) {
            const val = e.target.value.trim();
            window.location.href = val ? `/collection/${encodeURIComponent(val)}` : '/';
        });
    }

    // 2. Feedback visual al enviar la búsqueda
    if (searchForm) {
        searchForm.addEventListener('submit', function() {
            const submitBtn = searchForm.querySelector('button[type="submit"]');
            const inputEl = searchForm.querySelector('input[name="search"]');

            if (submitBtn && inputEl && inputEl.value.trim() !== '') {
                // Activa el spinner nativo de Pico CSS en el botón
                submitBtn.setAttribute('aria-busy', 'true');
                submitBtn.textContent = 'Buscando...';
                submitBtn.disabled = true;
            }
        });
    }
});
