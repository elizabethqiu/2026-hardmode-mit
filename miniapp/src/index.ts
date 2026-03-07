/**
 * Enoki MentraOS MiniApp entry point
 */

import { EnokiApp } from "./enoki-app.js";

const app = new EnokiApp({
  packageName: process.env.MENTRA_PACKAGE_NAME ?? "com.enoki.glass",
  apiKey: process.env.MENTRA_API_KEY ?? "",
  port: parseInt(process.env.PORT ?? "3000", 10),
});

app.start();
