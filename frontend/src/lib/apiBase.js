export function getApiBase() {
  const hostname = window.location.hostname;
  if (hostname === "localhost" || hostname === "127.0.0.1") {
    return "http://127.0.0.1:8000";
  }
  // Cloud Run: frontend and backend are separate services
  return "https://csnavigator-backend-750361124802.us-central1.run.app";
}
