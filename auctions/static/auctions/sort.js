document.addEventListener("DOMContentLoaded", function () {
  const sortByOptions = document.querySelectorAll(".sort-by-option");
  window.scrollTo(0, localStorage.getItem("scrollY"));

  sortByOptions.forEach((option) => {
    option.addEventListener("click", function () {
      const sortBy = this.dataset.sortBy;
      const direction =
        localStorage.getItem("sort-by-direction") === "asc" ? "desc" : "asc";
      localStorage.setItem("sort-by", sortBy);
      localStorage.setItem("sort-by-direction", direction);
      localStorage.setItem("scrollY", window.scrollY);
      document.querySelector("#sort-by").value = sortBy;
      document.querySelector("#sort-by-direction").value = direction;
      document.querySelector(".sort-by-form").submit();
    });
  });

  const updateSortUI = () => {
    const sortBy = localStorage.getItem("sort-by");
    const direction = localStorage.getItem("sort-by-direction");

    sortByOptions.forEach((option) => {
      const optionSortBy = option.dataset.sortBy;
      if (optionSortBy === sortBy) {
        option.classList.add("sort-by-active");
        if (sortBy === "title" || sortBy === "seller") {
          option.innerHTML = `${
            direction === "asc"
              ? `&darr; ${option.innerHTML} (A-Z)`
              : `&uarr; ${option.innerHTML} (Z-A)`
          }`;
        } else if (sortBy === "date") {
          option.innerHTML = `${
            direction === "asc"
              ? `&uarr; ${option.innerHTML} (Old-New)`
              : `&darr; ${option.innerHTML} (New-Old)`
          }`;
        } else if (sortBy === "price") {
          option.innerHTML = `${
            direction === "asc"
              ? `&darr; ${option.innerHTML} (Low-High)`
              : `&uarr; ${option.innerHTML} (High-Low)`
          }`;
        }
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

  if (goToClosed) {
    goToClosed.addEventListener("click", () => {
      closedListings.scrollIntoView();
    });
  }

  backToTop.addEventListener("click", () => {
    activeListings.scrollIntoView();
  });
});





