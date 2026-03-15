function toggleSidebar(){

    const sidebar = document.getElementById("sidebar");
    const overlay = document.getElementById("sidebarOverlay");

    sidebar.classList.toggle("sidebar-open");
    overlay.classList.toggle("active");

}