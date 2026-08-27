document.addEventListener('DOMContentLoaded', function() {
    console.log("pyShelf JS iniciado (Vanilla JS)");

    const selectEl = document.getElementById('collection-select');
    const formEl = document.getElementById('search-form');
    const inputEl = document.getElementById('search-input');

    // 1. Redirección al cambiar de colección en el Select
    if (selectEl) {
        selectEl.addEventListener('change', function(e) {
            const val = e.target.value.trim();
            if (val) {
                window.location.href = `/collection/${encodeURIComponent(val)}`;
            } else {
                window.location.href = '/';
            }
        });
    }

    // 2. Envío del formulario de búsqueda
    if (formEl) {
        formEl.addEventListener('submit', function(e) {
            e.preventDefault();
            const query = inputEl ? inputEl.value.trim() : '';
            const collection = selectEl ? selectEl.value.trim() : '';

            if (query) {
                window.location.href = `/api/search?search=${encodeURIComponent(query)}`;
            } else if (collection) {
                window.location.href = `/collection/${encodeURIComponent(collection)}`;
            } else {
                window.location.href = '/';
            }
        });
    }
});
