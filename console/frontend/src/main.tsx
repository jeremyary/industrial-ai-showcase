// This project was developed with assistance from AI tools.
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import "@patternfly/react-core/dist/styles/base.css";
import { App } from "./App.js";

const el = document.getElementById("root");
if (!el) throw new Error("#root element not found");
createRoot(el).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
