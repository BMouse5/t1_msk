document.addEventListener("DOMContentLoaded", function() {
    const loginModal = document.getElementById("loginModal");
    const registerModal = document.getElementById("registerModal");
    
    const loginButton = document.getElementById("loginButton"); // Кнопка "Вход"
    const registerButton = document.getElementById("registerButton"); // Кнопка "Регистрация"
    
    const closeButtons = document.querySelectorAll(".close-button");

    // Открытие модального окна для входа
    loginButton.addEventListener("click", function(event) {
        event.preventDefault(); // Предотвращаем переход по ссылке
        loginModal.style.display = "block"; // Показываем модальное окно для входа
    });

    // Открытие модального окна для регистрации
    registerButton.addEventListener("click", function(event) {
        event.preventDefault(); // Предотвращаем переход по ссылке
        registerModal.style.display = "block"; // Показываем модальное окно для регистрации
    });

    // Закрытие модальных окон
    closeButtons.forEach(button => {
        button.addEventListener("click", function() {
            loginModal.style.display = "none"; // Скрываем модальное окно для входа
            registerModal.style.display = "none"; // Скрываем модальное окно для регистрации
        });
    });

    // Закрытие модальных окон при клике вне их содержимого
    window.addEventListener("click", function(event) {
        if (event.target === loginModal) {
            loginModal.style.display = "none"; // Скрываем модальное окно для входа
        } else if (event.target === registerModal) {
            registerModal.style.display = "none"; // Скрываем модальное окно для регистрации
        }
    });
});