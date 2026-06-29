const leadForm = document.querySelector("#leadForm");
const formStatus = document.querySelector("#formStatus");

leadForm?.addEventListener("submit", async (event) => {
  event.preventDefault();
  formStatus.textContent = "Sending...";

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
    formStatus.textContent = result.storage === "postgres"
      ? "Thank you. Your inquiry was saved to Postgres."
      : "Thank you. Your inquiry was saved locally until Postgres is configured.";
  } catch (error) {
    formStatus.textContent = error.message;
  }
});
