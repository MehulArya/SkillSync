const screens = document.querySelectorAll(".screen");

function showScreen(id) {
  screens.forEach(screen => {
    screen.classList.remove("active");
  });

  const target = document.getElementById(id);

  if (target) {
    target.classList.add("active");
  }

  window.scrollTo({
    top: 0,
    behavior: "smooth"
  });
}

document.addEventListener("DOMContentLoaded", () => {
  showScreen("home");
});
