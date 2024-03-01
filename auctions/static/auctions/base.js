document.addEventListener("DOMContentLoaded", function () {
  deleteMsg = document.querySelector(".del-msg");
  if (deleteMsg) {
    deleteMsg.onclick = function () {
      this.parentElement.style.display = "none";
    };
  }

  document.querySelector("#msg-admin-link").onclick = function () {
    document
      .querySelector("#send-msg-form")
      .classList.toggle("hidden-hero");
  };
  document.querySelector("#cancel-msg-admin").onclick = function () {
    document
      .querySelector("#send-msg-form")
      .classList.toggle("hidden-hero");
  };

  const helpSubmitBtn = document.querySelector("#help-submit");
  const helpSubmitBtnFaux = document.querySelector("#help-submit-faux");

  helpSubmitBtnFaux.onclick = function () {
    const subjectValue = document.querySelector("#subject").value;
    const subjectText = `-- HELP -- ${subjectValue}`;
    document.querySelector("#subject").value = subjectText;
    helpSubmitBtn.click();
  };
});

setTimeout(function () {
  message = document.querySelector(".message");
  if (message) {
    message.style.display = "none";
  }
}, 3000);

// Check if the user has a theme preference and set it when page loads
if (localStorage.getItem("theme") === "dark") {
  document.querySelector("body").classList.add("dark-mode");
  document.querySelector("body").classList.remove("light-mode");
  document.querySelector("#standard-hero").classList.add("hidden-hero");
  document.querySelector("#standard-hero").classList.remove("visible-hero");
  document.querySelector("#inverted-hero").classList.add("visible-hero");
  document.querySelector("#inverted-hero").classList.remove("hidden-hero");
}

document.querySelector("#theme-mode-toggle").onclick = function () {
  document.querySelector("body").classList.toggle("dark-mode");
  document.querySelector("body").classList.toggle("light-mode");
  document.querySelector("#standard-hero").classList.toggle("visible-hero");
  document.querySelector("#standard-hero").classList.toggle("hidden-hero");
  document.querySelector("#inverted-hero").classList.toggle("hidden-hero");
  document.querySelector("#inverted-hero").classList.toggle("visible-hero");
  localStorage.setItem(
    "theme",
    document.querySelector("body").classList.contains("dark-mode")
      ? "dark"
      : "light"
  );
};
