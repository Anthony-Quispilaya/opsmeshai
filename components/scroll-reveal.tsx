"use client";

import { useEffect } from "react";

export function ScrollReveal() {
  useEffect(() => {
    const explicitElements = Array.from(document.querySelectorAll<HTMLElement>("[data-scroll-reveal]"));
    const autoElements = Array.from(
      document.querySelectorAll<HTMLElement>(
        ".landing-motion-scope section:not(:first-child) :is(h2, h3, p, article, a, li, span, div)",
      ),
    ).filter((element) => (element.textContent || "").trim().length > 0);
    const elements = Array.from(new Set([...explicitElements, ...autoElements]));

    elements.forEach((element) => {
      if (!element.hasAttribute("data-scroll-reveal")) {
        element.setAttribute("data-scroll-reveal", "auto");
      }
    });

    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
      elements.forEach((element) => element.classList.add("is-visible"));
      return;
    }

    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (!entry.isIntersecting) return;
          entry.target.classList.add("is-visible");
          observer.unobserve(entry.target);
        });
      },
      {
        threshold: 0.16,
        rootMargin: "0px 0px -10% 0px",
      },
    );

    elements.forEach((element, index) => {
      element.style.setProperty("--reveal-delay", `${Math.min(index % 5, 4) * 80}ms`);
      observer.observe(element);
    });

    return () => observer.disconnect();
  }, []);

  return null;
}
