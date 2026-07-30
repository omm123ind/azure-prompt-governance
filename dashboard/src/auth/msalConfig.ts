import { PublicClientApplication, type Configuration } from "@azure/msal-browser";

const msalConfig: Configuration = {
  auth: {
    clientId: import.meta.env.VITE_AAD_CLIENT_ID as string,
    authority: `https://login.microsoftonline.com/${import.meta.env.VITE_AAD_TENANT_ID as string}`,
    redirectUri: window.location.origin,
  },
  cache: {
    cacheLocation: "sessionStorage",
  },
};

export const loginRequest = {
  scopes: [`api://${import.meta.env.VITE_AAD_CLIENT_ID as string}/access_as_user`],
};

export const msalInstance = new PublicClientApplication(msalConfig);

export function getUserRoles(): string[] {
  const account = msalInstance.getActiveAccount();
  const claims = account?.idTokenClaims as { roles?: string[] } | undefined;
  return claims?.roles ?? [];
}
