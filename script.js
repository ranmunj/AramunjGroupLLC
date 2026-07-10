const leadForm = document.querySelector("#leadForm");
const formStatus = document.querySelector("#formStatus");
const navToggle = document.querySelector(".nav-toggle");
const header = document.querySelector("[data-elevate]");
const navLinks = document.querySelectorAll("nav a");
const revealItems = document.querySelectorAll(".reveal");

const updateHeader = () => {
  header?.classList.toggle("is-elevated", window.scrollY > 12);
};

updateHeader();
window.addEventListener("scroll", updateHeader, { passive: true });

navToggle?.addEventListener("click", () => {
  const isOpen = document.body.classList.toggle("nav-open");
  navToggle.setAttribute("aria-expanded", String(isOpen));
});

navLinks.forEach((link) => {
  link.addEventListener("click", () => {
    document.body.classList.remove("nav-open");
    navToggle?.setAttribute("aria-expanded", "false");
  });
});

if ("IntersectionObserver" in window) {
  const observer = new IntersectionObserver(
    (entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          entry.target.classList.add("is-visible");
          observer.unobserve(entry.target);
        }
      });
    },
    { rootMargin: "0px 0px -10% 0px", threshold: 0.1 },
  );

  revealItems.forEach((item) => observer.observe(item));
} else {
  revealItems.forEach((item) => item.classList.add("is-visible"));
}

leadForm?.addEventListener("submit", async (event) => {
  event.preventDefault();
  formStatus.textContent = "Submitting your inquiry...";

  const payload = Object.fromEntries(new FormData(leadForm).entries());

  try {
    const response = await fetch("/api/leads", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const result = await response.json();

    if (!response.ok) {
      throw new Error(result.error || "Unable to send inquiry.");
    }

    leadForm.reset();
    formStatus.textContent =
      "Thank you. Your inquiry has been received, and our team will contact you soon.";
  } catch (error) {
    formStatus.textContent =
      error.message || "We could not submit your inquiry. Please try again shortly.";
  }
});
