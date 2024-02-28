const showFullListings = document.querySelector(".full-listings")
const showTitleOnly = document.querySelector(".title-only")

const shortListings = document.querySelectorAll(".short-listings")
const longListings = document.querySelectorAll(".long-listings")

var fullOrTitle = localStorage.getItem("fullOrTitle")


showFullListings.addEventListener("click", () => {
    showFull();
});

showTitleOnly.addEventListener("click", () => {
    showTitle();
});


function showFull() {
  showFullListings.classList.add("opt-selected");
  showFullListings.classList.remove("opt-not-selected");
  showTitleOnly.classList.add("opt-not-selected");
  showTitleOnly.classList.remove("opt-selected");

  shortListings.forEach((listing) => {
    listing.classList.add("hidden-listings");
    listing.classList.remove("visible-listings");
  });

  longListings.forEach((listing) => {
    listing.classList.add("visible-listings");
    listing.classList.remove("hidden-listings");
  });

  localStorage.setItem("fullOrTitle", "full");
}

function showTitle() {
  showTitleOnly.classList.add("opt-selected");
  showTitleOnly.classList.remove("opt-not-selected");
  showFullListings.classList.add("opt-not-selected");
  showFullListings.classList.remove("opt-selected");

  longListings.forEach((listing) => {
    listing.classList.add("hidden-listings");
    listing.classList.remove("visible-listings");
  });

  shortListings.forEach((listing) => {
    listing.classList.add("visible-listings");
    listing.classList.remove("hidden-listings");
  });

  localStorage.setItem("fullOrTitle", "title");
}


// check length of the description, if over 125 characters, truncate and add a link to expand
var allDescriptions = document.querySelectorAll(".full-description")
var allTruncatedDescriptions = document.querySelectorAll(".truncated-description")
for (var i = 0; i < allDescriptions.length; i++) {
    if (allDescriptions[i].innerText.length > 200) {
        allDescriptions[i].classList.add("hidden-description")
        allDescriptions[i].classList.remove("visible-description")
        allTruncatedDescriptions[i].classList.add("visible-description")
        allTruncatedDescriptions[i].classList.remove("hidden-description")
    }
}

// add event listener to expand the description
document.querySelectorAll(".expand-link").forEach((link) => {
    link.addEventListener("click", () => {
        link.parentElement.classList.add("hidden-description")
        link.parentElement.classList.remove("visible-description")
        
        link.parentElement.previousElementSibling.classList.add("pointer")    
        link.parentElement.previousElementSibling.classList.remove("hidden-description")
        link.parentElement.previousElementSibling.classList.add("visible-description")

        link.parentElement.previousElementSibling.addEventListener("click", () => {
            link.parentElement.previousElementSibling.classList.add("hidden-description")
            link.parentElement.previousElementSibling.classList.remove("visible-description")
            link.parentElement.previousElementSibling.classList.remove("pointer")
            link.parentElement.classList.remove("hidden-description")
            link.parentElement.classList.add("visible-description")
        });
    });
});


document.addEventListener("DOMContentLoaded", () => {
  if (fullOrTitle === "full") {
    showFull();
  } else if (fullOrTitle === "title") {
    showTitle();
  }
});