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
    listing.classList.add("hidden");
    listing.classList.remove("visible");
  });

  longListings.forEach((listing) => {
    listing.classList.add("visible");
    listing.classList.remove("hidden");
  });

  localStorage.setItem("fullOrTitle", "full");
}

function showTitle() {
  showTitleOnly.classList.add("opt-selected");
  showTitleOnly.classList.remove("opt-not-selected");
  showFullListings.classList.add("opt-not-selected");
  showFullListings.classList.remove("opt-selected");

  longListings.forEach((listing) => {
    listing.classList.add("hidden");
    listing.classList.remove("visible");
  });

  shortListings.forEach((listing) => {
    listing.classList.add("visible");
    listing.classList.remove("hidden");
  });

  localStorage.setItem("fullOrTitle", "title");
}


// check length of the description, if over 125 characters, truncate and add a link to expand
var allDescriptions = document.querySelectorAll(".full-description")
var allTruncatedDescriptions = document.querySelectorAll(".truncated-description")
for (var i = 0; i < allDescriptions.length; i++) {
    if (allDescriptions[i].innerText.length > 200) {
        allDescriptions[i].classList.add("hidden")
        allDescriptions[i].classList.remove("visible")
        allTruncatedDescriptions[i].classList.add("visible")
        allTruncatedDescriptions[i].classList.remove("hidden")
    }
}

// add event listener to expand the description
document.querySelectorAll(".expand-link").forEach((link) => {
    link.addEventListener("click", () => {
        link.parentElement.classList.add("hidden")
        link.parentElement.classList.remove("visible")
        
        link.parentElement.previousElementSibling.classList.add("pointer")    
        link.parentElement.previousElementSibling.classList.remove("hidden")
        link.parentElement.previousElementSibling.classList.add("visible")

        link.parentElement.previousElementSibling.addEventListener("click", () => {
            link.parentElement.previousElementSibling.classList.add("hidden")
            link.parentElement.previousElementSibling.classList.remove("visible")
            link.parentElement.previousElementSibling.classList.remove("pointer")
            link.parentElement.classList.remove("hidden")
            link.parentElement.classList.add("visible")
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

// NUMBER OF LISTINGS TO DISPLAY

// numberOfListings will control how many listings are displayed at a time across index and listings pages
const numberOfListings = 10;

// Function to handle show more button click
function handleShowMore(listingListItems, showMore, visibleListings) {
    listingListItems.forEach((listing, index) => {
        if (index < visibleListings) {
            listing.classList.add('display-listing');
            listing.classList.remove('hide-listing');
        }
    });
    if (visibleListings >= listingListItems.length) {
        showMore.classList.add('hidden');
    }
}

// Function to initialize show more functionality
function initializeShowMore(listingListItems, showMore, itemCount) {
    let visibleListings = numberOfListings;
    showMore.textContent = `Show next ${numberOfListings} listings`;

    if (itemCount <= numberOfListings) {
        showMore.classList.add('hidden');
    }

    handleShowMore(listingListItems, showMore, visibleListings);

    showMore.addEventListener('click', () => {
        visibleListings += numberOfListings;
        handleShowMore(listingListItems, showMore, visibleListings);
    });
}

// Function to initialize show more for active listings
function initializeActiveListings() {
    const listingListItems = document.querySelectorAll('.li-listing-div');
    const showMore = document.getElementById('show-more');
    initializeShowMore(listingListItems, showMore, listingListItems.length);
}

// Function to initialize show more for closed listings
function initializeClosedListings() {
    const allClosedListings = document.querySelectorAll('.li-listing-closed-div');
    const showMoreClosed = document.getElementById('show-more-closed');
    initializeShowMore(allClosedListings, showMoreClosed, allClosedListings.length);
}

// Function to check and initialize based on localStorage value
function initializeShowMoreBasedOnLocalStorage() {
    if (localStorage.getItem('fullOrTitle') === 'full' || localStorage.getItem('fullOrTitle') === null) {
        initializeActiveListings();
        initializeClosedListings();
    } else {
        const showMore = document.getElementById('show-more');
        showMore.classList.add('hidden');
    }
}

// Initialize show more functionality
initializeShowMoreBasedOnLocalStorage();
