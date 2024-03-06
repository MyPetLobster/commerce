setTimeout(function () {
  message = document.querySelector(".alert-div");
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
  if (document.querySelector("#this-is-transactions-page")) {
    setTransactionDarkMode();
  }
}

if (localStorage.getItem("theme") === "light") {
  document.querySelector("body").classList.add("light-mode");
  document.querySelector("body").classList.remove("dark-mode");
  document.querySelector("#standard-hero").classList.add("visible");
  document.querySelector("#standard-hero").classList.remove("hidden");
  document.querySelector("#inverted-hero").classList.add("hidden");
  document.querySelector("#inverted-hero").classList.remove("visible");
  if (document.querySelector("#this-is-transactions-page")) {
    setTransactionLightMode();
  }
}

document.querySelector("#theme-mode-toggle").onclick = function () {
  document.querySelector("body").classList.toggle("dark-mode");
  document.querySelector("body").classList.toggle("light-mode");
  document.querySelector("#standard-hero").classList.toggle("visible");
  document.querySelector("#standard-hero").classList.toggle("hidden");
  document.querySelector("#inverted-hero").classList.toggle("hidden");
  document.querySelector("#inverted-hero").classList.toggle("visible");
  if (document.querySelector("#this-is-transactions-page")) {
    toggleTransactionMode();
  }
  
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

// TRANSACTIONS PAGE THEME MODE FUNCTIONS
function setTransactionDarkMode() {
  document.querySelector("#bids-table").classList.add("dark-mode-table");
  document.querySelector("#bids-table").classList.remove("light-mode-table");
  document.querySelector("#transactions-table").classList.add("dark-mode-table");
  document.querySelector("#transactions-table").classList.remove("light-mode-table"); 
}

function setTransactionLightMode() {
  document.querySelector("#bids-table").classList.add("light-mode-table");
  document.querySelector("#bids-table").classList.remove("dark-mode-table");
  document.querySelector("#transactions-table").classList.add("light-mode-table");
  document.querySelector("#transactions-table").classList.remove("dark-mode-table");
}

function toggleTransactionMode() {
  document.querySelector("#bids-table").classList.toggle("dark-mode-table");
  document.querySelector("#bids-table").classList.toggle("light-mode-table");
  document.querySelector("#transactions-table").classList.toggle("dark-mode-table");
  document.querySelector("#transactions-table").classList.toggle("light-mode-table");
}



document.addEventListener("DOMContentLoaded", function () {
  const mailIconDefault = document.getElementById("mail-icon-default");
  const mailIconHover = document.getElementById("mail-icon-hover");
  const mailIconUnread = document.getElementById("mail-icon-unread");
  const mailIconDiv = document.querySelector(".mail-icon-div");
  const unreadMessageCount = checkForUnreadMessages();
  const unreadMessageDisplay = document.getElementById("unread-count");

  let unreadMessages = false;
  if (unreadMessageCount > 0) {
    unreadMessages = true;
  }

  if (unreadMessages) {
    mailIconDefault.classList.add("hidden");
    mailIconDefault.classList.remove("visible");
    mailIconUnread.classList.add("visible");
    mailIconUnread.classList.remove("hidden");
  }

  if (unreadMessages) {
    mailIconDiv.onmouseover = function () {
      mailIconDefault.classList.add("hidden");
      mailIconDefault.classList.remove("visible");
      mailIconUnread.classList.add("hidden");
      mailIconUnread.classList.remove("visible");
      mailIconHover.classList.remove("hidden");
      mailIconHover.classList.add("visible");
      unreadMessageDisplay.classList.add("visible");
      unreadMessageDisplay.classList.remove("hidden");
    };
    mailIconDiv.onmouseout = function () {
      mailIconUnread.classList.add("visible");
      mailIconUnread.classList.remove("hidden");
      unreadMessageDisplay.classList.add("hidden");
      unreadMessageDisplay.classList.remove("visible");
      mailIconHover.classList.add("hidden");
      mailIconHover.classList.remove("visible");
    };
  } else {
    mailIconDiv.onmouseover = function () {
      mailIconDefault.classList.add("hidden");
      mailIconDefault.classList.remove("visible");
      mailIconUnread.classList.add("hidden");
      mailIconUnread.classList.remove("visible");
      mailIconHover.classList.remove("hidden");
      mailIconHover.classList.add("visible");
    };
    mailIconDiv.onmouseout = function () {
      mailIconDefault.classList.remove("hidden");
      mailIconDefault.classList.add("visible");
      mailIconHover.classList.add("hidden");
      mailIconHover.classList.remove("visible");
    }
  }

  deleteMsg = document.querySelector(".del-msg");
  if (deleteMsg) {
    deleteMsg.onclick = function () {
      this.parentElement.style.display = "none";
    };
  }

  const messageAdminBtn = document.querySelector("#msg-admin-link");
  const messageAdminForm = document.querySelector("#msg-admin-form");
  const cancelMsgAdminBtn = document.querySelector("#cancel-msg-admin");

  messageAdminBtn.onclick = function () {
    messageAdminForm.classList.remove("hidden");
    messageAdminForm.classList.add("send-msg-form");
  };

  cancelMsgAdminBtn.onclick = function () {
    messageAdminForm.classList.add("hidden");
    messageAdminForm.classList.remove("send-msg-form");
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
    showHideFullMessage();
  }
});

// FUNCTIONS

// select every other .message-div and darken the background slightly
function changeMessageColors() {
  messageDivs = document.querySelectorAll(".message-div");
  if (messageDivs.length !== 0) {
    lightModeColorOne = "#efefef";
    lightModeColorTwo = "#d0d0d0";
    darkModeColorOne = "#2b2c2e";
    darkModeColorTwo = "#353638";

    if (localStorage.getItem("theme") === "light") {
      modColorOne = lightModeColorOne;
      modColorTwo = lightModeColorTwo;
    }
    if (localStorage.getItem("theme") === "dark") {
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
  messageDivsFull = document.querySelectorAll(".message-div-full");
  if (messageDivsFull.length !== 0) {
    messageDivsFull.forEach((div, index) => {
      if (index % 2 === 0) {
        div.style.backgroundColor = modColorOne;
      } else {
        div.style.backgroundColor = modColorTwo;
      }
    });
  }
}

function showHideFullMessage() {
  const messageDivs = document.querySelectorAll(".message-div");
  messageDivs.forEach((div) => {
    div.onclick = function (event) {
      const fullMessage = this.nextElementSibling;
      const rect = this.getBoundingClientRect();
      const clickX = event.clientX - rect.left;
      const clickY = event.clientY - rect.top;

      // Exclude top right corner (e.g., 10px from the top and 10px from the right)
      if (clickX > rect.width - 120 && clickY < 75) {
        return;
      }

      const replyDeleteDivs = this.nextElementSibling.nextElementSibling;
      replyDeleteDivs.classList.toggle("hidden");

      fullMessage.classList.toggle("hidden");
      fullMessage.classList.toggle("visible");
      div.classList.toggle("hidden");

      fullMessage.onclick = function () {
        fullMessage.classList.toggle("hidden");
        fullMessage.classList.toggle("visible");
        div.classList.toggle("hidden");
        replyDeleteDivs.classList.toggle("hidden");
      };
    };
  });
}

function checkForUnreadMessages() {
  const isUnreadMessages = document.getElementById("unread-message-count");
  const unreadMessages = parseInt(isUnreadMessages.innerText);
  if (unreadMessages > 0) {
    return unreadMessages;
  } else {
    return 0;
  }
}

