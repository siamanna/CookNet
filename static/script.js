function toggleSidebar() {
    var sidebar = document.getElementById("mySidebar");
    var overlay = document.getElementById("overlay");
    sidebar.classList.toggle("open");
    overlay.classList.toggle("active");
}