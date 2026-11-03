import { createContext } from "react";
import type { Route } from "../lib/route";

/** The screen Back opens, set once by the shell for whichever screen is showing. */
export const BackTarget = createContext<Route>({ screen: "today" });
