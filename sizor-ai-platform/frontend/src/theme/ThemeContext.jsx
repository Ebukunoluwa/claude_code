import { createContext, useContext, useState } from "react";
import { DARK, LIGHT } from "./tokens";

const ThemeCtx = createContext(null);

export function useTheme() {
  return useContext(ThemeCtx);
}

export function ThemeProvider({ children }) {
  const [isDark, setIsDark] = useState(false);
  const t = isDark ? DARK : LIGHT;

  return (
    <ThemeCtx.Provider value={{ t, isDark, toggle: () => setIsDark((d) => !d) }}>
      {children}
    </ThemeCtx.Provider>
  );
}
