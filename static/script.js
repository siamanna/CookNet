function toggleSidebar() {
    var sidebar = document.getElementById("mySidebar");
    var overlay = document.querySelector(".overlay");
    sidebar.classList.toggle("open");
    overlay.classList.toggle("active");
}

document.addEventListener('DOMContentLoaded', function() {
    var menuButton = document.querySelector('.menu-button');
    if (menuButton) {
        menuButton.addEventListener('click', toggleSidebar);
    }

    var overlay = document.querySelector('.overlay');
    if (overlay) {
        overlay.addEventListener('click', toggleSidebar);
    }
});
