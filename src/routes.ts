import { createBrowserRouter } from "react-router-dom";
import { Dashboard } from "./components/Dashboard";
import { Schedule } from "./components/Schedule";
import { Social } from "./components/Social";

export const router = createBrowserRouter([
  {
    path: "/",
    Component: Dashboard,
  },
  {
    path: "/schedule",
    Component: Schedule,
  },
  {
    path: "/social",
    Component: Social,
  },
]);
