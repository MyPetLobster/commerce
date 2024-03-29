
// THEME FUNCTIONS


// Body background, text, and hero image color toggle
function setBodyTheme () {
  if (localStorage.getItem("theme") === "dark") {
    document.querySelector("body").classList.add("dark-mode");
    document.querySelector("body").classList.remove("light-mode");
    document.querySelector("#standard-hero").classList.add("hidden");
    document.querySelector("#inverted-hero").classList.remove("hidden");
  } else {
    document.querySelector("body").classList.add("light-mode");
    document.querySelector("body").classList.remove("dark-mode");
    document.querySelector("#standard-hero").classList.remove("hidden");
    document.querySelector("#inverted-hero").classList.add("hidden");
  }
}

// profile.html - delete account button theme
function toggleDeleteAccountButtonTheme() {
  const deleteAccountButton = document.getElementById('delete-account');
  const submitDeleteButton = document.getElementById('submit-delete-btn');
  const reallySubmitDeleteButton = document.getElementById('really-submit-delete-btn');

  if (localStorage.getItem('theme') === 'dark') {
      if (deleteAccountButton) {
        deleteAccountButton.classList.add('del-acct-btn-dark');
        if (deleteAccountButton.classList.contains('del-acct-btn-light')) {
            deleteAccountButton.classList.remove('del-acct-btn-light');
        }
        if (submitDeleteButton) {
            submitDeleteButton.classList.add('del-acct-neon-btn-dark');
            reallySubmitDeleteButton.classList.add('del-acct-neon-btn-dark');
            if (submitDeleteButton.classList.contains('del-acct-neon-btn-light')) {
                submitDeleteButton.classList.remove('del-acct-neon-btn-light');
                reallySubmitDeleteButton.classList.remove('del-acct-neon-btn-light');
            }
        }
      }
  } else {
      if (deleteAccountButton) {
        deleteAccountButton.classList.add('del-acct-btn-light');
        if (deleteAccountButton.classList.contains('del-acct-btn-dark')) {
            deleteAccountButton.classList.remove('del-acct-btn-dark');
        }
        if (submitDeleteButton) {
            submitDeleteButton.classList.add('del-acct-neon-btn-light');
            reallySubmitDeleteButton.classList.add('del-acct-neon-btn-light');
            if (submitDeleteButton.classList.contains('del-acct-neon-btn-dark')) {
                submitDeleteButton.classList.remove('del-acct-neon-btn-dark');
                reallySubmitDeleteButton.classList.remove('del-acct-neon-btn-dark');
            }
        }
      }
  }

}

// messages.html - sender link theme 
function toggleMessageSenderLinkTheme() {
  if (localStorage.getItem("theme") === "dark") {
    document.querySelector(".msg-sender-link").classList.remove("msg-sender-link-light");
    document.querySelector(".msg-sender-link").classList.add("msg-sender-link-dark");
  } else { 
    document.querySelector(".msg-sender-link").classList.remove("msg-sender-link-dark");
    document.querySelector(".msg-sender-link").classList.add("msg-sender-link-light");
  }
}
// messages.html - select every other .message-div and darken the background slightly
function toggleMessageColors() {
  messageDivs = document.querySelectorAll(".message-div");
  if (messageDivs.length !== 0) {
    lightModeColorOne = "#efefef";
    lightModeColorTwo = "#d0d0d0";
    darkModeColorOne = "#2b2c2e";
    darkModeColorTwo = "#353638";

    if (localStorage.getItem("theme") === "dark") {
      modColorOne = darkModeColorOne;
      modColorTwo = darkModeColorTwo;
    } else {
      modColorOne = lightModeColorOne;
      modColorTwo = lightModeColorTwo;
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
// messages.html - all theme
function toggleMessagePageTheme() { 
  const messagePageCheck = document.querySelector("#this-is-message-page");
  if (messagePageCheck) {
    toggleMessageColors();
    toggleMessageSenderLinkTheme();
  }
}

// search.html - search result color theme
function toggleSearchResultColorTheme() {
  const searchResultDesc = document.querySelectorAll('.search-result-desc');
  if (searchResultDesc) {
    if (localStorage.getItem('theme') === 'dark') {
        searchResultDesc.forEach(desc => {
            desc.classList.add('search-result-desc-dark');
            desc.classList.remove('search-result-desc-light');  
        });
    } else {
        searchResultDesc.forEach(desc => {  
            desc.classList.add('search-result-desc-light');
            desc.classList.remove('search-result-desc-dark');
        });
    }
  }
}

// index.html, listings.html, profile.html (bids) - time left text theme
function toggleTimeLeftTextTheme() {
  const timeLeftText = document.querySelectorAll(".dynamic-time-left-text");
  if (timeLeftText) {
    if (localStorage.getItem("theme") === "dark") {
      timeLeftText.forEach((text) => {
        text.classList.add("time-left-dark-mode")
        text.classList.remove("time-left-light-mode")
      });
    } else {
      timeLeftText.forEach((text) => {
        text.classList.add("time-left-light-mode")
        text.classList.remove("time-left-dark-mode")
      });
    }
  }
}

// transactions.html - toggle the table colors
function toggleTransactionTheme() {
  if (document.querySelector("#this-is-transactions-page")) {
    if (localStorage.getItem("theme") === "dark") {
      document.querySelector("#bids-table").classList.add("dark-mode-table");
      document.querySelector("#bids-table").classList.remove("light-mode-table");
      document.querySelector("#transactions-table").classList.add("dark-mode-table");
      document.querySelector("#transactions-table").classList.remove("light-mode-table");
  } else {
      document.querySelector("#bids-table").classList.add("light-mode-table");
      document.querySelector("#bids-table").classList.remove("dark-mode-table");
      document.querySelector("#transactions-table").classList.add("light-mode-table");
      document.querySelector("#transactions-table").classList.remove("dark-mode-table");

    } 
  } 
}

// Toggle the theme mode when the footer button is clicked
function toggleThemeMode() {
  document.querySelector("#theme-mode-toggle").onclick = function () {
    document.querySelector("body").classList.toggle("dark-mode");
    document.querySelector("body").classList.toggle("light-mode");
    document.querySelector("#standard-hero").classList.toggle("hidden");
    document.querySelector("#inverted-hero").classList.toggle("hidden");
    
    localStorage.setItem(
      "theme",
      document.querySelector("body").classList.contains("dark-mode")
        ? "dark"
        : "light"
    );

    // Other theme mode toggles
    toggleTransactionTheme();
    toggleDeleteAccountButtonTheme();
    toggleSearchResultColorTheme();
    toggleTimeLeftTextTheme();
    toggleMessagePageTheme();
  };
}




// BASE FUNCTIONS

// layout.html - Django Alert close button
function closeDjangoAlert() {
  // Alert message divs will disappear after 4.5 seconds
  setTimeout(function () {
    message = document.querySelector(".alert-div");
    if (message) {
      message.style.display = "none";
    }
  }, 4500);

  delX = document.querySelector('.del-msg');
  error_message = document.querySelector('.alert-div');

  if (delX) {
      delX.addEventListener('click', () => {
          error_message.style.display = 'none';
      });
  }
}

// layout.html - navbar - hidden message count passed from Django
function checkForUnreadMessages() {
  const isUnreadMessages = document.getElementById("unread-message-count"); 
  if (isUnreadMessages) {
    const unreadMessages = parseInt(isUnreadMessages.innerText);
    if (unreadMessages > 0) {
      return unreadMessages;
    } else {
      return 0;
    }
  }
}

// layout.html - navbar - nav item active class
function setActiveNavItem () {
  document.onreadystatechange = () => {
    if (document.readyState === "complete") {

      // Get localStorage value for activePage and make the appropriate link bold. 
      const activePage = localStorage.getItem("activePage");
      const navLinks = document.querySelectorAll(".nav-link");

      if (activePage !== null && activePage !== 'non-nav') {
        navLinks.forEach((link) => {
          if (link.id === `nav-${activePage}`) {
            link.classList.add("active-nav");
          } else {
            link.classList.remove("active-nav");
          }
        });
      } else {
        return;
      }
    } else {
      return;
    }
  }
}

// layout.html - navbar - mail icon display
function handleMailIconDisplay() {
  const mailIconDefault = document.getElementById("mail-icon-default");
  const mailIconHover = document.getElementById("mail-icon-hover");
  const mailIconUnread = document.getElementById("mail-icon-unread");
  const mailIconDiv = document.querySelector(".mail-icon-div");
  const unreadMessageCount = checkForUnreadMessages();
  const unreadMessageDisplay = document.getElementById("unread-count");

  const unreadMessages = unreadMessageCount > 0;

  if (unreadMessages) {
    mailIconDefault.classList.add("hidden");
    mailIconUnread.classList.remove("hidden");
  }

  const handleMouseOver = () => {
    mailIconDefault.classList.add("hidden");
    mailIconHover.classList.remove("hidden");
    if (unreadMessages) {
      mailIconUnread.classList.add("hidden");
      unreadMessageDisplay.classList.remove("hidden");
    }
  };

  const handleMouseOut = () => {
    mailIconHover.classList.add("hidden");
    if (unreadMessages) {
      mailIconUnread.classList.remove("hidden");
      unreadMessageDisplay.classList.add("hidden");
    } else {
      mailIconDefault.classList.remove("hidden");
    }
  };

  if (mailIconDiv) {
    mailIconDiv.addEventListener("mouseover", handleMouseOver);
    mailIconDiv.addEventListener("mouseout", handleMouseOut);
  }
}

// layout.html - navbar - dropdown menu
function handleNavDropdown() {
  
  // Dropdown Logout/My Yard links
  const fullDropDownDiv = document.querySelector("#full-dropdown-div");
  const statusProfile = document.querySelector("#status-profile");

  // "hi, username" text highlighted on hover
  if (fullDropDownDiv) {
    fullDropDownDiv.addEventListener("mouseover", () => {
        statusProfile.classList.add("active-dropdown-header");
    });
    fullDropDownDiv.addEventListener("mouseout", () => {
        statusProfile.classList.remove("active-dropdown-header");
    });
  }

  const dropdown = document.querySelector(".dropdown")
  if (dropdown) {
    dropdown.addEventListener("click", () => {
        dropdown.classList.toggle("active")
    });
  

    // click anywhere outside the dropdown to close it
    document.addEventListener('click', function(event) {
      const dropdown = document.querySelector('.dropdown');
      if (!dropdown.contains(event.target)) {
          dropdown.classList.remove('active');
      }
    });
  }
}

// layout.html - navbar - if user clicks balance link, scroll to balance part of profile page
function scrollToBalance() {
    // Scroll to balance part of profile page if user clicks balance link
    const balanceLink = document.querySelector('.balance-link');
    if (balanceLink) {
      balanceLink.addEventListener('click', () => {
          localStorage.setItem('fromBalanceLink', 'true');
      });
    }
}

// layout.html, about.html - message admin form
function handleMessageAdmin() {
  const messageAdminBtn = document.querySelector("#msg-admin-link");
  const messageAdminForm = document.querySelector("#msg-admin-form");
  const cancelMsgAdminBtn = document.querySelector("#cancel-msg-admin");

  if (messageAdminBtn) {
    messageAdminBtn.addEventListener("click", () => {
      messageAdminForm.classList.remove("hidden");
      messageAdminForm.classList.add("send-msg-form");
    });

    cancelMsgAdminBtn.addEventListener("click", () => {
      messageAdminForm.classList.add("hidden");
      messageAdminForm.classList.remove("send-msg-form");
    });

    const helpSubmitBtn = document.querySelector("#help-submit");
    const helpSubmitBtnFaux = document.querySelector("#help-submit-faux");

    helpSubmitBtnFaux.addEventListener("click", () => {
      const subjectValue = document.querySelector("#subject").value;
      const subjectText = `-- HELP -- ${subjectValue}`;
      document.querySelector("#subject").value = subjectText;
      helpSubmitBtn.click();
    });
  }

  // Message admin link in FAQ
  const messageAdminLinkTwo = document.querySelector("#msg-admin-link-two");
  if (messageAdminLinkTwo) {
    messageAdminLinkTwo.addEventListener("click", () => {
      messageAdminForm.classList.remove("hidden");
      messageAdminForm.classList.add("send-msg-form");
    });
  }
}

// messages.html - show/hide full message
function showHideFullMessage() {
  const messageDivs = document.querySelectorAll(".message-div");
  messageDivs.forEach((div) => {
    div.onclick = function (event) {
      const fullMessage = this.nextElementSibling;
      const rect = this.getBoundingClientRect();
      const clickX = event.clientX - rect.left;
      const clickY = event.clientY - rect.top;

      // Exclude top right corner where mark-as-read button is
      if (clickX > rect.width - 120 && clickY < 75) {
        return;
      }

      // Toggle visibility of the div below each msg with reply and delete buttons
      const replyDeleteDivs = this.nextElementSibling.nextElementSibling;
      replyDeleteDivs.classList.toggle("hidden");

      // Hide the collapsed message and show the full message
      fullMessage.classList.toggle("hidden");
      div.classList.toggle("hidden");

      // Click to hide the full message and show the collapsed message
      fullMessage.onclick = function () {
        fullMessage.classList.toggle("hidden");
        div.classList.toggle("hidden");
        replyDeleteDivs.classList.toggle("hidden");
      };
    };
  });
}




// Run all functions when the DOM is fully loaded
document.addEventListener("DOMContentLoaded", function () {
  setActiveNavItem();
  handleNavDropdown();
  closeDjangoAlert();
  handleMailIconDisplay();
  handleMessageAdmin();
  showHideFullMessage();

  setBodyTheme();
  scrollToBalance();
  toggleDeleteAccountButtonTheme();
  toggleMessagePageTheme();
  toggleSearchResultColorTheme();
  toggleTimeLeftTextTheme();
  toggleTransactionTheme();
  toggleThemeMode();
});
