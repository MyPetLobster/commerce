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
      .classList.toggle("hidden");
  };
  document.querySelector("#cancel-msg-admin").onclick = function () {
    document
      .querySelector("#send-msg-form")
      .classList.toggle("hidden");
  };

  const helpSubmitBtn = document.querySelector("#help-submit");
  const helpSubmitBtnFaux = document.querySelector("#help-submit-faux");

  helpSubmitBtnFaux.onclick = function () {
    const subjectValue = document.querySelector("#subject").value;
    const subjectText = `-- HELP -- ${subjectValue}`;
    document.querySelector("#subject").value = subjectText;
    helpSubmitBtn.click();
  };

  const messagePageCheck = document.querySelector("#this-is-message-page");
  if (messagePageCheck) {
    changeMessageColors();
  }
});

setTimeout(function () {
  message = document.querySelector(".message");
  if (message) {
    message.style.display = "none";
  }
}, 3000);

// DARK and LIGHT MODES
// Check if the user has a theme preference and set it when page loads
if (localStorage.getItem("theme") === "dark") {
  document.querySelector("body").classList.add("dark-mode");
  document.querySelector("body").classList.remove("light-mode");
  document.querySelector("#standard-hero").classList.add("hidden");
  document.querySelector("#standard-hero").classList.remove("visible");
  document.querySelector("#inverted-hero").classList.add("visible");
  document.querySelector("#inverted-hero").classList.remove("hidden");
}


document.querySelector("#theme-mode-toggle").onclick = function () {
  document.querySelector("body").classList.toggle("dark-mode");
  document.querySelector("body").classList.toggle("light-mode");
  document.querySelector("#standard-hero").classList.toggle("visible");
  document.querySelector("#standard-hero").classList.toggle("hidden");
  document.querySelector("#inverted-hero").classList.toggle("hidden");
  document.querySelector("#inverted-hero").classList.toggle("visible");
  localStorage.setItem(
    "theme",
    document.querySelector("body").classList.contains("dark-mode")
      ? "dark"
      : "light"
  );

  // change the colors of the message divs if they exist
  const messagePageCheck = document.querySelector("#this-is-message-page");
  if (messagePageCheck) {
    changeMessageColors();
  }
};



// select every other .message-div and darken the background slightly
function changeMessageColors() {
    messageDivs = document.querySelectorAll('.message-div');
    lightModeColorOne = '#ded9dd';
    lightModeColorTwo = '#e8e5e8';
    darkModeColorOne = '#454144';
    darkModeColorTwo = '#5e545c';

    if (localStorage.getItem('theme') === 'light') {
        modColorOne = lightModeColorOne;
        modColorTwo = lightModeColorTwo;
    } 
    if (localStorage.getItem('theme') === 'dark') {
        modColorOne = darkModeColorOne;
        modColorTwo = darkModeColorTwo;
    }

    messageDivs.forEach((div, index) => {
        if (index % 2 === 0) {
            div.style.backgroundColor = modColorOne;
        } else {
            div.style.backgroundColor = modColorTwo;
        }
    });
}