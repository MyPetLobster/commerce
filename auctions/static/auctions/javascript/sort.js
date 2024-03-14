document.addEventListener("DOMContentLoaded", function () {
  const sortByOptions = document.querySelectorAll(".sort-by-option");

  const handleSortByOptionClick = (event) => {
    const sortBy = event.target.dataset.sortBy;
    const direction =
      localStorage.getItem("sort-by-direction") === "asc" ? "desc" : "asc";
    localStorage.setItem("sort-by", sortBy);
    localStorage.setItem("sort-by-direction", direction);
    document.querySelector("#sort-by").value = sortBy;
    document.querySelector("#sort-by-direction").value = direction;
    document.querySelector(".sort-by-form").submit();
  };

  sortByOptions.forEach((option) => {
    option.addEventListener("click", handleSortByOptionClick);
  });

  const updateSortUI = () => {
    const sortBy = localStorage.getItem("sort-by");
    const direction = localStorage.getItem("sort-by-direction");

    sortByOptions.forEach((option) => {
      const optionSortBy = option.dataset.sortBy;
      if (optionSortBy === sortBy) {
        option.classList.add("sort-by-active");
        let directionText = "";
        if (sortBy === "title" || sortBy === "seller") {
          directionText = direction === "asc" ? "A-Z" : "Z-A";
        } else if (sortBy === "date") {
          directionText = direction === "asc" ? "Old-New" : "New-Old";
        } else if (sortBy === "price") {
          directionText = direction === "asc" ? "Low-High" : "High-Low";
        }
        option.innerHTML = `${direction === "asc" ? "&darr;" : "&uarr;"} ${
          option.innerHTML
        } (${directionText})`;
      } else {
        option.classList.remove("sort-by-active");
      }
    });
  };

  updateSortUI();

  const activeListings = document.getElementById("active-listings");
  const closedListings = document.getElementById("closed-listings");
  const goToClosed = document.getElementById("go-to-closed");
  const backToTop = document.getElementById("back-to-top");

  const handleGoToClosedClick = () => {
    closedListings.scrollIntoView();
  };

  const handleBackToTopClick = () => {
    activeListings.scrollIntoView();
  };

  if (goToClosed) {
    goToClosed.addEventListener("click", handleGoToClosedClick);
  }

  backToTop.addEventListener("click", handleBackToTopClick);

  const navBar = document.querySelectorAll(".nav");

  const handleNavBarClick = () => {
    localStorage.setItem("sort-by", "date");
    localStorage.setItem("sort-by-direction", "desc");
    updateSortUI();
  };

  navBar.forEach((nav) => {
    nav.addEventListener("click", handleNavBarClick);
  });
});