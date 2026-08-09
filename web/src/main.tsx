import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App";
import { AmbientBackground, CrtOverlay } from "./components/Ambient";
import "./theme.css";
import "./app.css";

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <div className="sunder-root">
      <AmbientBackground />
      <CrtOverlay />
      <App />
    </div>
  </React.StrictMode>,
);
