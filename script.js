const leadForm = document.querySelector("#leadForm");
const formStatus = document.querySelector("#formStatus");
const navToggle = document.querySelector(".nav-toggle");
const header = document.querySelector("[data-elevate]");
const navLinks = document.querySelectorAll("nav a");
const revealItems = document.querySelectorAll(".reveal");
const heroCanvas = document.querySelector(".hero-live-bg");
const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

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

const initHeroNetwork = () => {
  if (!heroCanvas) return;

  const context = heroCanvas.getContext("2d");
  if (!context) return;

  let width = 0;
  let height = 0;
  let points = [];
  let frameId = 0;
  let lastTime = 0;
  const networkColors = [
    "103, 232, 249",
    "45, 212, 191",
    "96, 165, 250",
    "139, 92, 246",
  ];

  const resize = () => {
    const rect = heroCanvas.getBoundingClientRect();
    const ratio = Math.min(window.devicePixelRatio || 1, 2);
    width = Math.max(1, rect.width);
    height = Math.max(1, rect.height);
    heroCanvas.width = Math.floor(width * ratio);
    heroCanvas.height = Math.floor(height * ratio);
    context.setTransform(ratio, 0, 0, ratio, 0, 0);

    const pointCount = Math.min(76, Math.max(36, Math.floor(width / 24)));
    points = Array.from({ length: pointCount }, (_, index) => ({
      x: (index / pointCount) * width + Math.random() * 42,
      y: Math.random() * height,
      speed: 0.018 + Math.random() * 0.036,
      drift: 0.12 + Math.random() * 0.34,
      size: Math.random() > 0.72 ? 2.5 : 1.6,
      phase: Math.random() * Math.PI * 2,
      accent: index % networkColors.length,
    }));
  };

  const draw = (time = 0) => {
    const elapsed = Math.min(32, Math.max(0, time - lastTime) || 16);
    lastTime = time;
    context.clearRect(0, 0, width, height);

    const scanX = ((time * 0.036) % (width + 220)) - 110;
    const scan = context.createLinearGradient(scanX - 90, 0, scanX + 90, 0);
    scan.addColorStop(0, "rgba(45, 212, 191, 0)");
    scan.addColorStop(0.42, "rgba(103, 232, 249, 0.16)");
    scan.addColorStop(0.64, "rgba(139, 92, 246, 0.1)");
    scan.addColorStop(1, "rgba(45, 212, 191, 0)");
    context.fillStyle = scan;
    context.fillRect(scanX - 90, 0, 180, height);

    points.forEach((point) => {
      if (!reduceMotion) {
        point.y -= point.speed * elapsed;
        point.x += Math.sin(time * 0.0007 + point.phase) * point.drift;
        if (point.y < -18) {
          point.y = height + Math.random() * 50;
          point.x = Math.random() * width;
        }
      }
    });

    for (let i = 0; i < points.length; i += 1) {
      for (let j = i + 1; j < points.length; j += 1) {
        const a = points[i];
        const b = points[j];
        const dx = a.x - b.x;
        const dy = a.y - b.y;
        const distance = Math.hypot(dx, dy);
        if (distance < 142) {
          const color = networkColors[(a.accent + b.accent) % networkColors.length];
          context.strokeStyle = `rgba(${color}, ${0.19 * (1 - distance / 142)})`;
          context.lineWidth = 1;
          context.beginPath();
          context.moveTo(a.x, a.y);
          context.lineTo(b.x, b.y);
          context.stroke();
        }
      }
    }

    points.forEach((point) => {
      const color = networkColors[point.accent];
      context.fillStyle = `rgba(${color}, 0.78)`;
      context.fillRect(point.x - point.size / 2, point.y - point.size / 2, point.size, point.size);
      context.fillStyle = `rgba(${color}, 0.2)`;
      context.fillRect(point.x - 5, point.y - 1, 10, 2);
      if (point.size > 2) {
        context.fillStyle = `rgba(${color}, 0.12)`;
        context.fillRect(point.x - 12, point.y + 6, 24, 2);
      }
    });

    if (!reduceMotion) {
      frameId = window.requestAnimationFrame(draw);
    }
  };

  resize();
  draw();

  window.addEventListener("resize", () => {
    window.cancelAnimationFrame(frameId);
    resize();
    draw();
  }, { passive: true });
};

initHeroNetwork();

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
