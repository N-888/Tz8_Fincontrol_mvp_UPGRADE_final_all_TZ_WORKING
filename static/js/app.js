// Дожидаемся полной загрузки DOM перед запуском кода.
document.addEventListener("DOMContentLoaded", () => {
    // Находим все bootstrap tooltip-элементы на странице.
    const tooltipTriggerList = document.querySelectorAll('[data-bs-toggle="tooltip"]');

    // Инициализируем каждый найденный tooltip.
    tooltipTriggerList.forEach((tooltipTriggerEl) => {
        // Создаём bootstrap tooltip для текущего элемента.
        new bootstrap.Tooltip(tooltipTriggerEl);
    });
});
