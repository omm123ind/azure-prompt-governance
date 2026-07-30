import { createTheme } from "@mui/material/styles";

const theme = createTheme({

  palette: {

    mode: "dark",

    primary: {
      main: "#0078D4",
    },

    secondary: {
      main: "#00BCF2",
    },

    background: {
      default: "#0F172A",
      paper: "#1E293B",
    }

  },

  shape: {
    borderRadius: 12,
  },

  typography: {
    fontFamily: "Segoe UI, Roboto, sans-serif",
  }

});

export default theme;