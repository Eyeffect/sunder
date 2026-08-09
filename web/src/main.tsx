import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App";
import { CrtOverlay } from "./components/Ambient";
import "./theme.css";
import "./app.css";

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <div className="sunder-root">
      <CrtOverlay />
      <App />
    </div>
  </React.StrictMode>,
);
