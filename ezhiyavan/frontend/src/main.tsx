import { createRoot } from "react-dom/client";
import App from "./App";
import Partner from "./Partner";
import Admin from "./Admin";
import "./styles.css";
// Operators use #/partner and #/admin (English UI, tokens kept in memory only); farmers use the main app.
const h = location.hash;
const Root = h.startsWith("#/partner") ? Partner : h.startsWith("#/admin") ? Admin : App;
createRoot(document.getElementById("root")!).render(<Root />);
const secureOrLocal = location.protocol === "https:" || ["localhost", "127.0.0.1"].includes(location.hostname);
if ("serviceWorker" in navigator && secureOrLocal) navigator.serviceWorker.register("/sw.js").catch(() => 0);   // caches only the app shell, never API data
